from __future__ import annotations

import json
from typing import Any, Dict, List


def message_to_dict(message: Any) -> Dict[str, Any]:
    metadata = getattr(message, "metadata", {})
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    return {
        "id": getattr(message, "id", None),
        "session_id": getattr(message, "session_id", None),
        "user_id": getattr(message, "user_id", None),
        "role": getattr(message, "role", None),
        "agent_name": getattr(message, "agent_name", None),
        "content": getattr(message, "content", None),
        "risk_level": getattr(message, "risk_level", "L0"),
        "metadata": metadata or {},
        "created_at": getattr(message, "created_at", None),
    }


def session_to_dict(session: Any) -> Dict[str, Any]:
    return {
        "id": getattr(session, "id", None),
        "user_id": getattr(session, "user_id", None),
        "title": getattr(session, "title", ""),
        "mode": getattr(session, "mode", "support"),
        "risk_level": getattr(session, "risk_level", "L0"),
        "status": getattr(session, "status", "active"),
        "summary": getattr(session, "summary", None),
        "latest_message_at": getattr(session, "latest_message_at", None),
        "created_at": getattr(session, "created_at", None),
        "updated_at": getattr(session, "updated_at", None),
    }


def memory_to_dict(memory: Any) -> Dict[str, Any]:
    return {
        "id": getattr(memory, "id", None),
        "user_id": getattr(memory, "user_id", None),
        "memory_type": getattr(memory, "memory_type", "note"),
        "content": getattr(memory, "content", ""),
        "source_session_id": getattr(memory, "source_session_id", None),
        "user_editable": bool(getattr(memory, "user_editable", True)),
        "created_at": getattr(memory, "created_at", None),
    }


def memory_summary_to_dict(summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total": int(summary.get("total", 0) or 0),
        "by_type": summary.get("by_type", {}),
        "recent": [memory_to_dict(memory) for memory in summary.get("recent", [])],
    }


def feedback_to_dict(feedback: Any) -> Dict[str, Any]:
    return {
        "id": getattr(feedback, "id", None),
        "user_id": getattr(feedback, "user_id", None),
        "session_id": getattr(feedback, "session_id", None),
        "rating": getattr(feedback, "rating", "helpful"),
        "content": getattr(feedback, "content", None),
        "risk_level": getattr(feedback, "risk_level", None),
        "linked_memory_id": getattr(feedback, "linked_memory_id", None),
        "created_at": getattr(feedback, "created_at", None),
    }


def feedback_summary_to_dict(summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total": int(summary.get("total", 0) or 0),
        "helpful": int(summary.get("helpful", 0) or 0),
        "not_helpful": int(summary.get("not_helpful", 0) or 0),
        "needs_follow_up": int(summary.get("needs_follow_up", 0) or 0),
        "by_risk_level": summary.get("by_risk_level", {}),
        "recent": [feedback_to_dict(item) for item in summary.get("recent", [])],
    }


def latest_user_message(messages: List[Dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            content = str(message.get("content") or "").strip()
            if content:
                return content
    return ""


def chunk_content(chunk: Any) -> str:
    if chunk is None:
        return ""
    choices = getattr(chunk, "choices", None)
    if not choices:
        return ""
    try:
        delta = choices[0].delta
        return str(getattr(delta, "content", "") or "")
    except Exception:
        return ""
