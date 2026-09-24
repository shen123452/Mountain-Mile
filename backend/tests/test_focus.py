from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base, Goal


@pytest.mark.asyncio
async def test_focus_completion_growth_and_daily_checkin() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def test_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            assert (await client.post("/auth/register", json={"email": "focus@example.test", "name": "Focus", "password": "secure-pass-123"})).status_code == 201
            goal = (await client.post("/goals", json={"name": "线性代数"})).json()["data"]
            session = (await client.post("/focus-sessions", json={"goal_id": goal["id"], "planned_minutes": 25})).json()["data"]
            done = await client.patch(f"/focus-sessions/{session['id']}", json={"actual_minutes": 16})
            assert done.status_code == 200
            checkin = await client.post("/checkins", json={"goal_id": goal["id"], "mood": "steady"})
            assert checkin.status_code == 201
            assert (await client.post("/checkins", json={"goal_id": goal["id"]})).status_code == 409
            refreshed = (await client.get("/goals")).json()["data"][0]
            assert refreshed["unlocked_count"] == 25
            async with sessions() as db:
                saved = await db.scalar(select(Goal).where(Goal.id == goal["id"]))
                assert saved is not None
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
