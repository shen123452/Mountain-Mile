from dataclasses import dataclass
from datetime import date, timedelta
from typing import Awaitable, Callable, Literal

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Checkin, FocusSession, Goal, Plan, PlanTask, ReviewItem, Todo, UserMemory
from app.knowledge.service import embed, find_memory_duplicate, search_chunks, search_memories
from app.review.service import apply_review, due_reviews, review_data
from app.api.reports import summary_for_period
from app.core.security import utc_now


@dataclass
class ToolContext:
    user_id: str
    db: AsyncSession


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    risk: Literal["read", "write-low", "write-high"]
    input_model: type[BaseModel]
    handler: Callable[[ToolContext, BaseModel], Awaitable[dict]]
    roles: tuple[str, ...] = ("Planner", "Executor", "Reflector", "Curator", "Scout")

    def schema(self) -> dict:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.input_model.model_json_schema()}}


class EmptyInput(BaseModel):
    pass


class CreatePlanInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    goal_id: str | None = None
    description: str | None = None


class PlanIdInput(BaseModel):
    plan_id: str


class BreakdownInput(PlanIdInput):
    tasks: list[str] = Field(min_length=1, max_length=30)


class TaskStatusInput(BaseModel):
    task_id: str
    status: Literal["todo", "in_progress", "done"]


class TodoCreateInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_date: date | None = None


class TodoUpdateInput(BaseModel):
    todo_id: str
    title: str | None = None
    status: Literal["open", "done"] | None = None
    due_date: date | None = None


class TodoIdInput(BaseModel):
    todo_id: str


class SearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class RecentInput(BaseModel):
    days: int = Field(default=7, ge=1, le=90)


class GoalIdInput(BaseModel):
    goal_id: str


class ReviewInput(BaseModel):
    knowledge_point: str = Field(min_length=1, max_length=500)
    mastery: int = Field(default=3, ge=0, le=5)


class CurateInput(BaseModel):
    context: str = Field(min_length=1, max_length=2000)


async def create_plan(ctx: ToolContext, data: CreatePlanInput) -> dict:
    if data.goal_id and not await ctx.db.scalar(select(Goal.id).where(Goal.id == data.goal_id, Goal.user_id == ctx.user_id)):
        return {"error": "目标不存在"}
    plan = Plan(user_id=ctx.user_id, goal_id=data.goal_id, name=data.name.strip(), description=data.description)
    ctx.db.add(plan)
    await ctx.db.flush()
    return {"plan_id": plan.id, "name": plan.name}


async def get_plans(ctx: ToolContext, _data: EmptyInput) -> dict:
    rows = await ctx.db.scalars(select(Plan).where(Plan.user_id == ctx.user_id, Plan.status == "active"))
    return {"plans": [{"id": row.id, "name": row.name, "goal_id": row.goal_id} for row in rows]}


async def breakdown(ctx: ToolContext, data: BreakdownInput) -> dict:
    plan = await ctx.db.scalar(select(Plan).where(Plan.id == data.plan_id, Plan.user_id == ctx.user_id))
    if not plan:
        return {"error": "计划不存在"}
    existing = set(await ctx.db.scalars(select(PlanTask.title).where(PlanTask.plan_id == plan.id)))
    created = []
    for title in data.tasks:
        title = title.strip()
        if title and title not in existing:
            task = PlanTask(plan_id=plan.id, goal_id=plan.goal_id, title=title)
            ctx.db.add(task)
            created.append(title)
            existing.add(title)
    return {"created": created}


async def get_plan_tasks(ctx: ToolContext, data: PlanIdInput) -> dict:
    plan = await ctx.db.scalar(select(Plan).where(Plan.id == data.plan_id, Plan.user_id == ctx.user_id))
    if not plan:
        return {"error": "计划不存在"}
    rows = await ctx.db.scalars(select(PlanTask).where(PlanTask.plan_id == plan.id))
    return {"tasks": [{"id": row.id, "title": row.title, "status": row.status} for row in rows]}


