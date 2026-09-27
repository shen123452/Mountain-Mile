"""One-shot seed of synthetic demo data (demo video / acceptance demos).

Usage (from the backend directory, with the app venv):
    .venv/Scripts/python.exe scripts/seed_demo.py        # idempotent: seeds only when empty
    .venv/Scripts/python.exe scripts/seed_demo.py --wipe # delete the demo user's data, reseed

Everything written belongs to demo@shancheng.local and is clearly synthetic.
Account: demo@shancheng.local / demo-pass-123 (autonomy L2 so agent runs flow hands-free).
"""
from __future__ import annotations

import asyncio
import random
import sys
from pathlib import Path

# Make `app` importable when run as a plain script from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import Checkin, FocusSession, Goal, ReviewItem, User, UserMemory
from app.models.user import new_id

EMAIL = "demo@shancheng.local"
PASSWORD = "demo-pass-123"
NAME = "Demo Learner"
DAYS = 35


def _today() -> datetime:
    return datetime.now(timezone.utc)


async def ensure_user(db) -> str:
    user = (await db.execute(select(User).where(User.email == EMAIL))).scalar_one_or_none()
    if user is None:
        user = User(email=EMAIL, name=NAME, password_hash=hash_password(PASSWORD), autonomy="L2")
        db.add(user)
        await db.flush()
    user.autonomy = "L2"
    await db.commit()
    return user.id


async def wipe(db, user_id: str) -> None:
    await db.execute(delete(User).where(User.id == user_id))  # cascades to all user data
    await db.commit()


def seed_payloads(rng: random.Random) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    today = date.today()
    start = today - timedelta(days=DAYS)

    goals = [
        {"key": "g1", "name": "软考：64 点 DFT 攻坚", "category": "exam", "palette_variant": "jade",
         "seed": "demo-dft-64", "weekly_target_minutes": 180, "sort_order": 0},
        {"key": "g2", "name": "短链服务后端", "category": "project", "palette_variant": "azurite",
         "seed": "demo-shortlink", "weekly_target_minutes": 120, "sort_order": 1},
        {"key": "g3", "name": "西语口语练习", "category": "language", "palette_variant": "ochre",
         "seed": "demo-spanish", "weekly_target_minutes": 60, "sort_order": 2},
    ]

    focus: list[dict] = []
    for offset in range(DAYS):
        day = start + timedelta(days=offset)
        weekday = day.weekday() < 5
        if weekday and rng.random() < 0.4:
            n = 1 + rng.randint(0, 1)
            for i in range(n):
                mins = rng.choice([25, 35, 50])
                focus.append({"goal": "g1", "day": day, "minutes": mins, "hour": 9 + i * 3})
        if weekday and rng.random() < 0.15:
            focus.append({"goal": "g2", "day": day, "minutes": rng.choice([30, 45, 50]), "hour": 20})
        if not weekday and rng.random() < 0.5:
            focus.append({"goal": "g2", "day": day, "minutes": rng.choice([40, 50]), "hour": 10})
        if not weekday and rng.random() < 0.5:
            focus.append({"goal": "g3", "day": day, "minutes": rng.choice([20, 30]), "hour": 15})
        if weekday and rng.random() < 0.1:
            focus.append({"goal": "g3", "day": day, "minutes": 20, "hour": 21})

    checkin_days = sorted(rng.sample(range(DAYS), 18))
    moods = ["good", "steady", "tired"]
    notes = ["今天把 DFT 的抽取法画了一遍，倍速回忆 25 分钟。", "短链接口加了限流，测试全绿。",
             "口语跟读 20 分钟，发音还是偏快。", "复盘本周：软考推进最稳的一周。", "状态一般，只做了一组番茄钟。"]
    checkins = [
        {"day": start + timedelta(days=d), "goal": rng.choice(["g1", "g1", "g3"]),
         "mood": moods[d % 3], "content": notes[d % len(notes)]}
        for d in checkin_days
    ]

    reviews = [
        {"goal": "g1", "kp": "DFT：16 点加零到 64 点时，时间抽取法的蝶形分组如何变化？",
         "ease": 2.5, "reps": 0, "interval": 0, "due": 0, "quality": None},
        {"goal": "g2", "kp": "HTTP 401 与 407 对客户端重试策略的影响分别是什么？",
         "ease": 2.3, "reps": 1, "interval": 0, "due": 0, "quality": 3},
        {"goal": "g3", "kp": "ser 与 estar 在「进行时 + 状态」语境中的取舍",
         "ease": 2.6, "reps": 1, "interval": 2, "due": 2, "quality": 4},
        {"goal": "g1", "kp": "DFT 栅栏函数：周期 64 的序列做 64 点 DFT 只有 k=0 非零，为什么？",
         "ease": 2.8, "reps": 3, "interval": 5, "due": 5, "quality": 4},
        {"goal": "g2", "kp": "短链 A/B 实验中，点击率与落地页转化的归因窗口如何设定？",
         "ease": 2.5, "reps": 2, "interval": 10, "due": 10, "quality": 3},
        {"goal": "g3", "kp": "西语虚拟式：对已发生事实的怀疑用未完成虚拟式过去时",
         "ease": 2.5, "reps": 0, "interval": 21, "due": 21, "quality": None},
    ]

    memories = [
        {"type": "preference", "content": "用户备考软考，主攻 64 点 DFT；偏好 25-50 分钟短专注块，晚间 9 点后效率下降。",
         "importance": 0.8, "confidence": 0.9, "source": "planner", "used_days": 3, "use_count": 5},
        {"type": "insight", "content": "用户状态好时西语练习放在周末更稳，工作日容易被软考挤掉。",
         "importance": 0.6, "confidence": 0.75, "source": "reflector", "used_days": 7, "use_count": 2},
        {"type": "fact", "content": "短链项目技术栈为 FastAPI + SQLAlchemy，部署在阿里云 ECS，容器单实例跑 APScheduler。",
         "importance": 0.7, "confidence": 0.8, "source": "executor", "used_days": 1, "use_count": 3},
    ]
    return goals, focus, checkins, reviews, memories


