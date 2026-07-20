from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Iterable

from app.services.skill_runtime import get_skill_catalog

logger = logging.getLogger(__name__)


def _row_value(row, key: str):
    if isinstance(row, dict):
        return row.get(key)
    return getattr(row, key, None)


def _existing_columns(conn, table_name: str, is_postgres: bool) -> set[str]:
    if is_postgres:
        rs = conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = ?
            """,
            [table_name],
        )
        return {str(_row_value(row, "column_name")) for row in getattr(rs, "rows", []) if _row_value(row, "column_name")}

    rs = conn.execute(f"PRAGMA table_info({table_name})")
    return {str(_row_value(row, "name")) for row in getattr(rs, "rows", []) if _row_value(row, "name")}


def _add_columns_if_missing(conn, table_name: str, columns: Iterable[tuple[str, str]], is_postgres: bool) -> None:
    existing = _existing_columns(conn, table_name, is_postgres)
    for column_name, ddl in columns:
        if column_name in existing:
            continue
        logger.info("Adding missing column %s.%s", table_name, column_name)
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}")


def ensure_multimodal_schema(conn, is_postgres: bool) -> None:
    persona_columns = [
        ("avatar", "TEXT"),
        ("skills", "JSONB DEFAULT '[]'::jsonb" if is_postgres else "TEXT DEFAULT '[]'"),
        ("skill_policy", "JSONB DEFAULT '{}'::jsonb" if is_postgres else "TEXT DEFAULT '{}'"),
        ("modalities", "JSONB DEFAULT '[\"text\"]'::jsonb" if is_postgres else "TEXT DEFAULT '[\"text\"]'"),
        ("capabilities_version", "INTEGER DEFAULT 1"),
    ]

    chat_message_columns = [
        ("message_type", "VARCHAR(50) DEFAULT 'text'" if is_postgres else "TEXT DEFAULT 'text'"),
        ("metadata", "JSONB DEFAULT '{}'::jsonb" if is_postgres else "TEXT DEFAULT '{}'"),
    ]

    attachment_columns = [
        ("persona_id", "INTEGER"),
        ("chat_message_id", "INTEGER"),
        ("session_id", "INTEGER"),
        ("kind", "VARCHAR(50)" if is_postgres else "TEXT"),
        ("preview_url", "TEXT"),
        ("sha256", "VARCHAR(128)" if is_postgres else "TEXT"),
        ("meta", "JSONB DEFAULT '{}'::jsonb" if is_postgres else "TEXT DEFAULT '{}'"),
    ]

    artifact_columns = [
        ("persona_id", "INTEGER"),
        ("task_run_id", "INTEGER"),
        ("preview_url", "TEXT"),
        ("version", "INTEGER DEFAULT 1"),
        ("status", "VARCHAR(50) DEFAULT 'ready'" if is_postgres else "TEXT DEFAULT 'ready'"),
        ("meta", "JSONB DEFAULT '{}'::jsonb" if is_postgres else "TEXT DEFAULT '{}'"),
    ]

    task_run_columns = [
        ("persona_id", "INTEGER"),
        ("skill_key", "VARCHAR(255)" if is_postgres else "TEXT"),
        ("session_id", "INTEGER"),
        ("status", "VARCHAR(50) DEFAULT 'queued'" if is_postgres else "TEXT DEFAULT 'queued'"),
        ("progress", "INTEGER DEFAULT 0"),
        ("input_payload", "JSONB DEFAULT '{}'::jsonb" if is_postgres else "TEXT DEFAULT '{}'"),
        ("output_payload", "JSONB DEFAULT '{}'::jsonb" if is_postgres else "TEXT DEFAULT '{}'"),
        ("error_message", "TEXT"),
        ("finished_at", "TIMESTAMP WITH TIME ZONE" if is_postgres else "DATETIME"),
    ]

    _add_columns_if_missing(conn, "personas", persona_columns, is_postgres)
    _add_columns_if_missing(conn, "chat_messages", chat_message_columns, is_postgres)
    _add_columns_if_missing(conn, "attachments", attachment_columns, is_postgres)
    _add_columns_if_missing(conn, "artifacts", artifact_columns, is_postgres)
    _add_columns_if_missing(conn, "task_runs", task_run_columns, is_postgres)


def seed_default_skills(conn) -> None:
    catalog = get_skill_catalog()
    if not catalog:
        return

    for skill in catalog:
        timestamp = datetime.now()
        conn.execute(
            """
            INSERT INTO skills (
                skill_key, name, category, description, input_modalities, output_types,
                required_models, required_tools, params_schema, permission_scope,
                cost_level, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(skill_key) DO UPDATE SET
                name = excluded.name,
                category = excluded.category,
                description = excluded.description,
                input_modalities = excluded.input_modalities,
                output_types = excluded.output_types,
                required_models = excluded.required_models,
                required_tools = excluded.required_tools,
                params_schema = excluded.params_schema,
                permission_scope = excluded.permission_scope,
                cost_level = excluded.cost_level,
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            [
                skill["skill_key"],
                skill["name"],
                skill["category"],
                skill.get("description"),
                json.dumps(skill.get("input_modalities", [])),
                json.dumps(skill.get("output_types", [])),
                json.dumps(skill.get("required_models", [])),
                json.dumps(skill.get("required_tools", [])),
                json.dumps(skill.get("params_schema", {})),
                json.dumps(skill.get("permission_scope", [])),
                skill.get("cost_level", "low"),
                skill.get("status", "active"),
                timestamp,
                timestamp,
            ],
        )
