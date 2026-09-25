from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Plan, PlanTask, Todo, User

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
async def list_tasks(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """当前待办(独立待办 + 计划任务),供工作台侧栏展示。归档/完成的不显示。"""
    todos = (await db.scalars(select(Todo).where(Todo.user_id == user.id, Todo.status == "open").limit(50))).all()
    plan_tasks = (await db.scalars(select(PlanTask).join(Plan, PlanTask.plan_id == Plan.id).where(
        Plan.user_id == user.id, PlanTask.status.notin_(["done", "archived"])).limit(50))).all()
    return {"data": {
        "todos": [{"id": item.id, "title": item.title, "due_date": item.due_date.isoformat() if item.due_date else None} for item in todos],
        "plan_tasks": [{"id": item.id, "title": item.title, "due_date": item.due_date.isoformat() if item.due_date else None} for item in plan_tasks],
    }}


@router.post("/todos/{todo_id}/toggle")
async def toggle_todo(todo_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    todo = await db.scalar(select(Todo).where(Todo.id == todo_id, Todo.user_id == user.id))
    if todo is None:
        raise HTTPException(status_code=404, detail="待办不存在")
    todo.status = "done" if todo.status == "open" else "open"
    await db.commit()
    return {"data": {"id": todo.id, "status": todo.status}}


@router.post("/plan-tasks/{task_id}/toggle")
async def toggle_plan_task(task_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task = await db.scalar(select(PlanTask).join(Plan, PlanTask.plan_id == Plan.id).where(
        PlanTask.id == task_id, Plan.user_id == user.id))
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.status = "done" if task.status != "done" else "todo"
    await db.commit()
    return {"data": {"id": task.id, "status": task.status}}


@router.post("/todos/{todo_id}/archive")
async def archive_todo(todo_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    todo = await db.scalar(select(Todo).where(Todo.id == todo_id, Todo.user_id == user.id))
    if todo is None:
        raise HTTPException(status_code=404, detail="待办不存在")
    todo.status = "archived"
    await db.commit()
    return {"data": {"id": todo.id, "status": todo.status}}


@router.delete("/todos/{todo_id}")
async def delete_todo(todo_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    todo = await db.scalar(select(Todo).where(Todo.id == todo_id, Todo.user_id == user.id))
    if todo is None:
        raise HTTPException(status_code=404, detail="待办不存在")
    await db.delete(todo)
    await db.commit()
    return {"data": {"ok": True}}


@router.post("/plan-tasks/{task_id}/archive")
async def archive_plan_task(task_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task = await db.scalar(select(PlanTask).join(Plan, PlanTask.plan_id == Plan.id).where(
        PlanTask.id == task_id, Plan.user_id == user.id))
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.status = "archived"
    await db.commit()
    return {"data": {"id": task.id, "status": task.status}}


@router.delete("/plan-tasks/{task_id}")
async def delete_plan_task(task_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task = await db.scalar(select(PlanTask).join(Plan, PlanTask.plan_id == Plan.id).where(
        PlanTask.id == task_id, Plan.user_id == user.id))
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    await db.delete(task)
    await db.commit()
    return {"data": {"ok": True}}
