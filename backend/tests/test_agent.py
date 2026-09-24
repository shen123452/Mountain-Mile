import json
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api import agent as agent_api
from app.core.database import get_db
from app.main import app
from app.models import Base, Todo
from app.tools.registry import REGISTRY


class FakeLLM:
    def __init__(self) -> None:
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **_kwargs):
        self.calls += 1
        if self.calls in (1, 3):
            tool_call = SimpleNamespace(id=f"call-{self.calls}", function=SimpleNamespace(
                name="createTodo", arguments=json.dumps({"title": f"复习高数 {self.calls}"})
            ))
            message = SimpleNamespace(content=None, tool_calls=[tool_call])
        else:
            message = SimpleNamespace(content="已处理你的学习待办。", tool_calls=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    async def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_agent_approval_resume_and_reject(monkeypatch) -> None:
    assert len(REGISTRY) == 14
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def test_db():
        async with sessions() as session:
            yield session

    fake = FakeLLM()
    monkeypatch.setattr(agent_api, "llm_client", lambda: fake)
    app.dependency_overrides[get_db] = test_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            assert (await client.post("/auth/register", json={"email": "agent@example.test", "name": "Agent", "password": "secure-pass-123"})).status_code == 201
            started = await client.post("/agent/runs", json={"goal": "为我安排复习"})
            assert started.status_code == 200, started.text
            run = started.json()["data"]
            assert run["status"] == "awaiting_approval"
            async with sessions() as session:
                assert (await session.scalars(select(Todo))).all() == []
            detail = (await client.get(f"/agent/runs/{run['id']}")).json()["data"]
            assert detail["steps"][0]["status"] == "awaiting_approval"
            approval = detail["approvals"][0]
            assert approval["payload"]["title"] == "复习高数 1"
            approved = await client.post(f"/agent/runs/{run['id']}/approval", json={"decision": "approve", "edited_payload": {"title": "复习线性代数"}})
            assert approved.status_code == 200, approved.text
            assert approved.json()["data"]["status"] == "completed"
            async with sessions() as session:
                todos = (await session.scalars(select(Todo))).all()
                assert [todo.title for todo in todos] == ["复习线性代数"]
            assert (await client.post(f"/agent/runs/{run['id']}/approval", json={"decision": "approve"})).status_code == 409

            rejected_run = (await client.post("/agent/runs", json={"goal": "另一个复习任务"})).json()["data"]
            assert rejected_run["status"] == "awaiting_approval"
            rejected = await client.post(f"/agent/runs/{rejected_run['id']}/approval", json={"decision": "reject", "reason": "今天不做"})
            assert rejected.json()["data"]["status"] == "rejected"
            async with sessions() as session:
                assert len((await session.scalars(select(Todo))).all()) == 1
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
