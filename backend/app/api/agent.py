from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import execute_tool, observed_messages, run_loop
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import utc_now
from app.models import AgentApproval, AgentRun, AgentStep, AgentToolCall, User
from app.tools.registry import REGISTRY

router = APIRouter(prefix="/agent/runs", tags=["agent"])


class StartBody(BaseModel):
    goal: str = Field(min_length=1, max_length=2000)


class ApprovalBody(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=500)
    edited_payload: dict | None = None


def run_data(run: AgentRun) -> dict:
    return {"id": run.id, "goal": run.goal, "status": run.status, "current_step": run.current_step,
            "max_steps": run.max_steps, "summary": run.summary, "error": run.error}


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
    llm = llm_client()
    run = AgentRun(user_id=user.id, goal=body.goal.strip(), mode="manual", role="Planner", status="queued")
    db.add(run)
    await db.commit()
    await db.refresh(run)
    try:
        await run_loop(db, run, llm, await observed_messages(db, user.id, run.goal))
    finally:
        await llm.close()
    return {"data": run_data(run)}


@router.get("/{run_id}")
async def get_run(run_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    run = await owned_run(run_id, user, db)
    steps = await db.scalars(select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.step_number))
    approvals = await db.scalars(select(AgentApproval).where(AgentApproval.run_id == run.id).order_by(AgentApproval.created_at))
    return {"data": {**run_data(run), "steps": [{"number": step.step_number, "kind": step.kind, "status": step.status, "title": step.title, "detail": step.detail} for step in steps],
                     "approvals": [{"id": item.id, "status": item.status, "payload": item.payload} for item in approvals]}}


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
        await run_loop(db, run, llm, messages)
    finally:
        await llm.close()
    return {"data": run_data(run)}
