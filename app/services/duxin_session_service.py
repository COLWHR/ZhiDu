from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from app.db.client import RowObject, db_execute_commit, fetch_all, fetch_one

RISK_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}


def _now() -> datetime:
    return datetime.now()


def _max_risk(current: str, incoming: str) -> str:
    return max((current or "L0"), (incoming or "L0"), key=lambda value: RISK_ORDER.get(value, 0))


def _default_title(mode: str, initial_message: Optional[str] = None) -> str:
    prefixes = {
        "support": "今天的心事",
        "relationship": "关系复盘",
        "growth": "成长整理",
        "crisis": "安全守门",
    }
    if initial_message:
        compact = initial_message.strip().replace("\n", " ")
        if len(compact) > 18:
            compact = compact[:18].rstrip("，。！？!? ")
        if compact:
            return compact
    return prefixes.get(mode, "渡心会话")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _truncate(text: str, limit: int = 120) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


class DuxinSessionService:
    def create_session(self, db, user_id: int, mode: str, title: Optional[str] = None) -> RowObject:
        now = _now()
        rs = db_execute_commit(
            db,
            """
            INSERT INTO duxin_sessions (
                user_id, title, mode, risk_level, status, summary, latest_message_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            [
                user_id,
                title or _default_title(mode),
                mode,
                "L0",
                "active",
                None,
                None,
                now,
                now,
            ],
        )
        return fetch_one(rs)

    def create_session_with_message(
        self,
        db,
        user_id: int,
        mode: str,
        title: Optional[str] = None,
        initial_message: Optional[str] = None,
    ) -> RowObject:
        session = self.create_session(db, user_id=user_id, mode=mode, title=title or _default_title(mode, initial_message))
        if initial_message:
            self.save_message(
                db,
                user_id=user_id,
                session_id=session.id,
                role="user",
                agent_name="用户",
                content=initial_message,
                risk_level="L0",
                metadata={"source": "session_create"},
            )
        return self.get_session(db, user_id=user_id, session_id=session.id) or session

    def list_sessions(self, db, user_id: int) -> List[RowObject]:
        rs = db.execute(
            """
            SELECT * FROM duxin_sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC, id DESC
            """,
            [user_id],
        )
        return fetch_all(rs)

    def get_session(self, db, user_id: int, session_id: int) -> Optional[RowObject]:
        rs = db.execute(
            "SELECT * FROM duxin_sessions WHERE id = ? AND user_id = ?",
            [session_id, user_id],
        )
        return fetch_one(rs)

    def list_messages(self, db, user_id: int, session_id: int) -> List[RowObject]:
        rs = db.execute(
            """
            SELECT * FROM duxin_messages
            WHERE user_id = ? AND session_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            [user_id, session_id],
        )
        return fetch_all(rs)

    def save_message(
        self,
        db,
        user_id: int,
        session_id: int,
        role: str,
        content: str,
        agent_name: Optional[str] = None,
        risk_level: str = "L0",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[RowObject]:
        session = self.get_session(db, user_id=user_id, session_id=session_id)
        if not session:
            return None

        now = _now()
        payload = {
            "role": role,
            "agent_name": agent_name or ("渡心主理人" if role == "assistant" else "用户"),
            "content": content,
            "risk_level": risk_level or "L0",
            "metadata": metadata or {},
        }

        rs = db_execute_commit(
            db,
            """
            INSERT INTO duxin_messages (
                session_id, user_id, role, agent_name, content, risk_level, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            [
                session_id,
                user_id,
                payload["role"],
                payload["agent_name"],
                payload["content"],
                payload["risk_level"],
                _json_dumps(payload["metadata"]),
                now,
            ],
        )
        message = fetch_one(rs)
        if message:
            self.touch_session(
                db,
                user_id=user_id,
                session_id=session_id,
                risk_level=risk_level,
                status="crisis_locked" if risk_level == "L3" else None,
            )
        return message

    def touch_session(
        self,
        db,
        user_id: int,
        session_id: int,
        risk_level: Optional[str] = None,
        status: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> Optional[RowObject]:
        session = self.get_session(db, user_id=user_id, session_id=session_id)
        if not session:
            return None

        now = _now()
        next_risk = _max_risk(session.risk_level, risk_level or session.risk_level)
        next_status = status or session.status

        rs = db_execute_commit(
            db,
            """
            UPDATE duxin_sessions
            SET risk_level = ?, status = ?, summary = COALESCE(?, summary), updated_at = ?, latest_message_at = ?
            WHERE id = ? AND user_id = ?
            RETURNING *
            """,
            [
                next_risk,
                next_status,
                summary,
                now,
                now,
                session_id,
                user_id,
            ],
        )
        return fetch_one(rs)

    def archive_session(self, db, user_id: int, session_id: int) -> Optional[RowObject]:
        summary = self.build_session_summary(db, user_id=user_id, session_id=session_id)
        now = _now()
        rs = db_execute_commit(
            db,
            """
            UPDATE duxin_sessions
            SET status = 'archived', summary = COALESCE(?, summary), updated_at = ?
            WHERE id = ? AND user_id = ?
            RETURNING *
            """,
            [summary, now, session_id, user_id],
        )
        return fetch_one(rs)

    def build_session_summary(self, db, user_id: int, session_id: int) -> Optional[str]:
        messages = self.list_messages(db, user_id=user_id, session_id=session_id)
        if not messages:
            return None

        parts: List[str] = []
        for message in messages[-4:]:
            role = "用户" if getattr(message, "role", "user") == "user" else "渡心"
            content = _truncate(str(getattr(message, "content", "") or ""))
            if content:
                parts.append(f"{role}：{content}")

        if not parts:
            return None

        return " | ".join(parts)

    def save_risk_event(
        self,
        db,
        user_id: int,
        session_id: int,
        risk_level: str,
        signals: Iterable[str],
        action_taken: str,
    ) -> Optional[RowObject]:
        now = _now()
        rs = db_execute_commit(
            db,
            """
            INSERT INTO duxin_risk_events (
                user_id, session_id, risk_level, signals, action_taken, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            [
                user_id,
                session_id,
                risk_level,
                _json_dumps(list(signals)),
                action_taken,
                now,
            ],
        )
        return fetch_one(rs)

    def save_feedback(
        self,
        db,
        user_id: int,
        session_id: Optional[int],
        rating: str,
        content: Optional[str] = None,
        risk_level: Optional[str] = None,
    ) -> Optional[RowObject]:
        now = _now()
        rs = db_execute_commit(
            db,
            """
            INSERT INTO duxin_safety_feedback (
                user_id, session_id, rating, content, risk_level, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            [user_id, session_id, rating, content, risk_level, now],
        )
        return fetch_one(rs)

    def list_feedback(
        self,
        db,
        user_id: int,
        session_id: Optional[int] = None,
        limit: int = 20,
    ) -> List[RowObject]:
        params: List[object] = [user_id]
        where_clause = "WHERE user_id = ?"
        if session_id is not None:
            where_clause += " AND session_id = ?"
            params.append(session_id)

        params.append(limit)
        rs = db.execute(
            f"""
            SELECT * FROM duxin_safety_feedback
            {where_clause}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            params,
        )
        return fetch_all(rs)

    def build_feedback_summary(self, db, user_id: int) -> Dict[str, Any]:
        feedback = self.list_feedback(db, user_id=user_id, limit=50)
        summary = {
            "total": len(feedback),
            "helpful": 0,
            "not_helpful": 0,
            "needs_follow_up": 0,
            "by_risk_level": {"L0": 0, "L1": 0, "L2": 0, "L3": 0},
            "recent": feedback[:8],
        }
        for item in feedback:
            rating = getattr(item, "rating", "helpful")
            if rating in summary:
                summary[rating] += 1
            risk_level = getattr(item, "risk_level", None)
            if risk_level in summary["by_risk_level"]:
                summary["by_risk_level"][risk_level] += 1
        return summary


duxin_session_service = DuxinSessionService()
