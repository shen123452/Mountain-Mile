import pytest
from datetime import date, timedelta

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import utc_now
from app.main import app
from app.models import AgentRun, AgentStep, AgentToolCall, Base, Checkin, FocusSession, Goal, Plan, PlanTask, Todo, User
from app.tools.registry import GoalIdInput, RecentInput, ToolContext, detect_overload, focus_rhythm, forecast_goal


@pytest.mark.asyncio
async def test_observatory_metrics_aggregates_runs_and_tools() -> None:
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
            assert (await owner.post("/auth/register", json={"email": "obs-owner@example.test", "name": "Owner", "password": "secure-pass-123"})).status_code == 201
            assert (await other.post("/auth/register", json={"email": "obs-other@example.test", "name": "Other", "password": "secure-pass-123"})).status_code == 201

            async with sessions() as session:
                user_id = await session.scalar(select(User.id).where(User.email == "obs-owner@example.test"))
                now = utc_now()
                run = AgentRun(user_id=user_id, goal="整理本周复习", role="Scout", status="completed",
                               prompt_tokens=1000, completion_tokens=500, current_step=2,
                               started_at=now, completed_at=now)
                session.add(run)
                await session.flush()
                step = AgentStep(run_id=run.id, step_number=1, agent_role="Scout", kind="tool", status="completed", title="scheduleReview")
                session.add(step)
                await session.flush()
                session.add_all([
                    AgentToolCall(step_id=step.id, tool="scheduleReview", risk_tier="write-low", args={}, status="completed", latency_ms=120, completed_at=now),
                    AgentToolCall(step_id=step.id, tool="scheduleReview", risk_tier="write-low", args={}, status="failed", completed_at=now),
                ])
                await session.commit()

            metrics = (await owner.get("/observatory/metrics")).json()["data"]
            totals = metrics["totals"]
            assert totals["runs"] == 1 and totals["success_rate"] == 1
            assert totals["prompt_tokens"] == 1000 and totals["completion_tokens"] == 500
            assert totals["estimated_cost"] == pytest.approx(0.0018, abs=1e-6)
            tool = next(entry for entry in metrics["tools"] if entry["tool"] == "scheduleReview")
            assert tool["calls"] == 2 and tool["success_rate"] == 0.5 and tool["avg_latency_ms"] == 120
            assert len(metrics["recent_runs"]) == 1 and metrics["recent_runs"][0]["estimated_cost"] == pytest.approx(0.0018, abs=1e-6)

            # 用户隔离
            other_metrics = (await other.get("/observatory/metrics")).json()["data"]
            assert other_metrics["totals"]["runs"] == 0 and other_metrics["recent_runs"] == []
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_analysis_tools_rhythm_overload_forecast() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as db:
            user = User(email="analysis@example.test", name="Ana", password_hash="x")
            db.add(user)
            await db.flush()
            now = utc_now()
            morning = FocusSession(user_id=user.id, goal_id="g0", planned_minutes=25, actual_minutes=25, completed=True,
                                   started_at=now.replace(hour=9), ended_at=now)
            evening = FocusSession(user_id=user.id, goal_id="g0", planned_minutes=25, actual_minutes=50, completed=True,
                                   started_at=now.replace(hour=21), ended_at=now)
            abandoned = FocusSession(user_id=user.id, goal_id="g0", planned_minutes=25, actual_minutes=5, completed=False,
                                     started_at=now.replace(hour=15), ended_at=now)
            db.add_all([morning, evening, abandoned])
            for index in range(6):
                db.add(Goal(user_id=user.id, name=f"目标{index}", seed=f"s{index}"))
            db.add(Checkin(user_id=user.id, checkin_date=date.today()))
            await db.commit()

            ctx = ToolContext(user.id, db)
            rhythm = await focus_rhythm(ctx, RecentInput(days=7))
            assert rhythm["total_sessions"] == 3 and rhythm["completed_sessions"] == 2
            assert rhythm["completion_rate"] == pytest.approx(2 / 3, abs=1e-3)
            assert rhythm["best_hour"] == 21
            assert rhythm["minutes_by_hour"]["9"] == 25

            overload = await detect_overload(ctx, GoalIdInput(goal_id="all"))
            assert overload["overloaded"] is True
            assert overload["active_goals"] == 6
            assert any("并行目标" in signal for signal in overload["signals"])
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_forecast_goal_estimates_completion() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as db:
            user = User(email="forecast@example.test", name="Fore", password_hash="x")
            db.add(user)
            await db.flush()
            goal = Goal(user_id=user.id, name="英语", seed="english-seed")
            db.add(goal)
            await db.flush()
            now = utc_now()
            # 近 14 天累计 560 分钟 → 日均 40 分钟 → 每天 5 块生长
            session = FocusSession(user_id=user.id, goal_id=goal.id, planned_minutes=60, actual_minutes=560, completed=True,
                                   started_at=now - timedelta(days=1), ended_at=now - timedelta(days=1))
            db.add(session)
            await db.commit()

            result = await forecast_goal(ToolContext(user.id, db), GoalIdInput(goal_id=goal.id))
            assert result["unlocked"] == 20 + 560 // 8  # 90
            assert result["total"] == 221
            assert result["daily_focus_minutes"] == pytest.approx(40.0, abs=0.1)
            assert result["estimated_completion"] is not None

            missing = await forecast_goal(ToolContext(user.id, db), GoalIdInput(goal_id="not-exist"))
            assert "error" in missing
    finally:
        await engine.dispose()
