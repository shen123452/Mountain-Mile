from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Goal, User

router = APIRouter(prefix="/goals", tags=["goals"])
Palette = Literal["jade", "azurite", "ochre", "pale"]


class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    category: str = Field(default="other", max_length=20)
    palette_variant: Palette = "jade"
    weekly_target_minutes: int | None = Field(default=None, ge=1, le=10080)


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=20)
    palette_variant: Palette | None = None
    weekly_target_minutes: int | None = Field(default=None, ge=1, le=10080)
    sort_order: int | None = None


def goal_data(goal: Goal) -> dict:
    return {
        "id": goal.id, "name": goal.name, "description": goal.description,
        "category": goal.category, "palette_variant": goal.palette_variant,
        "seed": goal.seed, "weekly_target_minutes": goal.weekly_target_minutes,
        "status": goal.status, "sort_order": goal.sort_order,
        "unlocked_count": 20, "created_at": goal.created_at.isoformat(),
    }


async def owned_goal(goal_id: str, user: User, db: AsyncSession) -> Goal:
    goal = await db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id))
    if goal is None:
        raise HTTPException(status_code=404, detail="目标不存在")
    return goal


@router.get("")
async def list_goals(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    rows = await db.scalars(select(Goal).where(Goal.user_id == user.id, Goal.status == "active").order_by(Goal.sort_order, Goal.created_at))
    return {"data": [goal_data(goal) for goal in rows]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_goal(body: GoalCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="目标名称不能为空")
    goal = Goal(user_id=user.id, name=name, description=body.description, category=body.category,
                palette_variant=body.palette_variant, weekly_target_minutes=body.weekly_target_minutes,
                seed="", status="active")
    db.add(goal)
    await db.flush()
    goal.seed = goal.id
    await db.commit()
    await db.refresh(goal)
    return {"data": goal_data(goal)}


@router.get("/{goal_id}")
async def get_goal(goal_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    return {"data": goal_data(await owned_goal(goal_id, user, db))}


@router.patch("/{goal_id}")
async def update_goal(goal_id: str, body: GoalUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    goal = await owned_goal(goal_id, user, db)
    if goal.status != "active":
        raise HTTPException(status_code=409, detail="已归档目标不可修改")
    changes = body.model_dump(exclude_unset=True)
    for required in ("name", "category", "palette_variant", "sort_order"):
        if required in changes and changes[required] is None:
            raise HTTPException(status_code=422, detail=f"{required} 不能为空")
    if "name" in changes:
        changes["name"] = changes["name"].strip()
        if not changes["name"]:
            raise HTTPException(status_code=422, detail="目标名称不能为空")
    for key, value in changes.items():
        setattr(goal, key, value)
    await db.commit()
    await db.refresh(goal)
    return {"data": goal_data(goal)}


@router.delete("/{goal_id}")
async def archive_goal(goal_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    goal = await owned_goal(goal_id, user, db)
    goal.status = "archived"
    await db.commit()
    return {"data": {"ok": True}}
