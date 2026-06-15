from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.duxin import DuxinMessageCreate, DuxinRiskAssessment
from app.services.duxin_memory_service import duxin_memory_service
from app.services.duxin_risk_service import assess_risk, build_crisis_reply
from app.services.duxin_session_service import duxin_session_service
from app.services.duxin_team_orchestrator import (
    build_team_plan,
    build_team_status_message,
    build_team_system_prompt,
)
from app.services.duxin_risk_service import build_support_reply_hint
from app.services.duxin_serializers import chunk_content, latest_user_message, message_to_dict, session_to_dict
from utils import LLMServiceError, get_chat_completion

logger = logging.getLogger(__name__)


def build_chat_messages(
    session: Any,
    messages: List[Dict[str, Any]],
    memory_summary: str,
    risk: DuxinRiskAssessment,
    team_plan,
) -> List[Dict[str, str]]:
    system_prompt = build_team_system_prompt(session.mode, memory_summary, risk, team_plan)
    response_hint = build_support_reply_hint(team_plan.mode, team_plan.summary)
    system_prompt = (
        f"{system_prompt}\n\n{response_hint}\n"
        "回复规则：先接住当前情绪，再给出一个最小可执行动作；只有在必要时才提出一个问题。"
    )
    llm_messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

    for message in messages[-12:]:
        role = "user" if message.get("role") == "user" else "assistant"
        content = str(message.get("content") or "").strip()
        if content:
            llm_messages.append({"role": role, "content": content})

    if not any(item["role"] == "user" for item in llm_messages[1:]):
        llm_messages.append({"role": "user", "content": "我现在需要一点支持。"})

    return llm_messages


def save_assistant_reply(
    db,
    session_id: int,
    user_id: int,
    content: str,
    risk_level: str,
    agent_name: str = "智小渡",
    metadata: Dict[str, Any] | None = None,
) -> None:
    duxin_session_service.save_message(
        db,
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        agent_name=agent_name,
        content=content,
        risk_level=risk_level,
        metadata=metadata or {},
    )


