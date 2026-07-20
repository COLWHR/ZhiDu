from __future__ import annotations

import importlib
import io
import sqlite3
import sys
from uuid import uuid4


def auth_headers(client, username: str | None = None):
    username = username or f"user_{uuid4().hex[:8]}"
    password = "password123"
    client.post("/api/v1/auth/register", json={"username": username, "password": password})
    response = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_skill_catalog_exposes_builtin_skills(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/skills/catalog", headers=headers)
    assert response.status_code == 200
    skill_keys = {skill["skill_key"] for skill in response.json()}
    assert "chat.reply" in skill_keys
    assert "doc.generate" in skill_keys
    assert "file.read" in skill_keys


def test_persona_roundtrip_with_skills_and_modalities(client):
    headers = auth_headers(client)
    payload = {
        "name": "Multimodal Persona",
        "bio": "Can handle attachments.",
        "theories": ["systems", "tools"],
        "stance": "helpful",
        "system_prompt": "You are a multimodal assistant.",
        "skills": ["chat.reply", "file.read", "doc.generate"],
        "modalities": ["text", "file", "artifact"],
        "capabilities_version": 2,
    }

    created = client.post("/api/v1/personas/", headers=headers, json=payload)
    assert created.status_code == 200
    created_data = created.json()
    assert created_data["skills"] == payload["skills"]
    assert created_data["modalities"] == payload["modalities"]

    updated = client.put(
        f"/api/v1/personas/{created_data['id']}",
        headers=headers,
        json={"skills": ["chat.reply", "image.view"], "modalities": ["text", "image"]},
    )
    assert updated.status_code == 200
    updated_data = updated.json()
    assert updated_data["skills"] == ["chat.reply", "image.view"]
    assert updated_data["modalities"] == ["text", "image"]


def test_upload_and_chat_history_preserves_attachments(client):
    headers = auth_headers(client)
    persona = client.post(
        "/api/v1/personas/",
        headers=headers,
        json={
            "name": "Attachment Persona",
            "skills": ["chat.reply", "file.read"],
            "modalities": ["text", "file"],
        },
    ).json()

    upload = client.post(
        "/api/v1/upload/asset",
        headers=headers,
        files={"file": ("notes.txt", io.BytesIO(b"hello multimodal"), "text/plain")},
    )
    assert upload.status_code == 200
    attachment = upload.json()
    assert attachment["file_name"] == "notes.txt"
    assert attachment["kind"] == "file"

    saved = client.post(
        "/api/v1/agents/chat/message",
        headers=headers,
        json={
            "persona_id": persona["id"],
            "role": "user",
            "content": "Please read this file.",
            "message_type": "mixed",
            "attachment_ids": [attachment["id"]],
            "metadata": {"attachments": [attachment]},
        },
    )
    assert saved.status_code == 200
    assert saved.json()["success"] is True

    history = client.get(f"/api/v1/agents/chat/history/{persona['id']}", headers=headers)
    assert history.status_code == 200
    items = history.json()
    assert len(items) == 1
    assert items[0]["attachments"]
    assert items[0]["attachments"][0]["file_name"] == "notes.txt"


def test_skill_runtime_imports_without_optional_docx_and_pillow(monkeypatch):
    monkeypatch.setitem(sys.modules, "docx", None)
    monkeypatch.setitem(sys.modules, "PIL", None)
    monkeypatch.setitem(sys.modules, "PIL.Image", None)
    monkeypatch.setitem(sys.modules, "PIL.ImageDraw", None)
    monkeypatch.setitem(sys.modules, "PIL.ImageFont", None)
    sys.modules.pop("app.services.skill_runtime", None)

    skill_runtime = importlib.import_module("app.services.skill_runtime")

    skill_keys = {skill["skill_key"] for skill in skill_runtime.get_skill_catalog()}
    assert "chat.reply" in skill_keys
    assert "doc.generate" in skill_keys


def test_render_text_artifact_falls_back_to_plain_text_without_docx(monkeypatch):
    skill_runtime = importlib.import_module("app.services.skill_runtime")
    monkeypatch.setattr(skill_runtime, "_load_docx_document", lambda: None)

    file_name, mime_type, storage_url = skill_runtime.render_text_artifact("hello world", title="Fallback Doc")

    assert file_name.endswith(".txt")
    assert mime_type == "text/plain"
    assert storage_url.endswith(file_name)


def test_multimodal_schema_adds_avatar_column_to_existing_personas_table(tmp_path):
    from app.db.migrations import ensure_multimodal_schema

    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            """
            CREATE TABLE personas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                title TEXT,
                bio TEXT,
                theories TEXT,
                stance TEXT,
                system_prompt TEXT,
                is_public BOOLEAN DEFAULT 0
            )
            """
        )
        conn.execute("CREATE TABLE chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT)")
        conn.execute("CREATE TABLE attachments (id INTEGER PRIMARY KEY AUTOINCREMENT)")
        conn.execute("CREATE TABLE artifacts (id INTEGER PRIMARY KEY AUTOINCREMENT)")
        conn.execute("CREATE TABLE task_runs (id INTEGER PRIMARY KEY AUTOINCREMENT)")

        class _CompatConn:
            def __init__(self, raw_conn):
                self.raw_conn = raw_conn

            def execute(self, query, params=None):
                cursor = self.raw_conn.execute(query, params or [])
                if query.strip().lower().startswith("pragma table_info"):
                    rows = [dict(row) for row in cursor.fetchall()]

                    class _Result:
                        def __init__(self, rows):
                            self.rows = rows

                    return _Result(rows)
                return cursor

        ensure_multimodal_schema(_CompatConn(conn), is_postgres=False)

        columns = [row["name"] for row in conn.execute("PRAGMA table_info(personas)").fetchall()]
        assert "avatar" in columns
    finally:
        conn.close()
