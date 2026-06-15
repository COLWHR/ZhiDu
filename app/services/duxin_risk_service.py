from __future__ import annotations

from typing import List, Tuple

from app.schemas.duxin import DuxinRiskAssessment


L3_PATTERNS: Tuple[Tuple[str, ...], ...] = (
    ("想死", "不想活", "结束生命", "自杀", "轻生"),
    ("kill myself", "end my life", "suicide", "want to die"),
    ("割腕", "上吊", "跳楼", "服药过量", "过量服药", "喝药", "吃药自杀"),
    ("伤害别人", "杀人", "报复社会", "我会杀", "hurt someone", "kill them"),
)

L2_PATTERNS: Tuple[Tuple[str, ...], ...] = (
    ("已经准备好了", "准备好了", "今晚就", "马上就", "已经买了", "刚买了"),
    ("刀", "绳子", "药", "安眠药", "刀片", "汽油", "农药"),
    ("计划", "方法", "步骤", "怎么做", "具体做法", "地点", "时间"),
    ("can't go on", "cannot go on", "no way out", "i am done"),
)

L1_PATTERNS: Tuple[Tuple[str, ...], ...] = (
    ("崩溃", "难受", "焦虑", "失眠", "失恋", "孤独", "委屈", "自责"),
    ("撑不住", "压力好大", "很痛苦", "想哭", "心慌", "害怕", "迷茫"),
    ("burned out", "anxious", "overwhelmed", "lonely", "panic"),
)


def _normalize_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _collect_signals(text: str, patterns: Tuple[Tuple[str, ...], ...]) -> List[str]:
    normalized = _normalize_text(text)
    signals: List[str] = []
    for group in patterns:
        hits = [item for item in group if item and item.lower() in normalized]
        if hits:
            signals.append(hits[0])
    return signals


def assess_risk(text: str) -> DuxinRiskAssessment:
    normalized = _normalize_text(text)

    signals = _collect_signals(normalized, L3_PATTERNS)
    if signals:
        return DuxinRiskAssessment(
            risk_level="L3",
            signals=signals,
            response_mode="crisis",
            should_escalate=True,
            summary="检测到明确的自伤、自杀或伤害他人高风险信号。",
            recommended_actions=[
                "立刻停止普通陪伴流程",
                "鼓励联系当地急救或危机热线",
                "建议联系现实中可信任的人陪同",
                "避免提供任何危险细节",
            ],
        )

    signals = _collect_signals(normalized, L2_PATTERNS)
    if signals:
        return DuxinRiskAssessment(
            risk_level="L2",
            signals=signals,
            response_mode="stabilize",
            should_escalate=True,
            summary="检测到潜在危机或已经出现准备行为。",
            recommended_actions=[
                "先稳定情绪，再继续对话",
                "鼓励联系现实世界的支持",
                "避免讨论危险细节",
                "给出下一步安全动作",
            ],
        )

    signals = _collect_signals(normalized, L1_PATTERNS)
    if signals:
        return DuxinRiskAssessment(
            risk_level="L1",
            signals=signals,
            response_mode="support",
            should_escalate=False,
            summary="检测到明显的情绪压力或低落信号。",
            recommended_actions=[
                "先接住情绪",
                "帮助用户澄清最主要的困扰",
                "提供一个可执行的小步骤",
            ],
        )

    return DuxinRiskAssessment(
        risk_level="L0",
        signals=[],
        response_mode="support",
        should_escalate=False,
        summary="未检测到明显风险信号。",
        recommended_actions=[
            "保持温柔、稳定、有限边界的支持",
            "协助用户整理感受和下一步行动",
        ],
    )


def build_crisis_reply(risk: DuxinRiskAssessment, latest_user_message: str = "") -> str:
    user_hint = f"你刚才提到：{latest_user_message}\n" if latest_user_message else ""
    escalation = "\n".join(f"- {item}" for item in risk.recommended_actions)
    return (
        "我很重视你现在的状态。\n"
        f"{user_hint}"
        "我不会展开危险细节，但我会先陪你把眼前这一步稳住。\n\n"
        "现在请立刻做这 3 件事：\n"
        "1. 把可能伤害自己的东西放远一点。\n"
        "2. 联系一个现实里可信任的人，告诉对方你现在需要陪伴。\n"
        "3. 如果你在美国或加拿大，请拨打或短信 988；如果在其他地区，请联系当地急救/危机热线。\n\n"
        "如果你愿意，只要回复我一个字“在”，我就继续陪你走下一步。\n\n"
        f"{escalation}"
    )


def build_support_reply_hint(mode: str, summary: str) -> str:
    mode_label = {
        "support": "情绪接住",
        "relationship": "关系复盘",
        "growth": "成长拆解",
        "crisis": "安全守门",
    }.get(mode, "情绪接住")

    playbook = {
        "support": "先接住情绪，再复述需求，最后给一个今天就能做的小动作。",
        "relationship": "先镜像双方感受，再指出互动循环和边界，最后给一句能直接说出口的话。",
        "growth": "先确认目标，再拆成下一步行动，最后把任务缩成一个今天能完成的动作。",
        "crisis": "先稳定安全，不追问细节，只给现实可执行的支持与求助路径。",
    }.get(mode, "先接住情绪，再复述需求，最后给一个今天就能做的小动作。")

    return f"当前模式：{mode_label}。{playbook} 参考摘要：{summary}"
