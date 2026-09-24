from dataclasses import dataclass
from datetime import date
from typing import Awaitable, Callable, Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Goal, Plan, PlanTask, Todo


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
    return {"tasks": [{"id": row.id, "title": row.title, "due_date": row.due_date.isoformat() if row.due_date else None} for row in rows]}


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


async def not_ready(_ctx: ToolContext, _data: BaseModel) -> dict:
    return {"available": False, "reason": "所需学习数据将在后续里程碑接入"}


SPECS = [
    ToolSpec("createPlan", "创建学习计划", "write-high", CreatePlanInput, create_plan),
    ToolSpec("getMyPlans", "查询我的计划", "read", EmptyInput, get_plans),
    ToolSpec("breakdownPlanTasks", "将计划拆解为任务并去重", "write-high", BreakdownInput, breakdown),
    ToolSpec("getPlanTasks", "查询计划任务", "read", PlanIdInput, get_plan_tasks),
    ToolSpec("updateTaskStatus", "更新任务状态", "write-low", TaskStatusInput, update_task),
    ToolSpec("getTodayTasks", "查询今日到期任务", "read", EmptyInput, today_tasks),
    ToolSpec("getMyTodos", "查询待办", "read", EmptyInput, get_todos),
    ToolSpec("createTodo", "创建待办", "write-low", TodoCreateInput, create_todo),
    ToolSpec("updateTodo", "更新待办", "write-low", TodoUpdateInput, update_todo),
    ToolSpec("deleteTodo", "删除待办", "write-high", TodoIdInput, delete_todo),
    ToolSpec("getRecentCheckins", "查询近期打卡", "read", RecentInput, not_ready),
    ToolSpec("getMyMemories", "查询长期记忆", "read", SearchInput, not_ready),
    ToolSpec("getStudyStats", "查询学习统计", "read", EmptyInput, not_ready),
    ToolSpec("searchKnowledgeBase", "搜索个人知识库", "read", SearchInput, not_ready),
]
REGISTRY = {spec.name: spec for spec in SPECS}
