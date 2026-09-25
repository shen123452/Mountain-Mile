import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import Base, Notification, User, UserMemory
from app.scheduler.jobs import evict_cold_memories


@pytest.mark.asyncio
async def test_cold_memories_are_evicted_with_audit_notification() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as db:
            user = User(email="evict@example.test", name="Evict", password_hash="x")
            db.add(user)
            await db.flush()
            old = datetime.now(timezone.utc) - timedelta(days=120)
            cold = UserMemory(user_id=user.id, content="很久没用的低重要记忆", importance=0.1)
            cold.created_at = old
            cold.use_count = 0
            recent_low = UserMemory(user_id=user.id, content="最近记录的低重要记忆", importance=0.1)
            old_important = UserMemory(user_id=user.id, content="很久前的重要记忆", importance=0.9)
            old_important.created_at = old
            db.add_all([cold, recent_low, old_important])
            await db.commit()

            counts = await evict_cold_memories(db)
            await db.commit()

            assert counts == {user.id: 1}
            remaining = set(await db.scalars(select(UserMemory.content).where(UserMemory.user_id == user.id)))
            assert remaining == {"最近记录的低重要记忆", "很久前的重要记忆"}
            note = await db.scalar(select(Notification).where(Notification.user_id == user.id, Notification.type == "memory_eviction"))
            assert note is not None
            assert "1 条" in note.content

            # 同日再次执行不产生重复通知
            second = await evict_cold_memories(db)
            await db.commit()
            assert second == {}
            notes = list(await db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.type == "memory_eviction")))
            assert len(notes) == 1
    finally:
        await engine.dispose()
