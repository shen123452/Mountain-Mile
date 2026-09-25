from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Checkin, FocusSession, Goal, User
from app.api.focus import growth_for_goal
from app.review.service import due_reviews

router = APIRouter(prefix="/stats", tags=["stats"])

APP_TZ = ZoneInfo("Asia/Shanghai")
TERRAIN_TOTAL_TILES = 221
HEATMAP_LEVEL_CAPS = (0, 15, 45, 90)  # 分钟数分档:0 / ≤15 / ≤45 / ≤90 / >90


def heatmap_level(minutes: int) -> int:
    if minutes <= 0:
        return 0
    if minutes <= HEATMAP_LEVEL_CAPS[1]:
        return 1
    if minutes <= HEATMAP_LEVEL_CAPS[2]:
        return 2
    if minutes <= HEATMAP_LEVEL_CAPS[3]:
        return 3
    return 4


async def minutes_by_day(db: AsyncSession, user_id: str, since: date) -> dict[date, int]:
    lower = datetime.combine(since, time.min, APP_TZ)
    rows = (await db.execute(select(FocusSession.ended_at, FocusSession.actual_minutes).where(
        FocusSession.user_id == user_id, FocusSession.completed, FocusSession.ended_at >= lower))).all()
    by_day: dict[date, int] = {}
    for ended_at, minutes in rows:
        day = ended_at.astimezone(APP_TZ).date() if ended_at.tzinfo else ended_at.date()
        by_day[day] = by_day.get(day, 0) + (minutes or 0)
    return by_day


def current_streak(checkin_dates: set[date], today: date) -> int:
    cursor = today if today in checkin_dates else today - timedelta(days=1)
    streak = 0
    while cursor in checkin_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


@router.get("/summary")
async def stats_summary(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    total_minutes = await db.scalar(select(func.coalesce(func.sum(FocusSession.actual_minutes), 0)).where(
        FocusSession.user_id == user.id, FocusSession.completed)) or 0
    total_sessions = await db.scalar(select(func.count(FocusSession.id)).where(
        FocusSession.user_id == user.id, FocusSession.completed)) or 0
    checkin_dates = set(await db.scalars(select(Checkin.checkin_date).where(Checkin.user_id == user.id)))
    goals = list(await db.scalars(select(Goal).where(Goal.user_id == user.id, Goal.status == "active")))
    ranking = []
    for goal in goals:
        unlocked = await growth_for_goal(goal.id, user.id, db)
        ranking.append({"id": goal.id, "name": goal.name, "unlocked": unlocked, "total": TERRAIN_TOTAL_TILES,
                        "progress": round(unlocked / TERRAIN_TOTAL_TILES, 3)})
    ranking.sort(key=lambda item: -item["unlocked"])
    due_review_count = len(await due_reviews(db, user.id))
    return {"data": {
        "total_focus_minutes": int(total_minutes), "total_focus_sessions": int(total_sessions),
        "total_checkins": len(checkin_dates), "current_streak": current_streak(checkin_dates, datetime.now(APP_TZ).date()),
        "active_goals": len(goals), "due_reviews": due_review_count, "goal_ranking": ranking,
    }}


@router.get("/trend")
async def stats_trend(days: int = Query(default=14, ge=1, le=90),
                      user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    today = datetime.now(APP_TZ).date()
    since = today - timedelta(days=days - 1)
    by_day = await minutes_by_day(db, user.id, since)
    return {"data": {"days": days, "points": [
        {"date": (since + timedelta(days=offset)).isoformat(),
         "minutes": by_day.get(since + timedelta(days=offset), 0)}
        for offset in range(days)]}}


@router.get("/heatmap")
async def stats_heatmap(weeks: int = Query(default=26, ge=1, le=53),
                        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    today = datetime.now(APP_TZ).date()
    start = today - timedelta(days=weeks * 7 - 1)
    start = start - timedelta(days=start.weekday())  # 对齐到周一
    by_day = await minutes_by_day(db, user.id, start)
    cells = []
    cursor = start
    while cursor <= today:
        minutes = by_day.get(cursor, 0)
        cells.append({"date": cursor.isoformat(), "minutes": minutes, "level": heatmap_level(minutes)})
        cursor += timedelta(days=1)
    return {"data": {"weeks": weeks, "start": start.isoformat(), "cells": cells}}
