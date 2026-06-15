from app.schemas.duxin import DuxinRiskAssessment
from app.services.duxin_team_orchestrator import build_team_plan, build_team_status_message, build_team_system_prompt


def _risk(level: str = "L0", signals: list[str] | None = None) -> DuxinRiskAssessment:
    return DuxinRiskAssessment(
        risk_level=level,
        signals=signals or [],
        response_mode="support",
        should_escalate=level in {"L2", "L3"},
        summary="test",
        recommended_actions=[],
    )


def test_build_team_plan_for_relationship_topic():
    plan = build_team_plan("support", "我想复盘一下这段关系和边界", _risk())
    assert plan.mode == "relationship"
    assert plan.primary_agent.name == "智小渡"
    assert any(member.key == "repair" for member in plan.members)
    assert "关系复盘师" in plan.summary


def test_build_team_plan_escalates_to_crisis():
    plan = build_team_plan("support", "我想死", _risk("L3", ["我想死"]))
    assert plan.mode == "crisis"
    assert any(member.key == "guardian" for member in plan.members)
    assert "危机守门员" in build_team_status_message(plan)


def test_build_team_system_prompt_contains_team_roster():
    plan = build_team_plan("growth", "我想把目标拆小", _risk())
    prompt = build_team_system_prompt("growth", "记忆摘要", _risk(), plan)
    assert "智小渡" in prompt
    assert "本轮团队分配" in prompt
    assert "行动教练" in prompt

