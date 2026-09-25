from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import AgentRun, AgentStep, AgentToolCall, User

router = APIRouter(prefix="/observatory", tags=["observatory"])

FINISHED_STATUSES = ("completed", "failed", "cancelled", "rejected")


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return round(prompt_tokens / 1000 * settings.token_price_input_per_1k
                 + completion_tokens / 1000 * settings.token_price_output_per_1k, 4)


@router.get("/metrics")
async def observatory_metrics(days: int = Query(default=14, ge=1, le=90),
                              user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    since = datetime.now().astimezone() - timedelta(days=days)
    runs = list(await db.scalars(select(AgentRun).where(AgentRun.user_id == user.id, AgentRun.created_at >= since)
                                 .order_by(AgentRun.created_at.desc())))
    finished = [run for run in runs if run.status in FINISHED_STATUSES]
    succeeded = [run for run in runs if run.status == "completed"]
    prompt_total = sum(run.prompt_tokens for run in runs)
    completion_total = sum(run.completion_tokens for run in runs)

    by_day: dict[str, dict] = {}
    for run in runs:
        day = run.created_at.astimezone().date().isoformat()
        bucket = by_day.setdefault(day, {"date": day, "runs": 0, "prompt_tokens": 0, "completion_tokens": 0})
        bucket["runs"] += 1
        bucket["prompt_tokens"] += run.prompt_tokens
        bucket["completion_tokens"] += run.completion_tokens
    daily = []
    for bucket in sorted(by_day.values(), key=lambda item: item["date"]):
        daily.append({**bucket, "estimated_cost": estimate_cost(bucket["prompt_tokens"], bucket["completion_tokens"])})

    tool_rows = (await db.execute(
        select(AgentToolCall.tool, AgentToolCall.status, AgentToolCall.latency_ms)
        .join(AgentStep, AgentToolCall.step_id == AgentStep.id)
        .join(AgentRun, AgentStep.run_id == AgentRun.id)
        .where(AgentRun.user_id == user.id, AgentRun.created_at >= since))).all()
    by_tool: dict[str, dict] = {}
    for tool, call_status, latency in tool_rows:
        bucket = by_tool.setdefault(tool, {"tool": tool, "calls": 0, "succeeded": 0, "latencies": []})
        bucket["calls"] += 1
        if call_status == "completed":
            bucket["succeeded"] += 1
        if latency is not None:
            bucket["latencies"].append(latency)
    tools = [{"tool": bucket["tool"], "calls": bucket["calls"],
              "success_rate": round(bucket["succeeded"] / bucket["calls"], 3) if bucket["calls"] else 0,
              "avg_latency_ms": round(sum(bucket["latencies"]) / len(bucket["latencies"])) if bucket["latencies"] else None}
             for bucket in sorted(by_tool.values(), key=lambda item: -item["calls"])]

    recent = []
    for run in runs[:10]:
        duration_ms = None
        if run.started_at and run.completed_at:
            duration_ms = round((run.completed_at - run.started_at).total_seconds() * 1000)
        recent.append({"id": run.id, "goal": run.goal[:120], "role": run.role, "status": run.status,
                       "current_step": run.current_step, "prompt_tokens": run.prompt_tokens,
                       "completion_tokens": run.completion_tokens,
                       "estimated_cost": estimate_cost(run.prompt_tokens, run.completion_tokens),
                       "duration_ms": duration_ms, "created_at": run.created_at.isoformat()})

    return {"data": {
        "days": days,
        "totals": {"runs": len(runs), "finished": len(finished),
                   "success_rate": round(len(succeeded) / len(finished), 3) if finished else None,
                   "prompt_tokens": prompt_total, "completion_tokens": completion_total,
                   "estimated_cost": estimate_cost(prompt_total, completion_total)},
        "daily": daily,
        "tools": tools,
        "recent_runs": recent,
        "price_note": "成本按配置单价估算(元),仅用于趋势参考",
    }}
