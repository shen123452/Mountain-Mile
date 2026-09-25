from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import utc_now
from app.models import ReviewItem
from app.review.sm2 import sm2_next


async def apply_review(db: AsyncSession, user_id: str, knowledge_point: str, quality: int,
                       goal_id: str | None = None) -> ReviewItem:
    """按 SM-2 记录一次复习:不存在则建卡,存在则推进排期。"""
    point = knowledge_point.strip()
    item = await db.scalar(select(ReviewItem).where(ReviewItem.user_id == user_id, ReviewItem.knowledge_point == point))
    if item is None:
        item = ReviewItem(user_id=user_id, goal_id=goal_id, knowledge_point=point, due_date=date.today())
        db.add(item)
    # 新卡的 default 值在 flush 后才落库,读取时用 SM-2 初始值兜底
    ease, interval, repetitions = sm2_next(item.ease or 2.5, item.interval_days or 0, item.repetitions or 0, quality)
    item.ease = ease
    item.interval_days = interval
    item.repetitions = repetitions
    item.last_quality = quality
    item.last_reviewed_at = utc_now()
    item.due_date = date.today() + timedelta(days=interval)
    await db.flush()
    return item


async def due_reviews(db: AsyncSession, user_id: str, today: date | None = None, limit: int = 50) -> list[ReviewItem]:
    """查询到期的复习卡(含今天)。"""
    due = today or date.today()
    rows = await db.scalars(select(ReviewItem).where(
        ReviewItem.user_id == user_id, ReviewItem.due_date <= due,
    ).order_by(ReviewItem.due_date, ReviewItem.created_at).limit(limit))
    return list(rows)


def review_data(item: ReviewItem) -> dict:
    return {
        "id": item.id, "knowledge_point": item.knowledge_point, "goal_id": item.goal_id,
        "ease": item.ease, "interval_days": item.interval_days, "repetitions": item.repetitions,
        "due_date": item.due_date.isoformat(), "last_quality": item.last_quality,
        "last_reviewed_at": item.last_reviewed_at.isoformat() if item.last_reviewed_at else None,
    }