async def stream_session_chat(
    session_id: int,
    payload: DuxinMessageCreate,
    db,
    current_user,
) -> StreamingResponse:
    session = duxin_session_service.get_session(db, user_id=current_user.id, session_id=session_id)
    if not session:
        raise ValueError("Duxin session not found")

    user_message = duxin_session_service.save_message(
        db,
        user_id=current_user.id,
        session_id=session_id,
        role="user",
        agent_name="用户",
        content=payload.content,
        risk_level="L0",
        metadata={"source": "chat"},
    )
    if not user_message:
        raise RuntimeError("Failed to save user message")

    risk = assess_risk(payload.content)
    team_plan = build_team_plan(session.mode, payload.content, risk)
    duxin_session_service.save_risk_event(
        db,
        user_id=current_user.id,
        session_id=session_id,
        risk_level=risk.risk_level,
        signals=risk.signals,
        action_taken="crisis_reply" if risk.should_escalate else "support_reply",
    )

    session = (
        duxin_session_service.touch_session(
            db,
            user_id=current_user.id,
            session_id=session_id,
            risk_level=risk.risk_level,
            status="crisis_locked" if risk.risk_level == "L3" else "active",
        )
        or session
    )

    memory_summary = duxin_memory_service.build_memory_summary(db, user_id=current_user.id)
    history = [
        message_to_dict(message)
        for message in duxin_session_service.list_messages(db, user_id=current_user.id, session_id=session_id)
    ]
    llm_messages = build_chat_messages(session, history, memory_summary, risk, team_plan)

    async def generate():
        yield f"data: {json.dumps({'type': 'session', 'session': session_to_dict(session)}, ensure_ascii=False)}\n\n"
        yield (
            "data: "
            + json.dumps(
                {
                    "type": "risk",
                    "risk_level": risk.risk_level,
                    "signals": risk.signals,
                    "summary": risk.summary,
                    "response_mode": risk.response_mode,
                },
                ensure_ascii=False,
            )
            + "\n\n"
        )
        yield f"data: {json.dumps({'type': 'team', 'team': team_plan.to_dict()}, ensure_ascii=False)}\n\n"
        yield (
            "data: "
            + json.dumps(
                {
                    "type": "agent_status",
                    "agent": team_plan.primary_agent.name,
                    "content": build_team_status_message(team_plan),
                },
                ensure_ascii=False,
            )
            + "\n\n"
        )

        if risk.should_escalate:
            crisis_reply = build_crisis_reply(risk, latest_user_message=payload.content)
            yield f"data: {json.dumps({'type': 'chunk', 'content': crisis_reply}, ensure_ascii=False)}\n\n"
            save_assistant_reply(
                db,
                session_id=session_id,
                user_id=current_user.id,
                content=crisis_reply,
                risk_level=risk.risk_level,
                agent_name=team_plan.primary_agent.name,
                metadata={"risk": risk.model_dump(), "team": team_plan.to_dict()},
            )
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'risk_level': risk.risk_level}, ensure_ascii=False)}\n\n"
            return

        try:
            stream = get_chat_completion(
                llm_messages,
                stream=True,
                raise_error=True,
                max_retries=1,
                timeout=12,
            )
            if not stream:
                raise LLMServiceError(kind="empty_response", message="Unable to fetch reply stream")

            full_reply = ""
            emitted = False
            for chunk in stream:
                content = chunk_content(chunk)
                if not content:
                    continue
                emitted = True
                full_reply += content
                yield f"data: {json.dumps({'type': 'chunk', 'content': content}, ensure_ascii=False)}\n\n"

            if not emitted or not full_reply.strip():
                full_reply = (
                    "我先接住你现在的感受。\n"
                    "这次我们会先把事情拆小，再决定下一步怎么做。\n"
                    "如果你愿意，我只回答一个最重要的问题。"
                )
                yield f"data: {json.dumps({'type': 'chunk', 'content': full_reply}, ensure_ascii=False)}\n\n"

            save_assistant_reply(
                db,
                session_id=session_id,
                user_id=current_user.id,
                content=full_reply,
                risk_level=risk.risk_level,
                agent_name=team_plan.primary_agent.name,
                metadata={"risk": risk.model_dump(), "team": team_plan.to_dict()},
            )
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'risk_level': risk.risk_level}, ensure_ascii=False)}\n\n"
        except LLMServiceError as exc:
            logger.warning("Duxin LLM fallback: %s", exc)
            fallback_reply = (
                "我先接住你现在的感受。\n"
                "我们不着急下结论，先把这件事拆成两步：\n"
                "1. 说出最难受的那一点；\n"
                "2. 只选一个今天能做的小动作。"
            )
            yield f"data: {json.dumps({'type': 'chunk', 'content': fallback_reply}, ensure_ascii=False)}\n\n"
            save_assistant_reply(
                db,
                session_id=session_id,
                user_id=current_user.id,
                content=fallback_reply,
                risk_level=risk.risk_level,
                agent_name=team_plan.primary_agent.name,
                metadata={"risk": risk.model_dump(), "team": team_plan.to_dict(), "fallback": True},
            )
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'risk_level': risk.risk_level, 'fallback': True}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.error("Duxin stream error: %s", exc)
            failure_reply = (
                "抱歉，时空之门刚刚遇到了一点阻塞。\n"
                "你可以先告诉我：你此刻最想被怎么接住？"
            )
            yield f"data: {json.dumps({'type': 'chunk', 'content': failure_reply}, ensure_ascii=False)}\n\n"
            save_assistant_reply(
                db,
                session_id=session_id,
                user_id=current_user.id,
                content=failure_reply,
                risk_level=risk.risk_level,
                agent_name=team_plan.primary_agent.name,
                metadata={"risk": risk.model_dump(), "team": team_plan.to_dict(), "error": str(exc)},
            )
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'risk_level': risk.risk_level, 'error': True}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
