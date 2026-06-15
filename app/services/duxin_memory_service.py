from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from app.db.client import RowObject, db_execute_commit, fetch_all, fetch_one


def _now() -> datetime:
    return datetime.now()


class DuxinMemoryService:
    def get_memory(self, db, user_id: int, memory_id: int) -> Optional[RowObject]:
        rs = db.execute(
            "SELECT * FROM duxin_memories WHERE id = ? AND user_id = ?",
            [memory_id, user_id],
        )
        return fetch_one(rs)

    def list_memories(self, db, user_id: int, memory_type: Optional[str] = None) -> List[RowObject]:
        if memory_type:
            rs = db.execute(
                """
                SELECT * FROM duxin_memories
                WHERE user_id = ? AND memory_type = ?
                ORDER BY created_at DESC, id DESC
                """,
                [user_id, memory_type],
            )
        else:
            rs = db.execute(
                """
                SELECT * FROM duxin_memories
                WHERE user_id = ?
                ORDER BY created_at DESC, id DESC
                """,
                [user_id],
        )
        return fetch_all(rs)

    def get_memory_summary(self, db, user_id: int) -> Dict[str, object]:
        memories = self.list_memories(db, user_id=user_id)
        by_type: Dict[str, int] = {}
        recent = []
        for memory in memories:
            memory_type = getattr(memory, "memory_type", "note")
            by_type[memory_type] = by_type.get(memory_type, 0) + 1
        for memory in memories[:8]:
            recent.append(memory)
        return {
            "total": len(memories),
            "by_type": by_type,
            "recent": recent,
        }

    def create_memory(
        self,
        db,
        user_id: int,
        memory_type: str,
        content: str,
        source_session_id: Optional[int] = None,
        user_editable: bool = True,
    ) -> Optional[RowObject]:
        rs = db_execute_commit(
            db,
            """
            INSERT INTO duxin_memories (
                user_id, memory_type, content, source_session_id, user_editable, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            [user_id, memory_type, content, source_session_id, int(bool(user_editable)), _now()],
        )
        return fetch_one(rs)

    def update_memory(
        self,
        db,
        user_id: int,
        memory_id: int,
        memory_type: Optional[str] = None,
        content: Optional[str] = None,
        user_editable: Optional[bool] = None,
    ) -> Optional[RowObject]:
        memory = self.get_memory(db, user_id=user_id, memory_id=memory_id)
        if not memory:
            return None

        fields: List[str] = []
        values: List[object] = []
        if memory_type is not None:
            fields.append("memory_type = ?")
            values.append(memory_type)
        if content is not None:
            fields.append("content = ?")
            values.append(content)
        if user_editable is not None:
            fields.append("user_editable = ?")
            values.append(int(bool(user_editable)))

        if not fields:
            return memory

        values.extend([memory_id, user_id])
        rs = db_execute_commit(
            db,
            f"UPDATE duxin_memories SET {', '.join(fields)} WHERE id = ? AND user_id = ? RETURNING *",
            values,
        )
        return fetch_one(rs)

    def delete_memory(self, db, user_id: int, memory_id: int) -> bool:
        rs = db_execute_commit(
            db,
            "DELETE FROM duxin_memories WHERE id = ? AND user_id = ?",
            [memory_id, user_id],
        )
        return rs is not None

    def clear_memories(self, db, user_id: int) -> bool:
        rs = db_execute_commit(
            db,
            "DELETE FROM duxin_memories WHERE user_id = ?",
            [user_id],
        )
        return rs is not None

    def build_memory_summary(self, db, user_id: int) -> str:
        memories = self.list_memories(db, user_id=user_id)
        if not memories:
            return ""

        lines = []
        for memory in memories[:5]:
            lines.append(f"- {memory.memory_type}: {memory.content}")
        return "\n".join(lines)


duxin_memory_service = DuxinMemoryService()
