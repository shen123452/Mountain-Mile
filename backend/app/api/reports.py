from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Checkin, FocusSession, Goal, User

router = APIRouter(prefix="/reports", tags=["reports"])


APP_TZ = ZoneInfo("Asia/Shanghai")


async def summary_for_period(user_id: str, db: AsyncSession, start: date, end: date) -> dict:
    lower = datetime.combine(start, time.min, APP_TZ)
    upper = datetime.combine(end + timedelta(days=1), time.min, APP_TZ)
    minutes = await db.scalar(select(func.coalesce(func.sum(FocusSession.actual_minutes), 0)).where(FocusSession.user_id == user_id, FocusSession.completed, FocusSession.ended_at >= lower, FocusSession.ended_at < upper))
    sessions = await db.scalar(select(func.count(FocusSession.id)).where(FocusSession.user_id == user_id, FocusSession.completed, FocusSession.ended_at >= lower, FocusSession.ended_at < upper))
    checkins = await db.scalar(select(func.count(Checkin.id)).where(Checkin.user_id == user_id, Checkin.checkin_date.between(start, end)))
    goals = await db.scalars(select(Goal).where(Goal.user_id == user_id, Goal.status == "active"))
    return {"period": {"start": start.isoformat(), "end": end.isoformat()}, "focus_minutes": int(minutes or 0), "focus_sessions": int(sessions or 0), "checkins": int(checkins or 0), "active_goals": [{"id": goal.id, "name": goal.name} for goal in goals]}


async def weekly_summary(user_id: str, db: AsyncSession, today: date | None = None) -> dict:
    today = today or datetime.now(APP_TZ).date()
    start = today - timedelta(days=today.weekday())
    return await summary_for_period(user_id, db, start, start + timedelta(days=6))


@router.get("/weekly")
async def weekly_report(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return {"data": await weekly_summary(user.id, db)}


@router.get("/daily")
async def daily_report(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    today = datetime.now(APP_TZ).date()
    return {"data": await summary_for_period(user.id, db, today, today)}