async def update_task(ctx: ToolContext, data: TaskStatusInput) -> dict:
    task = await ctx.db.scalar(select(PlanTask).join(Plan, PlanTask.plan_id == Plan.id).where(PlanTask.id == data.task_id, Plan.user_id == ctx.user_id))
    if not task:
        return {"error": "任务不存在"}
    task.status = data.status
    return {"task_id": task.id, "status": task.status}


async def today_tasks(ctx: ToolContext, _data: EmptyInput) -> dict:
    rows = await ctx.db.scalars(select(PlanTask).join(Plan, PlanTask.plan_id == Plan.id).where(Plan.user_id == ctx.user_id, PlanTask.status != "done", PlanTask.due_date <= date.today()).limit(50))
    reviews = await due_reviews(ctx.db, ctx.user_id)
    return {"tasks": [{"id": row.id, "title": row.title, "due_date": row.due_date.isoformat() if row.due_date else None} for row in rows],
            "due_reviews": [review_data(item) for item in reviews]}


async def get_todos(ctx: ToolContext, _data: EmptyInput) -> dict:
    rows = await ctx.db.scalars(select(Todo).where(Todo.user_id == ctx.user_id, Todo.status == "open").limit(50))
    return {"todos": [{"id": row.id, "title": row.title} for row in rows]}


async def create_todo(ctx: ToolContext, data: TodoCreateInput) -> dict:
    todo = Todo(user_id=ctx.user_id, title=data.title.strip(), due_date=data.due_date)
    ctx.db.add(todo)
    await ctx.db.flush()
    return {"todo_id": todo.id, "title": todo.title}


async def update_todo(ctx: ToolContext, data: TodoUpdateInput) -> dict:
    todo = await ctx.db.scalar(select(Todo).where(Todo.id == data.todo_id, Todo.user_id == ctx.user_id))
    if not todo:
        return {"error": "待办不存在"}
    for key in ("title", "status", "due_date"):
        value = getattr(data, key)
        if value is not None:
            setattr(todo, key, value)
    return {"todo_id": todo.id, "status": todo.status, "title": todo.title}


async def delete_todo(ctx: ToolContext, data: TodoIdInput) -> dict:
    todo = await ctx.db.scalar(select(Todo).where(Todo.id == data.todo_id, Todo.user_id == ctx.user_id))
    if not todo:
        return {"error": "待办不存在"}
    await ctx.db.delete(todo)
    return {"deleted": True}


async def recent_checkins(ctx: ToolContext, data: RecentInput) -> dict:
    since = date.today() - timedelta(days=data.days - 1)
    rows = await ctx.db.scalars(select(Checkin).where(Checkin.user_id == ctx.user_id, Checkin.checkin_date >= since).order_by(Checkin.checkin_date.desc()))
    return {"days": data.days, "checkins": [{"date": row.checkin_date.isoformat(), "mood": row.mood, "content": row.content} for row in rows]}


async def study_stats(ctx: ToolContext, _data: EmptyInput) -> dict:
    today = date.today()
    return await summary_for_period(ctx.user_id, ctx.db, today - timedelta(days=6), today)


async def schedule_review(ctx: ToolContext, data: ReviewInput) -> dict:
    item = await apply_review(ctx.db, ctx.user_id, data.knowledge_point, data.mastery)
    return {"review_item_id": item.id, "knowledge_point": item.knowledge_point, "due_date": item.due_date.isoformat(), "interval_days": item.interval_days, "repetitions": item.repetitions}


async def focus_rhythm(ctx: ToolContext, data: RecentInput) -> dict:
    """近 N 天专注节律:完成率、时段分布(按服务器时区小时聚合)、最佳时段。"""
    since = utc_now() - timedelta(days=data.days)
    rows = list(await ctx.db.scalars(select(FocusSession).where(FocusSession.user_id == ctx.user_id, FocusSession.started_at >= since)))
    completed = [row for row in rows if row.completed]
    by_hour: dict[int, int] = {}
    for row in completed:
        by_hour[row.started_at.hour] = by_hour.get(row.started_at.hour, 0) + row.actual_minutes
    total_minutes = sum(row.actual_minutes for row in completed)
    return {
        "days": data.days,
        "total_sessions": len(rows),
        "completed_sessions": len(completed),
        "completion_rate": round(len(completed) / len(rows), 3) if rows else 0,
        "total_minutes": total_minutes,
        "avg_minutes_per_day": round(total_minutes / data.days, 1),
        "best_hour": max(by_hour, key=by_hour.get) if by_hour else None,
        "minutes_by_hour": {str(hour): by_hour[hour] for hour in sorted(by_hour)},
    }


