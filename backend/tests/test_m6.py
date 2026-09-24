import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base


@pytest.mark.asyncio
async def test_conversation_report_and_schedule(monkeypatch) -> None:
    monkeypatch.setattr("app.api.conversations.settings.dashscope_api_key", "")
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
            assert (await client.post("/auth/register", json={"email": "m6@example.test", "name": "M6", "password": "secure-pass-123"})).status_code == 201
            conversation = (await client.post("/conversations", json={"title": "本周复盘"})).json()["data"]
            sent = await client.post(f"/conversations/{conversation['id']}/messages", json={"content": "今天复习什么？"})
            assert sent.status_code == 200
            assert sent.json()["data"]["provider_status"] == "unconfigured"
            detail = (await client.get(f"/conversations/{conversation['id']}")) .json()["data"]
            assert [item["role"] for item in detail["messages"]] == ["user", "assistant"]
            report = await client.get("/reports/weekly")
            assert report.status_code == 200
            invalid = await client.post("/agent/schedule", json={"cron": "bad", "goal": "复盘"})
            assert invalid.status_code == 422
            schedule = await client.post("/agent/schedule", json={"cron": "0 9 * * *", "goal": "生成今日学习安排"})
            assert schedule.status_code == 201
            assert schedule.json()["data"]["next_run_at"]
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
