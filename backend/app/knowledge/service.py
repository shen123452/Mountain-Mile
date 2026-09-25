import io
import math
import re
from datetime import datetime
from pathlib import Path

from docx import Document as DocxDocument
from openai import AsyncOpenAI
from pgvector.sqlalchemy import Vector
from pypdf import PdfReader
from sqlalchemy import cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import utc_now
from app.models import DocumentChunk, KnowledgeDoc, UserMemory

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf", ".docx"}


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    return re.sub(r"[ \t]+", " ", text).strip()


def extract_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError("仅支持 TXT、Markdown、PDF 和 DOCX 文件")
    if suffix in {".txt", ".md"}:
        return clean_text(data.decode("utf-8-sig", errors="replace"))
    if suffix == ".pdf":
        return clean_text("\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages))
    document = DocxDocument(io.BytesIO(data))
    return clean_text("\n".join(paragraph.text for paragraph in document.paragraphs))


def split_chunks(text: str, size: int = 1200, overlap: int = 160) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = max(text.rfind("\n", start, end), text.rfind("。", start, end), text.rfind(" ", start, end))
            if boundary > start + size // 2:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return [item for item in chunks if item]


def keyword_score(query: str, content: str) -> float:
    terms = [term for term in re.findall(r"[\w\u4e00-\u9fff]+", query.casefold()) if term]
    if not terms:
        return 0
    haystack = content.casefold()
    return sum(haystack.count(term) for term in terms) / len(terms)


def cosine_score(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0
    dot = sum(a * b for a, b in zip(left, right))
    norm = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right))
    return dot / norm if norm else 0


async def embed(texts: list[str]) -> list[list[float] | None]:
    if not texts or not settings.dashscope_api_key:
        return [None for _ in texts]
    client = AsyncOpenAI(api_key=settings.dashscope_api_key, base_url=settings.llm_base_url)
    try:
        output: list[list[float] | None] = []
        for offset in range(0, len(texts), 10):
            response = await client.embeddings.create(model=settings.embedding_model, input=texts[offset:offset + 10], dimensions=settings.embedding_dim)
            vectors = sorted(response.data, key=lambda item: item.index)
            output.extend(list(item.embedding) for item in vectors)
        return output
    except Exception:
        return [None for _ in texts]
    finally:
        await client.close()


async def store_document(db: AsyncSession, user_id: str, filename: str, mime_type: str, data: bytes) -> KnowledgeDoc:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("文件不能超过 8 MB")
    text = extract_text(filename, data)
    if not text:
        raise ValueError("文件没有可提取的文本")
    filename = Path(filename.replace("\\", "/")).name
    title = Path(filename).stem[:200] or "未命名资料"
    has_oss_config = all((settings.oss_bucket, settings.oss_access_key_id, settings.oss_access_key_secret, settings.oss_endpoint))
    doc = KnowledgeDoc(user_id=user_id, title=title, filename=filename[:255], mime_type=mime_type[:120], char_count=len(text), raw_data=None if has_oss_config else data)
    db.add(doc)
    await db.flush()
    chunks = split_chunks(text)
    vectors = await embed(chunks)
    for index, (content, vector) in enumerate(zip(chunks, vectors)):
        db.add(DocumentChunk(document_id=doc.id, user_id=user_id, chunk_index=index, content=content, embedding=vector, token_count=len(content)))
    if settings.oss_bucket and settings.oss_access_key_id and settings.oss_access_key_secret and settings.oss_endpoint:
        try:
            import oss2
            auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
            bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket)
            key = f"knowledge/{user_id}/{doc.id}/{filename}"
            bucket.put_object(key, data)
            doc.object_key = key
            doc.source_url = f"{settings.oss_public_base.rstrip('/')}/{key}" if settings.oss_public_base else None
            doc.raw_data = None
        except Exception as exc:
            doc.status = "stored_local"
            doc.error = f"OSS 上传失败，已保留本地索引：{type(exc).__name__}"
    return doc


async def search_chunks(db: AsyncSession, user_id: str, query: str, limit: int = 5) -> list[dict]:
    limit = max(1, min(limit, 20))
    query_vector = (await embed([query]))[0]
    if query_vector and db.bind and db.bind.dialect.name == "postgresql":
        # 模型列是 JSON().with_variant(Vector, "postgresql"):表达式层 comparator 不带
        # pgvector 方法,必须显式 cast 到 Vector 才能调 cosine_distance
        emb = cast(DocumentChunk.embedding, Vector(settings.embedding_dim))
        distance = emb.cosine_distance(query_vector).label("distance")
        rows = (await db.execute(select(DocumentChunk, KnowledgeDoc, distance)
            .join(KnowledgeDoc, DocumentChunk.document_id == KnowledgeDoc.id)
            .where(DocumentChunk.user_id == user_id, DocumentChunk.embedding.is_not(None))
            .order_by(distance).limit(limit))).all()
        return [{"document_id": chunk.document_id, "title": doc.title, "chunk_index": chunk.chunk_index,
                 "content": chunk.content, "score": round(max(0.0, 1 - float(distance_value)), 4)}
                for chunk, doc, distance_value in rows]
    rows = (await db.execute(select(DocumentChunk, KnowledgeDoc).join(KnowledgeDoc, DocumentChunk.document_id == KnowledgeDoc.id).where(DocumentChunk.user_id == user_id))).all()
    scored = []
    for chunk, doc in rows:
        vector = chunk.embedding if isinstance(chunk.embedding, list) else None
        score = cosine_score(query_vector, vector) if query_vector and vector else keyword_score(query, chunk.content)
        scored.append((score, chunk, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [{"document_id": chunk.document_id, "title": doc.title, "chunk_index": chunk.chunk_index, "content": chunk.content, "score": round(score, 4)} for score, chunk, doc in scored[:limit]]


async def find_memory_duplicate(db: AsyncSession, user_id: str, content: str) -> UserMemory | None:
    rows = list(await db.scalars(select(UserMemory).where(UserMemory.user_id == user_id)))
    normalized = re.sub(r"\s+", "", content.casefold())
    exact = next((row for row in rows if normalized == re.sub(r"\s+", "", row.content.casefold()) or normalized in re.sub(r"\s+", "", row.content.casefold()) or re.sub(r"\s+", "", row.content.casefold()) in normalized), None)
    if exact:
        return exact
    vector = (await embed([content]))[0]
    if vector:
        return next((row for row in rows if isinstance(row.embedding, list) and cosine_score(vector, row.embedding) >= 0.92), None)
    return None


async def search_memories(db: AsyncSession, user_id: str, query: str = "", limit: int = 10) -> list[UserMemory]:
    limit = max(1, min(limit, 50))
    rows = list(await db.scalars(select(UserMemory).where(UserMemory.user_id == user_id)))
    vector = (await embed([query]))[0] if query else None
    if vector and db.bind and db.bind.dialect.name == "postgresql":
        emb = cast(UserMemory.embedding, Vector(settings.embedding_dim))
        distance = emb.cosine_distance(vector)
        return list(await db.scalars(select(UserMemory).where(UserMemory.user_id == user_id, UserMemory.embedding.is_not(None)).order_by(distance).limit(limit)))
    if query:
        rows.sort(key=lambda row: cosine_score(vector, row.embedding) if vector and isinstance(row.embedding, list) else keyword_score(query, row.content), reverse=True)
    else:
        rows.sort(key=lambda row: row.importance * 0.6 + max(0, 1 - (datetime.now().astimezone() - (row.last_used or row.created_at).astimezone()).days / 365) * 0.4, reverse=True)
    return rows[:limit]
