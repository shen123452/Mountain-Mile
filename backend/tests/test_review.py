import pytest
from datetime import date, timedelta

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base, ReviewItem
from app.review.sm2 import sm2_next
from app.tools.registry import EmptyInput, ToolContext, today_tasks


def test_sm2_schedule_progression() -> None:
    ease, interval, reps = sm2_next(2.5, 0, 0, 4)
    assert (interval, reps) == (1, 1)
    ease2, interval2, reps2 = sm2_next(ease, interval, reps, 5)
    assert (interval2, reps2) == (6, 2)
    ease3, interval3, reps3 = sm2_next(ease2, interval2, reps2, 5)
    assert reps3 == 3
    assert interval3 == round(6 * ease2)
    # 未掌握:回到 1 天后,重复清零,ease 不变
    ease4, interval4, reps4 = sm2_next(ease3, interval3, reps3, 2)
    assert (ease4, interval4, reps4) == (ease3, 1, 0)


def test_sm2_ease_floor() -> None:
    ease, _, _ = sm2_next(1.3, 10, 5, 3)
    assert ease == 1.3


@pytest.mark.asyncio
async def test_review_items_flow_and_user_isolation() -> None:
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
            assert (await owner.post("/auth/register", json={"email": "review-owner@example.test", "name": "Owner", "password": "secure-pass-123"})).status_code == 201
            assert (await other.post("/auth/register", json={"email": "review-other@example.test", "name": "Other", "password": "secure-pass-123"})).status_code == 201

            created = await owner.post("/review-items", json={"knowledge_point": "SM-2 算法", "mastery": 4})
            assert created.status_code == 201, created.text
            item = created.json()["data"]
            assert item["repetitions"] == 1 and item["interval_days"] == 1
            assert item["due_date"] == (date.today() + timedelta(days=1)).isoformat()

            # 未到期:due=true 查不到
            assert (await owner.get("/review-items", params={"due": True})).json()["data"] == []
            # 列表能查到;他人不可见
            assert len((await owner.get("/review-items")).json()["data"]) == 1
            assert (await other.get("/review-items")).json()["data"] == []

            # 手动把到期日改回今天,模拟到期
            async with sessions() as session:
                row = await session.scalar(select(ReviewItem).where(ReviewItem.id == item["id"]))
                row.due_date = date.today()
                await session.commit()
            due_items = (await owner.get("/review-items", params={"due": True})).json()["data"]
            assert [entry["id"] for entry in due_items] == [item["id"]]

            # 按掌握度评分:排期后延
            scored = await owner.post(f"/review-items/{item['id']}/review", json={"quality": 5})
            assert scored.status_code == 200
            updated = scored.json()["data"]
            assert updated["repetitions"] == 2 and updated["interval_days"] == 6
            assert updated["due_date"] > date.today().isoformat()

            # 低分:回到 1 天后、次数清零
            failed = await owner.post(f"/review-items/{item['id']}/review", json={"quality": 1})
            assert failed.json()["data"]["repetitions"] == 0

            assert (await other.post(f"/review-items/{item['id']}/review", json={"quality": 5})).status_code == 404
            assert (await owner.delete(f"/review-items/{item['id']}")).status_code == 200
            assert (await owner.get("/review-items")).json()["data"] == []
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_today_tasks_include_due_reviews() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as db:
            from app.models import User
            user = User(email="due-review@example.test", name="Due", password_hash="x")
            db.add(user)
            await db.flush()
            item = ReviewItem(user_id=user.id, knowledge_point="到期知识点", due_date=date.today())
            future = ReviewItem(user_id=user.id, knowledge_point="未到期知识点", due_date=date.today() + timedelta(days=3))
            db.add_all([item, future])
            await db.commit()

            result = await today_tasks(ToolContext(user.id, db), EmptyInput())
            points = [entry["knowledge_point"] for entry in result["due_reviews"]]
            assert points == ["到期知识点"]
    finally:
        await engine.dispose()