TERRAIN_TOTAL_TILES = 221


async def forecast_goal(ctx: ToolContext, data: GoalIdInput) -> dict:
    """按当前生长速度与近 14 天日均专注,线性外推山屿点满时间。"""
    goal = await ctx.db.scalar(select(Goal).where(Goal.id == data.goal_id, Goal.user_id == ctx.user_id))
    if not goal:
        return {"error": "目标不存在"}
    from app.api.focus import growth_for_goal  # 延迟导入,避免 API 层与工具层循环依赖
    unlocked = await growth_for_goal(goal.id, goal.user_id, ctx.db)
    remaining = max(0, TERRAIN_TOTAL_TILES - unlocked)
    since = utc_now() - timedelta(days=14)
    minutes = await ctx.db.scalar(select(func.coalesce(func.sum(FocusSession.actual_minutes), 0)).where(
        FocusSession.goal_id == goal.id, FocusSession.user_id == ctx.user_id, FocusSession.completed, FocusSession.started_at >= since))
    daily_minutes = (minutes or 0) / 14
    eta = None
    if daily_minutes > 0 and remaining > 0:
        eta = (date.today() + timedelta(days=round(remaining * 8 / daily_minutes))).isoformat()
    return {"goal_id": goal.id, "unlocked": unlocked, "total": TERRAIN_TOTAL_TILES,
            "progress": round(unlocked / TERRAIN_TOTAL_TILES, 3),
            "daily_focus_minutes": round(daily_minutes, 1), "estimated_completion": eta}


OVERLOAD_ACTIVE_GOALS = 5
OVERLOAD_OPEN_TODOS = 12
OVERLOAD_DUE_TASKS = 8


async def detect_overload(ctx: ToolContext, data: GoalIdInput) -> dict:
    """整体过载检测;goal_id 传 "all" 或任意值均可,若对应真实目标会附带其到期任务数。"""
    active_goals = await ctx.db.scalar(select(func.count(Goal.id)).where(Goal.user_id == ctx.user_id, Goal.status == "active")) or 0
    open_todos = await ctx.db.scalar(select(func.count(Todo.id)).where(Todo.user_id == ctx.user_id, Todo.status == "open")) or 0
    due_tasks = await ctx.db.scalar(select(func.count(PlanTask.id)).join(Plan, PlanTask.plan_id == Plan.id).where(
        Plan.user_id == ctx.user_id, PlanTask.status != "done", PlanTask.due_date <= date.today())) or 0
    due_reviews_count = len(await due_reviews(ctx.db, ctx.user_id))
    signals = []
    if active_goals > OVERLOAD_ACTIVE_GOALS:
        signals.append(f"并行目标 {active_goals} 个,超过建议上限 {OVERLOAD_ACTIVE_GOALS}")
    if open_todos > OVERLOAD_OPEN_TODOS:
        signals.append(f"待办积压 {open_todos} 条,超过 {OVERLOAD_OPEN_TODOS}")
    if due_tasks > OVERLOAD_DUE_TASKS:
        signals.append(f"今日到期任务 {due_tasks} 个,单日难以完成")
    if due_reviews_count > 10:
        signals.append(f"到期复习 {due_reviews_count} 张,建议分批处理")
    goal_extra = None
    if data.goal_id != "all":
        goal = await ctx.db.scalar(select(Goal).where(Goal.id == data.goal_id, Goal.user_id == ctx.user_id))
        if goal:
            goal_due = await ctx.db.scalar(select(func.count(PlanTask.id)).where(
                PlanTask.goal_id == goal.id, PlanTask.status != "done", PlanTask.due_date <= date.today())) or 0
            goal_extra = {"goal_id": goal.id, "name": goal.name, "due_tasks": goal_due}
    return {"overloaded": bool(signals), "active_goals": active_goals, "open_todos": open_todos,
            "due_tasks_today": due_tasks, "due_reviews": due_reviews_count, "signals": signals,
            "goal": goal_extra,
            "suggestion": "暂停新增目标,先清空今日到期任务与复习" if signals else "负载健康,可以按计划推进"}


