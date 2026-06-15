from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

from app.schemas.duxin import DuxinRiskAssessment


@dataclass(frozen=True)
class DuxinTeamMember:
    key: str
    name: str
    role: str
    style: str
    focus: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "key": self.key,
            "name": self.name,
            "role": self.role,
            "style": self.style,
            "focus": self.focus,
        }


@dataclass(frozen=True)
class DuxinTeamPlan:
    mode: str
    primary_agent: DuxinTeamMember
    members: List[DuxinTeamMember]
    handoff_reason: str
    summary: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "mode": self.mode,
            "primary_agent": self.primary_agent.to_dict(),
            "members": [member.to_dict() for member in self.members],
            "handoff_reason": self.handoff_reason,
            "summary": self.summary,
        }


TEAM_PRESETS: Dict[str, Sequence[DuxinTeamMember]] = {
    "support": (
        DuxinTeamMember("zhidu", "智小渡", "总协调", "温和、稳定、收束", "先接住情绪并把信息整理成可执行步骤"),
        DuxinTeamMember("stabilizer", "情绪安抚员", "情绪稳定", "慢一点、软一点、低刺激", "先稳住呼吸、身体感受和当下安全"),
        DuxinTeamMember("clarifier", "认知整理员", "问题澄清", "结构化、简洁、清楚", "把混乱感拆成事件、想法、情绪和需求"),
    ),
    "relationship": (
        DuxinTeamMember("zhidu", "智小渡", "总协调", "温和、稳定、收束", "先接住情绪并把关系议题梳理清楚"),
        DuxinTeamMember("repair", "关系复盘师", "关系视角", "不站队、看边界", "看清互动循环、双方期待和真实卡点"),
        DuxinTeamMember("boundary", "边界教练", "边界与沟通", "清楚、克制、实用", "把关系里能说清、能执行的边界说出来"),
    ),
    "growth": (
        DuxinTeamMember("zhidu", "智小渡", "总协调", "温和、稳定、收束", "先接住情绪并把目标拆成行动"),
        DuxinTeamMember("planner", "行动教练", "行动拆解", "具体、短句、可执行", "把想法变成今天就能开始的下一步"),
        DuxinTeamMember("reflector", "认知整理员", "认知澄清", "结构化、清晰", "识别卡住的自动想法和更平衡的看法"),
    ),
    "crisis": (
        DuxinTeamMember("zhidu", "智小渡", "总协调", "坚定、稳定、收束", "先稳住安全并快速转入危机流程"),
        DuxinTeamMember("guardian", "危机守门员", "安全优先", "直接、简短、明确", "优先识别风险并引导现实世界求助"),
        DuxinTeamMember("stabilizer", "情绪安抚员", "情绪稳定", "慢一点、低刺激", "帮助把当下情绪压到可承受范围"),
    ),
}


def _normalize_text(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _contains_any(text: str, keywords: Sequence[str]) -> bool:
    normalized = _normalize_text(text)
    return any(keyword.lower() in normalized for keyword in keywords)


def _pick_mode(mode: str, latest_user_message: str, risk: DuxinRiskAssessment) -> str:
    if risk.risk_level in {"L2", "L3"}:
        return "crisis"

    if _contains_any(
        latest_user_message,
        (
            "关系",
            "伴侣",
            "前任",
            "分手",
            "冷战",
            "争吵",
            "边界",
            "父母",
            "家庭",
            "出轨",
            "沟通",
        ),
    ):
        return "relationship"

    if _contains_any(
        latest_user_message,
        (
            "目标",
            "计划",
            "行动",
            "拖延",
            "工作",
            "职业",
            "成长",
            "习惯",
            "选择",
            "迷茫",
            "复盘",
        ),
    ):
        return "growth"

    if mode in TEAM_PRESETS:
        return mode

    return "support"


def _build_handoff_reason(mode: str, latest_user_message: str, risk: DuxinRiskAssessment) -> str:
    if risk.risk_level == "L3":
        return "检测到明确高风险信号，优先由危机守门员和情绪安抚员接手。"
    if risk.risk_level == "L2":
        return "检测到潜在危机或准备行动的信号，先稳住安全，再继续分析。"

    if mode == "relationship":
        return "当前更像关系卡点，适合让关系复盘师和边界教练一起补充。"
    if mode == "growth":
        return "当前更像成长与行动问题，适合让行动教练把下一步拆小。"

    if _contains_any(latest_user_message, ("累", "崩", "焦虑", "难受", "压力", "害怕", "孤独")):
        return "用户更需要先被接住情绪，再慢慢澄清问题。"

    return "默认由智小渡主理，再由认知整理员补充结构化整理。"


def build_team_plan(mode: str, latest_user_message: str, risk: DuxinRiskAssessment) -> DuxinTeamPlan:
    selected_mode = _pick_mode(mode, latest_user_message, risk)
    members = list(TEAM_PRESETS.get(selected_mode, TEAM_PRESETS["support"]))
    primary_agent = members[0]
    handoff_reason = _build_handoff_reason(selected_mode, latest_user_message, risk)
    summary = "；".join(f"{member.name}负责{member.focus}" for member in members)
    return DuxinTeamPlan(
        mode=selected_mode,
        primary_agent=primary_agent,
        members=members,
        handoff_reason=handoff_reason,
        summary=summary,
    )


def build_team_status_message(plan: DuxinTeamPlan) -> str:
    if len(plan.members) <= 1:
        return "智小渡正在接住你的诉求。"

    names = "、".join(member.name for member in plan.members[1:])
    return f"智小渡正在把你的诉求分给{names}"


def build_team_system_prompt(
    mode: str,
    memory_summary: str,
    risk: DuxinRiskAssessment,
    plan: DuxinTeamPlan,
) -> str:
    mode_hint = {
        "support": "先接住情绪，再澄清诉求。",
        "relationship": "以关系复盘、边界和沟通为重点。",
        "growth": "以认知整理、行动步骤和长期成长为重点。",
        "crisis": "以稳定、安全和现实求助为优先。",
    }.get(mode, "先接住情绪，再澄清诉求。")

    member_lines = "\n".join(
        f"- {member.name}：{member.role}；风格：{member.style}；职责：{member.focus}"
        for member in plan.members
    )
    memory_block = f"\n\n可用记忆:\n{memory_summary}" if memory_summary else ""

    return (
        "你是“智小渡”，渡心团队的前台总协调。"
        "用户只会面对一个统一的声音，但后台会临时分配不同风格的疏导员协同。"
        "你的目标不是像会议纪要一样分角色，而是像一支配合默契的团队一样给出自然、温和、可执行的回应。\n"
        f"\n本轮团队分配:\n{plan.summary}\n"
        f"\n分配原因:\n{plan.handoff_reason}\n"
        f"\n成员配置:\n{member_lines}\n"
        "\n输出规则:\n"
        "- 先由智小渡用一句话接住情绪和诉求。\n"
        "- 再由 1 到 2 位疏导员补充不同视角，每位只说一小段。\n"
        "- 末尾由智小渡收束成 1 到 3 个可执行的小步骤。\n"
        "- 风格要像团队协同，不要像在背概念。\n"
        "- 不要诊断疾病，不要提供药物建议，不要替代专业治疗。\n"
        "- 如果风险等级是 L2 或 L3，先稳定安全，再继续分析。\n"
        f"\n当前模式：{mode_hint}"
        f"\n当前风险级别：{risk.risk_level}; 检测到的风险信号：{', '.join(risk.signals) if risk.signals else '无'}"
        f"{memory_block}"
    )
