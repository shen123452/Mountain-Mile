import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base


@pytest.mark.asyncio
async def test_knowledge_documents_and_memories_are_private_and_searchable(monkeypatch) -> None:
    monkeypatch.setattr("app.knowledge.service.settings.dashscope_api_key", "")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def test_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as owner, AsyncClient(transport=transport, base_url="http://testserver") as other:
            assert (await owner.post("/auth/register", json={"email": "knowledge-owner@example.test", "name": "Owner", "password": "secure-pass-123"})).status_code == 201
            assert (await other.post("/auth/register", json={"email": "knowledge-other@example.test", "name": "Other", "password": "secure-pass-123"})).status_code == 201

            uploaded = await owner.post("/knowledge/documents", files={"file": ("notes.txt", "Python asyncio\nAsyncSession keeps database work non-blocking.".encode(), "text/plain")})
            assert uploaded.status_code == 201, uploaded.text
            document = uploaded.json()["data"]
            assert document["title"] == "notes"
            assert (await other.get("/knowledge/documents")).json()["data"] == []

            results = await owner.post("/knowledge/search", json={"query": "non-blocking"})
            assert results.status_code == 200
            assert results.json()["data"]["results"][0]["title"] == "notes"
            assert (await other.post("/knowledge/search", json={"query": "non-blocking"})).json()["data"]["results"] == []

            first = await owner.post("/knowledge/memories", json={"content": "我习惯早晨学习", "memory_type": "habit", "importance": 0.4})
            assert first.status_code == 201
            memory = first.json()["data"]
            merged = await owner.post("/knowledge/memories", json={"content": "我习惯 早晨学习", "memory_type": "habit", "importance": 0.8})
            assert merged.status_code == 201
            assert merged.json()["merged"] is True
            assert merged.json()["data"]["id"] == memory["id"]
            assert merged.json()["data"]["importance"] == 0.8
            searched = await owner.get("/knowledge/memories", params={"query": "早晨"})
            assert [item["id"] for item in searched.json()["data"]] == [memory["id"]]
            assert (await other.get("/knowledge/memories")).json()["data"] == []

            assert (await other.delete(f"/knowledge/documents/{document['id']}")).status_code == 404
            assert (await owner.delete(f"/knowledge/documents/{document['id']}")).status_code == 200
            assert (await owner.delete(f"/knowledge/memories/{memory['id']}")).status_code == 200
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
