from app.agent.roles import needs_approval, route_role, tools_for_role, ROLES
from app.tools.registry import SPECS


def test_role_router_and_tool_boundaries() -> None:
    assert route_role("帮我制定本周学习计划") == "Planner"
    assert route_role("复盘最近的专注节奏") == "Reflector"
    assert route_role("安排下周的间隔复习") == "Scout"
    assert route_role("整理我的知识库笔记") == "Curator"
    assert route_role("把今日待办标记完成") == "Executor"
    assert "createPlan" in {item.name for item in tools_for_role("Planner", SPECS)}
    assert "createPlan" not in {item.name for item in tools_for_role("Executor", SPECS)}
    assert {"scheduleReview", "getTodayTasks"}.issubset({item.name for item in tools_for_role("Scout", SPECS)})
    assert {"curateMemory", "getMyMemories"}.issubset({item.name for item in tools_for_role("Curator", SPECS)})
    assert set(ROLES) == {"Planner", "Executor", "Reflector", "Curator", "Scout"}


def test_autonomy_risk_policy() -> None:
    assert needs_approval("read", "L0") is False
    assert needs_approval("write-low", "L0") is True
    assert needs_approval("write-low", "L1") is False
    assert needs_approval("write-low", "L2") is False
    assert all(needs_approval("write-high", level) for level in ("L0", "L1", "L2"))
