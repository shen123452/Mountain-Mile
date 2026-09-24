from typing import Literal

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import emit, execute_tool, observed_messages, run_loop
from app.agent.roles import route_role
from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.deps import get_current_user
from app.core.security import utc_now
from app.models import AgentApproval, AgentEvent, AgentRun, AgentStep, AgentToolCall, User
from app.tools.registry import REGISTRY

router = APIRouter(prefix="/agent/runs", tags=["agent"])
RUN_TASKS: dict[str, asyncio.Task] = {}


class StartBody(BaseModel):
    goal: str = Field(min_length=1, max_length=2000)


class ApprovalBody(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=500)
    edited_payload: dict | None = None


def run_data(run: AgentRun) -> dict:
    return {"id": run.id, "goal": run.goal, "status": run.status, "current_step": run.current_step,
            "max_steps": run.max_steps, "role": run.role, "summary": run.summary, "error": run.error}


def llm_client() -> AsyncOpenAI:
    if not settings.dashscope_api_key:
        raise HTTPException(status_code=503, detail="尚未配置 DashScope API Key")
    return AsyncOpenAI(api_key=settings.dashscope_api_key, base_url=settings.llm_base_url)


async def owned_run(run_id: str, user: User, db: AsyncSession) -> AgentRun:
    run = await db.scalar(select(AgentRun).where(AgentRun.id == run_id, AgentRun.user_id == user.id))
    if run is None:
        raise HTTPException(status_code=404, detail="运行不存在")
    return run


@router.get("")
async def list_runs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    rows = await db.scalars(select(AgentRun).where(AgentRun.user_id == user.id).order_by(AgentRun.created_at.desc()).limit(50))
    return {"data": [run_data(row) for row in rows]}


@router.post("")
async def create_run(body: StartBody, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    role = route_role(body.goal)
    run = AgentRun(user_id=user.id, goal=body.goal.strip(), mode="manual", role=role, status="queued")
    db.add(run)
    await db.commit()
    await db.refresh(run)
    task = asyncio.create_task(run_agent_background(run.id, user.id, run.goal))
    RUN_TASKS[run.id] = task
    task.add_done_callback(lambda _task: RUN_TASKS.pop(run.id, None))
    return {"data": run_data(run)}


async def run_agent_background(run_id: str, user_id: str, goal: str) -> None:
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        if run is None or run.status == "cancelled": return
        user = await db.get(User, user_id)
        autonomy = user.autonomy if user else "L0"
        try:
            llm = llm_client()
        except Exception as exc:
            run.status = "failed"; run.error = str(exc.detail if isinstance(exc, HTTPException) else exc)
            await emit(db, run, "done", {"status": "failed", "error": run.error}); return
        try:
            await run_loop(db, run, llm, await observed_messages(db, user_id, goal, run.role), autonomy)
        finally:
            await llm.close()


@router.get("/{run_id}")
async def get_run(run_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    run = await owned_run(run_id, user, db)
    steps = await db.scalars(select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.step_number))
    approvals = await db.scalars(select(AgentApproval).where(AgentApproval.run_id == run.id).order_by(AgentApproval.created_at))
    events = await db.scalars(select(AgentEvent).where(AgentEvent.run_id == run.id).order_by(AgentEvent.id))
    return {"data": {**run_data(run), "steps": [{"number": step.step_number, "kind": step.kind, "role": step.agent_role, "status": step.status, "title": step.title, "detail": step.detail} for step in steps],
                     "events": [{"id": event.id, "type": event.type, "payload": event.payload, "created_at": event.created_at.isoformat()} for event in events],
                     "approvals": [{"id": item.id, "status": item.status, "payload": item.payload} for item in approvals]}}


@router.get("/{run_id}/stream")
async def stream_run(run_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_run(run_id, user, db)

    async def events():
        last_id = 0
        while True:
            async with AsyncSessionLocal() as stream_db:
                rows = list(await stream_db.scalars(select(AgentEvent).where(AgentEvent.run_id == run_id, AgentEvent.id > last_id).order_by(AgentEvent.id)))
                run = await stream_db.get(AgentRun, run_id)
            for event in rows:
                last_id = event.id
                yield {"id": str(event.id), "event": event.type, "data": event.payload}
            if run and run.status in ("completed", "failed", "cancelled", "rejected") and not rows:
                break
            await asyncio.sleep(0.4)

    return EventSourceResponse(events(), headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/{run_id}/cancel")
async def cancel_run(run_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run = await owned_run(run_id, user, db)
    if run.status in ("completed", "failed", "cancelled", "rejected"):
        raise HTTPException(status_code=409, detail="运行已结束")
    task = RUN_TASKS.get(run.id)
    if task and not task.done():
        task.cancel()
    else:
        run.status = "cancelled"; run.error = "用户已中断运行"; await db.commit()
    return {"data": run_data(run)}


@router.post("/{run_id}/approval")
async def decide_approval(run_id: str, body: ApprovalBody, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    run = await db.scalar(select(AgentRun).where(AgentRun.id == run_id, AgentRun.user_id == user.id).with_for_update())
    if run is None:
        raise HTTPException(status_code=404, detail="运行不存在")
    if run.status != "awaiting_approval":
        raise HTTPException(status_code=409, detail="运行未等待审批")
    approval = await db.scalar(select(AgentApproval).where(AgentApproval.run_id == run.id, AgentApproval.status == "pending").with_for_update())
    if approval is None:
        raise HTTPException(status_code=409, detail="审批已处理")
    call = await db.get(AgentToolCall, approval.tool_call_id)
    step = await db.get(AgentStep, call.step_id) if call else None
    if call is None or step is None:
        raise HTTPException(status_code=500, detail="审批记录不完整")
    messages = run.state["messages"]
    call_id = run.state["pending_call_id"]
    approval.decided_at = utc_now()
    approval.decision_reason = body.reason
    if body.decision == "reject":
        approval.status = "rejected"
        call.status = "rejected"
        step.status = "rejected"
        run.status = "rejected"
        run.summary = body.reason or "用户拒绝了工具调用"
        run.completed_at = utc_now()
        await db.commit()
        return {"data": run_data(run)}
    spec = REGISTRY[call.tool]
    try:
        data = spec.input_model.model_validate(body.edited_payload if body.edited_payload is not None else approval.payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="修改后的参数不正确") from exc
    approval.status = "approved"
    approval.edited_payload = body.edited_payload
    llm = llm_client()
    await execute_tool(db, run, step, call, spec, data, messages, call_id)
    try:
        await run_loop(db, run, llm, messages, user.autonomy)
    finally:
        await llm.close()
    return {"data": run_data(run)}
