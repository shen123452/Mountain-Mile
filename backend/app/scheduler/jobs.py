from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.agent.orchestrator import observed_messages, run_loop
from app.agent.roles import route_role
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import AgentRun, AgentSchedule, Notification, User
from app.api.reports import weekly_summary
from openai import AsyncOpenAI

APP_TZ = ZoneInfo("Asia/Shanghai")


async def run_due_schedules() -> None:
    now = datetime.now(APP_TZ)
    async with AsyncSessionLocal() as db:
        schedules = list(await db.scalars(select(AgentSchedule).where(AgentSchedule.enabled == True, AgentSchedule.next_run_at <= now)))
        for schedule in schedules:
            user = await db.get(User, schedule.user_id)
            role = route_role(schedule.goal)
            run = AgentRun(user_id=schedule.user_id, goal=schedule.goal, mode="scheduled", role=role, status="queued")
            db.add(run); await db.flush()
            schedule.last_run_at = now
            from apscheduler.triggers.cron import CronTrigger
            schedule.next_run_at = CronTrigger.from_crontab(schedule.cron, timezone=APP_TZ).get_next_fire_time(now, now)
            if not settings.dashscope_api_key:
                run.status = "failed"; run.error = "尚未配置 DashScope API Key"
                db.add(Notification(user_id=schedule.user_id, type="schedule", title="定时向导未执行", content="已记录定时任务，但需要配置 DashScope API Key 后才能运行。", action_url="/agent"))
                continue
            client = AsyncOpenAI(api_key=settings.dashscope_api_key, base_url=settings.llm_base_url)
            try:
                await run_loop(db, run, client, await observed_messages(db, schedule.user_id, schedule.goal, role), user.autonomy if user else "L0")
            finally:
                await client.close()
        await db.commit()


async def create_weekly_notifications() -> None:
    async with AsyncSessionLocal() as db:
        users = list(await db.scalars(select(User)))
        for user in users:
            summary = await weekly_summary(user.id, db)
            title = f"本周学习报告 · {summary['period']['start']} 至 {summary['period']['end']}"
            existing = await db.scalar(select(Notification.id).where(Notification.user_id == user.id, Notification.type == "weekly_report", Notification.title == title))
            if existing is None:
                db.add(Notification(user_id=user.id, type="weekly_report", title=title, content=f"累计 {summary['focus_minutes']} 分钟，完成 {summary['focus_sessions']} 次专注，打卡 {summary['checkins']} 天。", action_url="/reports"))
        await db.commit()


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=APP_TZ)
    scheduler.add_job(run_due_schedules, "interval", minutes=1, id="scheduled-agent-runs", replace_existing=True, coalesce=True)
    scheduler.add_job(create_weekly_notifications, "cron", day_of_week="sun", hour=20, minute=0, id="weekly-report", replace_existing=True, coalesce=True)
    return scheduler
