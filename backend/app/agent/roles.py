from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

RoleName = Literal["Planner", "Executor", "Reflector", "Curator", "Scout"]
AutonomyLevel = Literal["L0", "L1", "L2"]


@dataclass(frozen=True)
class RoleDef:
    label: str
    purpose: str
    tools: tuple[str, ...]
    handoff: tuple[str, ...]


ROLES: dict[str, RoleDef] = {
    "Planner": RoleDef("规划者", "分析学情、制定计划并拆分任务", ("createPlan", "getMyPlans", "breakdownPlanTasks", "getPlanTasks", "getStudyStats"), ("Executor", "Scout", "Reflector")),
    "Executor": RoleDef("执行者", "推进任务、整理待办并记录学习进展", ("updateTaskStatus", "getTodayTasks", "getMyTodos", "createTodo", "updateTodo"), ("Reflector", "Planner")),
    "Reflector": RoleDef("复盘者", "复盘近期投入、打卡与学习节奏", ("getRecentCheckins", "analyzeFocusRhythm", "getStudyStats"), ("Planner", "Scout", "Curator")),
    "Curator": RoleDef("记忆官", "整理长期记忆与学习资料", ("getMyMemories", "searchKnowledgeBase", "curateMemory"), ("Scout", "Planner")),
    "Scout": RoleDef("向导", "发现待复习内容并安排提醒", ("scheduleReview", "getTodayTasks", "getMyTodos"), ("Executor", "Reflector")),
}


class DelegateInput(BaseModel):
    role: RoleName
    context: str = Field(min_length=1, max_length=1000)


def route_role(goal: str) -> str:
    text = goal.casefold()
    if any(word in text for word in ("记忆", "知识库", "资料", "笔记", "知识点")):
        return "Curator"
    if any(word in text for word in ("复盘", "总结", "统计", "节奏", "分析")):
        return "Reflector"
    if any(word in text for word in ("复习", "提醒", "到期", "间隔")):
        return "Scout"
    if any(word in text for word in ("待办", "任务", "专注", "打卡", "执行")):
        return "Executor"
    return "Planner"


def tools_for_role(role: str, specs: list) -> list:
    return [spec for spec in specs if role in spec.roles]


def needs_approval(risk: str, autonomy: str) -> bool:
    if risk == "read":
        return False
    if risk == "write-high":
        return True
    return autonomy == "L0"


def role_prompt(role: str) -> str:
    definition = ROLES[role]
    return (
        f"你当前担任山程的{definition.label}（{role}）。{definition.purpose}。"
        "只处理职责范围内的学习事务；先查询，再按权限调用工具。"
        "需要其他角色处理时使用 delegateToRole 并交代精简上下文。"
        "不要臆造工具结果，也不要声称未执行的写入已经完成。"
    )


def delegate_schema(role: str) -> dict:
    choices = list(ROLES[role].handoff)
    schema = DelegateInput.model_json_schema()
    schema["properties"]["role"]["enum"] = choices
    return {"type": "function", "function": {
        "name": "delegateToRole",
        "description": "把子任务交给具备相应职责的另一个 Agent 角色。",
        "parameters": schema,
    }}
