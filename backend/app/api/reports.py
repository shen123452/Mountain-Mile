from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Checkin, FocusSession, Goal, User

router = APIRouter(prefix="/reports", tags=["reports"])


async def weekly_summary(user_id: str, db: AsyncSession, end: date | None = None) -> dict:
    end = end or date.today(); start = end - timedelta(days=6)
    minutes = await db.scalar(select(func.coalesce(func.sum(FocusSession.actual_minutes), 0)).where(FocusSession.user_id == user_id, FocusSession.completed, FocusSession.started_at >= start))
    sessions = await db.scalar(select(func.count(FocusSession.id)).where(FocusSession.user_id == user_id, FocusSession.completed, FocusSession.started_at >= start))
    checkins = await db.scalar(select(func.count(Checkin.id)).where(Checkin.user_id == user_id, Checkin.checkin_date.between(start, end)))
    goals = await db.scalars(select(Goal).where(Goal.user_id == user_id, Goal.status == "active"))
    return {"period": {"start": start.isoformat(), "end": end.isoformat()}, "focus_minutes": int(minutes or 0), "focus_sessions": int(sessions or 0), "checkins": int(checkins or 0), "active_goals": [{"id": goal.id, "name": goal.name} for goal in goals]}


@router.get("/weekly")
async def weekly_report(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return {"data": await weekly_summary(user.id, db)}


@router.get("/daily")
async def daily_report(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return {"data": await weekly_summary(user.id, db, date.today())}