async def seed(db, user_id: str) -> None:
    rng = random.Random(20260927)
    goals, focus, checkins, reviews, memories = seed_payloads(rng)

    goal_ids: dict[str, str] = {}
    for g in goals:
        goal = Goal(
            id=new_id(), user_id=user_id, name=g["name"], category=g["category"],
            palette_variant=g["palette_variant"], seed=g["seed"],
            description=f"{g['name']}（演示合成数据）", weekly_target_minutes=g["weekly_target_minutes"],
            status="active", sort_order=g["sort_order"],
            start_date=datetime.combine(date.today() - timedelta(days=42), datetime.min.time(), tzinfo=timezone.utc),
        )
        db.add(goal)
        await db.flush()
        goal_ids[g["key"]] = goal.id

    now = _today()
    for f in focus:
        started = datetime.combine(f["day"], datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=f["hour"])
        db.add(FocusSession(
            id=new_id(), user_id=user_id, goal_id=goal_ids[f["goal"]],
            planned_minutes=f["minutes"], actual_minutes=f["minutes"],
            mode="pomodoro", completed=True,
            note="演示合成数据" if rng.random() < 0.3 else None,
            started_at=min(started, now - timedelta(minutes=30)),
            ended_at=min(started + timedelta(minutes=f["minutes"]), now - timedelta(minutes=5)),
        ))

    for c in checkins:
        db.add(Checkin(
            id=new_id(), user_id=user_id, goal_id=goal_ids.get(c["goal"]),
            mood=c["mood"], content=c["content"], checkin_date=c["day"],
        ))

    for r in reviews:
        db.add(ReviewItem(
            id=new_id(), user_id=user_id, goal_id=goal_ids.get(r["goal"]),
            knowledge_point=r["kp"], ease=r["ease"], repetitions=r["reps"],
            interval_days=r["interval"], due_date=date.today() + timedelta(days=r["due"]),
            last_quality=r["quality"],
            last_reviewed_at=(now - timedelta(days=max(1, r["interval"]))) if r["quality"] else None,
        ))

    for m in memories:
        db.add(UserMemory(
            id=new_id(), user_id=user_id, memory_type=m["type"], content=m["content"],
            importance=m["importance"], confidence=m["confidence"], source=m["source"],
            use_count=m["use_count"], last_used=now - timedelta(days=m["used_days"]),
        ))
    await db.commit()
    print(f"seeded: {len(goals)} goals, {len(focus)} focus sessions, {len(checkins)} checkins, {len(reviews)} reviews, {len(memories)} memories for {EMAIL}")


async def main() -> int:
    wipe_it = "--wipe" in sys.argv[1:]
    async with AsyncSessionLocal() as db:
        user_id = await ensure_user(db)
        if wipe_it:
            await wipe(db, user_id)
            user_id = await ensure_user(db)
        existing = (await db.execute(
            select(Goal).where(Goal.user_id == user_id, Goal.status == "active"))).scalars().all()
        if existing:
            print(f"demo user already has {len(existing)} goals; skip seeding (use --wipe to reseed)")
            return 0
        await seed(db, user_id)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
