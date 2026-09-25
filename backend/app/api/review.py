from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Goal, ReviewItem, User
from app.review.service import apply_review, due_reviews, review_data

router = APIRouter(prefix="/review-items", tags=["review"])


class ReviewCreate(BaseModel):
    knowledge_point: str = Field(min_length=1, max_length=500)
    goal_id: str | None = None
    mastery: int = Field(default=3, ge=0, le=5)


class ReviewScore(BaseModel):
    quality: int = Field(ge=0, le=5)


async def owned_item(item_id: str, user: User, db: AsyncSession) -> ReviewItem:
    item = await db.scalar(select(ReviewItem).where(ReviewItem.id == item_id, ReviewItem.user_id == user.id))
    if item is None:
        raise HTTPException(status_code=404, detail="复习卡不存在")
    return item


@router.get("")
async def list_review_items(due: bool = False, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if due:
        return {"data": [review_data(item) for item in await due_reviews(db, user.id)]}
    rows = await db.scalars(select(ReviewItem).where(ReviewItem.user_id == user.id).order_by(ReviewItem.due_date).limit(200))
    return {"data": [review_data(item) for item in rows]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_review_item(body: ReviewCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if body.goal_id and not await db.scalar(select(Goal.id).where(Goal.id == body.goal_id, Goal.user_id == user.id)):
        raise HTTPException(status_code=404, detail="目标不存在")
    item = await apply_review(db, user.id, body.knowledge_point, body.mastery, body.goal_id)
    await db.commit()
    return {"data": review_data(item)}


@router.post("/{item_id}/review")
async def score_review_item(item_id: str, body: ReviewScore, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await owned_item(item_id, user, db)
    updated = await apply_review(db, user.id, item.knowledge_point, body.quality, item.goal_id)
    await db.commit()
    return {"data": review_data(updated)}


@router.delete("/{item_id}")
async def delete_review_item(item_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await owned_item(item_id, user, db)
    await db.delete(item)
    await db.commit()
    return {"data": {"ok": True}}
