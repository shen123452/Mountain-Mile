import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base


@pytest.mark.asyncio
async def test_goals_are_owned_and_archive_preserves_history() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def test_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as owner, AsyncClient(transport=transport, base_url="http://testserver") as other:
            await owner.post("/auth/register", json={"email": "owner@example.test", "name": "Owner", "password": "secure-pass-123"})
            await other.post("/auth/register", json={"email": "other@example.test", "name": "Other", "password": "secure-pass-123"})
            created = await owner.post("/goals", json={"name": "  高等数学  ", "palette_variant": "azurite", "weekly_target_minutes": 300})
            assert created.status_code == 201, created.text
            goal = created.json()["data"]
            assert goal["name"] == "高等数学"
            assert goal["seed"] == goal["id"]
            assert goal["unlocked_count"] == 20
            assert len((await owner.get("/goals")).json()["data"]) == 1
            assert (await other.get(f"/goals/{goal['id']}")).status_code == 404
            assert (await other.patch(f"/goals/{goal['id']}", json={"name": "Wrong"})).status_code == 404
            assert (await owner.patch(f"/goals/{goal['id']}", json={"name": "数学进阶"})).json()["data"]["name"] == "数学进阶"
            assert (await owner.delete(f"/goals/{goal['id']}")).status_code == 200
            assert (await owner.get("/goals")).json()["data"] == []
            assert (await owner.get(f"/goals/{goal['id']}")).json()["data"]["status"] == "archived"
            assert (await owner.patch(f"/goals/{goal['id']}", json={"name": "Again"})).status_code == 409
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
