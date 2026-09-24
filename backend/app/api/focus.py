from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import utc_now
from app.models import Checkin, FocusSession, Goal, User

router = APIRouter(tags=["focus"])


class FocusStart(BaseModel):
    goal_id: str
    planned_minutes: int = Field(default=25, ge=1, le=240)
    mode: Literal["pomodoro", "deep_work", "custom"] = "pomodoro"


class FocusComplete(BaseModel):
    actual_minutes: int = Field(ge=0, le=1440)
    note: str | None = Field(default=None, max_length=2000)


class CheckinCreate(BaseModel):
    goal_id: str | None = None
    mood: str | None = Field(default=None, max_length=20)
    content: str | None = Field(default=None, max_length=2000)


def focus_data(item: FocusSession) -> dict:
    return {"id": item.id, "goal_id": item.goal_id, "planned_minutes": item.planned_minutes, "actual_minutes": item.actual_minutes,
            "mode": item.mode, "completed": item.completed, "note": item.note, "started_at": item.started_at.isoformat(),
            "ended_at": item.ended_at.isoformat() if item.ended_at else None}


async def owned_goal(goal_id: str, user_id: str, db: AsyncSession) -> Goal:
    goal = await db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id, Goal.status == "active"))
    if not goal:
        raise HTTPException(status_code=404, detail="目标不存在")
    return goal


@router.post("/focus-sessions", status_code=status.HTTP_201_CREATED)
async def start_focus(body: FocusStart, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_goal(body.goal_id, user.id, db)
    item = FocusSession(user_id=user.id, goal_id=body.goal_id, planned_minutes=body.planned_minutes, mode=body.mode)
    db.add(item); await db.commit(); await db.refresh(item)
    return {"data": focus_data(item)}


@router.patch("/focus-sessions/{session_id}")
async def complete_focus(session_id: str, body: FocusComplete, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(FocusSession).where(FocusSession.id == session_id, FocusSession.user_id == user.id).with_for_update())
    if not item: raise HTTPException(status_code=404, detail="专注记录不存在")
    if item.completed: raise HTTPException(status_code=409, detail="专注记录已完成")
    item.actual_minutes = body.actual_minutes; item.note = body.note; item.completed = True; item.ended_at = utc_now()
    await db.commit(); await db.refresh(item)
    return {"data": focus_data(item)}


@router.get("/focus-sessions")
async def list_focus(goal_id: str | None = None, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(FocusSession).where(FocusSession.user_id == user.id).order_by(FocusSession.started_at.desc()).limit(100)
    if goal_id: query = query.where(FocusSession.goal_id == goal_id)
    return {"data": [focus_data(item) for item in await db.scalars(query)]}


@router.post("/checkins", status_code=status.HTTP_201_CREATED)
async def create_checkin(body: CheckinCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if body.goal_id: await owned_goal(body.goal_id, user.id, db)
    item = Checkin(user_id=user.id, goal_id=body.goal_id, mood=body.mood, content=body.content, checkin_date=date.today())
    db.add(item)
    try: await db.commit()
    except IntegrityError as exc:
        await db.rollback(); raise HTTPException(status_code=409, detail="今天已经打卡") from exc
    await db.refresh(item)
    return {"data": {"id": item.id, "goal_id": item.goal_id, "mood": item.mood, "content": item.content, "checkin_date": item.checkin_date.isoformat()}}


@router.get("/checkins")
async def list_checkins(days: int = 30, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    days = max(1, min(days, 365))
    rows = await db.scalars(select(Checkin).where(Checkin.user_id == user.id).order_by(Checkin.checkin_date.desc()).limit(days))
    return {"data": [{"id": item.id, "goal_id": item.goal_id, "mood": item.mood, "content": item.content, "checkin_date": item.checkin_date.isoformat()} for item in rows]}


async def growth_for_goal(goal_id: str, user_id: str, db: AsyncSession) -> int:
    focus = await db.scalar(select(func.coalesce(func.sum(FocusSession.actual_minutes), 0)).where(FocusSession.goal_id == goal_id, FocusSession.user_id == user_id, FocusSession.completed))
    checkins = await db.scalar(select(func.count(Checkin.id)).where(Checkin.goal_id == goal_id, Checkin.user_id == user_id))
    return min(221, 20 + int(focus or 0) // 8 + int(checkins or 0) * 3)
