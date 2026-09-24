from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import AgentSchedule, User

router = APIRouter(prefix="/agent/schedule", tags=["schedule"])
APP_TZ = ZoneInfo("Asia/Shanghai")


class ScheduleBody(BaseModel):
    type: str = Field(default="daily", max_length=20)
    cron: str = Field(min_length=9, max_length=60)
    goal: str = Field(min_length=1, max_length=500)
    enabled: bool = True


def schedule_data(item: AgentSchedule) -> dict:
    return {"id": item.id, "type": item.type, "cron": item.cron, "goal": item.goal, "enabled": item.enabled, "last_run_at": item.last_run_at.isoformat() if item.last_run_at else None, "next_run_at": item.next_run_at.isoformat() if item.next_run_at else None}


def validate_cron(value: str) -> str:
    try: CronTrigger.from_crontab(value)
    except (ValueError, IndexError) as exc: raise HTTPException(status_code=422, detail="cron 必须是五段标准表达式") from exc
    return value


@router.get("")
async def list_schedules(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.scalars(select(AgentSchedule).where(AgentSchedule.user_id == user.id).order_by(AgentSchedule.created_at.desc()))
    return {"data": [schedule_data(item) for item in rows]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_schedule(body: ScheduleBody, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cron = validate_cron(body.cron.strip()); now = datetime.now(APP_TZ)
    trigger = CronTrigger.from_crontab(cron, timezone=APP_TZ)
    item = AgentSchedule(user_id=user.id, type=body.type, cron=cron, goal=body.goal.strip(), enabled=body.enabled, next_run_at=trigger.get_next_fire_time(None, now))
    db.add(item); await db.commit(); await db.refresh(item)
    return {"data": schedule_data(item)}


@router.patch("/{schedule_id}")
async def update_schedule(schedule_id: str, body: ScheduleBody, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(AgentSchedule).where(AgentSchedule.id == schedule_id, AgentSchedule.user_id == user.id))
    if not item: raise HTTPException(status_code=404, detail="调度不存在")
    cron = validate_cron(body.cron.strip()); item.type = body.type; item.cron = cron; item.goal = body.goal.strip(); item.enabled = body.enabled
    item.next_run_at = CronTrigger.from_crontab(cron, timezone=APP_TZ).get_next_fire_time(None, datetime.now(APP_TZ))
    await db.commit(); await db.refresh(item)
    return {"data": schedule_data(item)}