async def get_memories(ctx: ToolContext, data: SearchInput) -> dict:
    rows = await search_memories(ctx.db, ctx.user_id, data.query.strip(), 20)
    return {"memories": [{"id": row.id, "type": row.memory_type, "content": row.content, "importance": row.importance} for row in rows[:20]]}


async def search_knowledge(ctx: ToolContext, data: SearchInput) -> dict:
    return {"available": True, "results": await search_chunks(ctx.db, ctx.user_id, data.query, 5)}


async def curate_memory(ctx: ToolContext, data: CurateInput) -> dict:
    content = data.context.strip()
    duplicate = await find_memory_duplicate(ctx.db, ctx.user_id, content)
    if duplicate:
        duplicate.use_count += 1; duplicate.last_used = utc_now(); await ctx.db.flush()
        return {"merged": True, "memory_id": duplicate.id}
    item = UserMemory(user_id=ctx.user_id, content=content, memory_type="fact", importance=0.5, confidence=0.6, source="curator", embedding=(await embed([content]))[0])
    ctx.db.add(item); await ctx.db.flush()
    return {"merged": False, "memory_id": item.id}


SPECS = [
    ToolSpec("createPlan", "创建学习计划", "write-high", CreatePlanInput, create_plan, ("Planner",)),
    ToolSpec("getMyPlans", "查询我的计划", "read", EmptyInput, get_plans, ("Planner", "Executor", "Reflector")),
    ToolSpec("breakdownPlanTasks", "将计划拆解为任务并去重", "write-high", BreakdownInput, breakdown, ("Planner",)),
    ToolSpec("getPlanTasks", "查询计划任务", "read", PlanIdInput, get_plan_tasks, ("Planner", "Executor", "Reflector")),
    ToolSpec("updateTaskStatus", "更新任务状态", "write-low", TaskStatusInput, update_task, ("Executor",)),
    ToolSpec("getTodayTasks", "查询今日到期任务", "read", EmptyInput, today_tasks, ("Executor", "Scout", "Planner")),
    ToolSpec("getMyTodos", "查询待办", "read", EmptyInput, get_todos, ("Executor", "Scout")),
    ToolSpec("createTodo", "创建待办", "write-low", TodoCreateInput, create_todo, ("Executor", "Scout")),
    ToolSpec("updateTodo", "更新待办", "write-low", TodoUpdateInput, update_todo, ("Executor",)),
    ToolSpec("deleteTodo", "删除待办", "write-high", TodoIdInput, delete_todo, ("Executor",)),
    ToolSpec("getRecentCheckins", "查询近期打卡", "read", RecentInput, recent_checkins, ("Reflector", "Planner")),
    ToolSpec("getMyMemories", "查询长期记忆", "read", SearchInput, get_memories, ("Curator", "Planner")),
    ToolSpec("getStudyStats", "查询学习统计", "read", EmptyInput, study_stats, ("Planner", "Reflector")),
    ToolSpec("searchKnowledgeBase", "搜索个人知识库", "read", SearchInput, search_knowledge, ("Curator", "Planner")),
    ToolSpec("scheduleReview", "安排知识点复习", "write-low", ReviewInput, schedule_review, ("Scout",)),
    ToolSpec("analyzeFocusRhythm", "分析近期专注节奏", "read", RecentInput, focus_rhythm, ("Reflector",)),
    ToolSpec("forecastGoal", "预测目标完成进度", "read", GoalIdInput, forecast_goal, ("Planner", "Reflector")),
    ToolSpec("detectOverload", "检测目标与任务过载", "read", GoalIdInput, detect_overload, ("Planner", "Reflector")),
    ToolSpec("curateMemory", "整理长期记忆", "write-low", CurateInput, curate_memory, ("Curator",)),
]
REGISTRY = {spec.name: spec for spec in SPECS}
