import pytest
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base, Checkin, FocusSession, Goal
from app.api.stats import current_streak, heatmap_level

APP_TZ = ZoneInfo("Asia/Shanghai")


def test_heatmap_level_thresholds() -> None:
    assert heatmap_level(0) == 0
    assert heatmap_level(15) == 1
    assert heatmap_level(45) == 2
    assert heatmap_level(90) == 3
    assert heatmap_level(120) == 4


def test_current_streak_counts_backwards() -> None:
    today = date.today()
    dates = {today - timedelta(days=offset) for offset in (1, 2, 3)}
    assert current_streak(dates, today) == 3  # 今天未打卡,从昨天往前数
    assert current_streak(dates | {today}, today) == 4
    assert current_streak({today - timedelta(days=5)}, today) == 0


@pytest.mark.asyncio
async def test_stats_endpoints_and_isolation() -> None:
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
            assert (await owner.post("/auth/register", json={"email": "stats-owner@example.test", "name": "Owner", "password": "secure-pass-123"})).status_code == 201
            assert (await other.post("/auth/register", json={"email": "stats-other@example.test", "name": "Other", "password": "secure-pass-123"})).status_code == 201

            from sqlalchemy import select as sa_select
            from app.models import User
            async with sessions() as session:
                user_id = await session.scalar(sa_select(User.id).where(User.email == "stats-owner@example.test"))
                today = datetime.now(APP_TZ).date()
                goal_a = Goal(user_id=user_id, name="高数", seed="seed-math")
                goal_b = Goal(user_id=user_id, name="英语", seed="seed-english")
                session.add_all([goal_a, goal_b])
                await session.flush()
                # 高数 160 分钟 → 20+20=40 块;英语 0 分钟 → 20 块;排行高数在前
                ended = datetime.combine(today, time(hour=10), APP_TZ)
                session.add(FocusSession(user_id=user_id, goal_id=goal_a.id, actual_minutes=160, completed=True, started_at=ended, ended_at=ended))
                session.add(Checkin(user_id=user_id, checkin_date=today))
                session.add(Checkin(user_id=user_id, checkin_date=today - timedelta(days=1)))
                await session.commit()

            summary = (await owner.get("/stats/summary")).json()["data"]
            assert summary["total_focus_minutes"] == 160
            assert summary["total_focus_sessions"] == 1
            assert summary["total_checkins"] == 2
            assert summary["current_streak"] == 2
            assert summary["active_goals"] == 2
            ranking = summary["goal_ranking"]
            assert ranking[0]["name"] == "高数" and ranking[0]["unlocked"] == 40
            assert ranking[1]["unlocked"] == 20

            trend = (await owner.get("/stats/trend", params={"days": 7})).json()["data"]
            assert len(trend["points"]) == 7
            today_point = next(point for point in trend["points"] if point["date"] == today.isoformat())
            assert today_point["minutes"] == 160
            assert sum(point["minutes"] for point in trend["points"]) == 160

            heatmap = (await owner.get("/stats/heatmap", params={"weeks": 4})).json()["data"]
            assert heatmap["cells"][0]["date"] <= (today - timedelta(days=27)).isoformat()
            today_cell = next(cell for cell in heatmap["cells"] if cell["date"] == today.isoformat())
            assert today_cell["minutes"] == 160 and today_cell["level"] == 4

            # 用户隔离
            other_summary = (await other.get("/stats/summary")).json()["data"]
            assert other_summary["total_focus_minutes"] == 0 and other_summary["goal_ranking"] == []
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
