from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import utc_now
from app.knowledge.service import MAX_UPLOAD_BYTES, embed, find_memory_duplicate, search_chunks, search_memories, store_document
from app.models import DocumentChunk, KnowledgeDoc, User, UserMemory

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    memory_type: str = Field(default="fact", pattern=r"^(goal|habit|preference|skill|weakness|fact)$")
    importance: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=0.7, ge=0, le=1)


class MemoryUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    memory_type: str = Field(pattern=r"^(goal|habit|preference|skill|weakness|fact)$")
    importance: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)


class SearchBody(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)


def memory_data(item: UserMemory) -> dict:
    return {"id": item.id, "content": item.content, "memory_type": item.memory_type, "importance": item.importance, "confidence": item.confidence, "source": item.source, "use_count": item.use_count, "last_used": item.last_used.isoformat() if item.last_used else None, "created_at": item.created_at.isoformat()}


def document_data(item: KnowledgeDoc) -> dict:
    return {"id": item.id, "title": item.title, "filename": item.filename, "mime_type": item.mime_type, "status": item.status, "char_count": item.char_count, "source_url": item.source_url, "created_at": item.created_at.isoformat()}


@router.get("/documents")
async def list_documents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.scalars(select(KnowledgeDoc).where(KnowledgeDoc.user_id == user.id).order_by(KnowledgeDoc.created_at.desc()))
    return {"data": [document_data(item) for item in rows]}


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件不能超过 8 MB")
    try:
        item = await store_document(db, user.id, file.filename or "untitled.txt", file.content_type or "text/plain", data)
        await db.commit(); await db.refresh(item)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"data": document_data(item)}


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(KnowledgeDoc).where(KnowledgeDoc.id == document_id, KnowledgeDoc.user_id == user.id))
    if not item: raise HTTPException(status_code=404, detail="资料不存在")
    await db.delete(item); await db.commit()
    return {"data": {"ok": True}}


@router.post("/search")
async def search_knowledge(body: SearchBody, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return {"data": {"query": body.query, "results": await search_chunks(db, user.id, body.query, body.limit)}}


@router.get("/memories")
async def list_memories(query: str = "", limit: int = 50, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await search_memories(db, user.id, query.strip(), limit)
    return {"data": [memory_data(item) for item in rows]}


@router.post("/memories", status_code=status.HTTP_201_CREATED)
async def create_memory(body: MemoryCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    duplicate = await find_memory_duplicate(db, user.id, body.content.strip())
    if duplicate:
        duplicate.importance = max(duplicate.importance, body.importance); duplicate.confidence = max(duplicate.confidence, body.confidence); duplicate.updated_at = utc_now()
        await db.commit(); await db.refresh(duplicate)
        return {"data": memory_data(duplicate), "merged": True}
    content = body.content.strip()
    item = UserMemory(user_id=user.id, content=content, memory_type=body.memory_type, importance=body.importance, confidence=body.confidence, source="user", embedding=(await embed([content]))[0])
    db.add(item); await db.commit(); await db.refresh(item)
    return {"data": memory_data(item), "merged": False}


@router.patch("/memories/{memory_id}")
async def update_memory(memory_id: str, body: MemoryUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(UserMemory).where(UserMemory.id == memory_id, UserMemory.user_id == user.id))
    if not item: raise HTTPException(status_code=404, detail="记忆不存在")
    item.content = body.content.strip(); item.memory_type = body.memory_type; item.importance = body.importance; item.confidence = body.confidence
    item.embedding = (await embed([item.content]))[0]
    await db.commit(); await db.refresh(item)
    return {"data": memory_data(item)}


@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(UserMemory).where(UserMemory.id == memory_id, UserMemory.user_id == user.id))
    if not item: raise HTTPException(status_code=404, detail="记忆不存在")
    await db.delete(item); await db.commit()
    return {"data": {"ok": True}}
