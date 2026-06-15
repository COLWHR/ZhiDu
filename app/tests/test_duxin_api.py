from types import SimpleNamespace
from unittest.mock import patch


def get_auth_headers(client, username="duxin_user", password="password123"):
    client.post("/api/v1/auth/register", json={"username": username, "password": password})
    response = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _fake_stream(*args, **kwargs):
    def generator():
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="我先接住你现在的感受。"))])
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="我们可以先把最重的那一块说出来。"))])

    return generator()


def test_create_duxin_session_and_stream(client):
    headers = get_auth_headers(client, "duxin_stream_user")

    session_response = client.post(
        "/api/v1/duxin/sessions",
        headers=headers,
        json={"mode": "support", "title": "今晚有点难熬"},
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["id"]

    with patch("app.api.v1.endpoints.duxin.get_chat_completion", side_effect=_fake_stream):
        response = client.post(
            f"/api/v1/duxin/sessions/{session_id}/chat/stream",
            headers=headers,
            json={"content": "我最近压力很大"},
        )

    assert response.status_code == 200
    body = response.text
    assert '"type": "risk"' in body
    assert '"type": "team"' in body
    assert '"type": "chunk"' in body
    assert '"type": "done"' in body

    messages_response = client.get(f"/api/v1/duxin/sessions/{session_id}/messages", headers=headers)
    assert messages_response.status_code == 200
    messages = messages_response.json()
    assert len(messages) >= 2
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["metadata"].get("team") is not None


def test_duxin_crisis_stream_returns_crisis_reply(client):
    headers = get_auth_headers(client, "duxin_crisis_user")
    session_response = client.post(
        "/api/v1/duxin/sessions",
        headers=headers,
        json={"mode": "crisis", "title": "危机测试"},
    )
    session_id = session_response.json()["id"]

    response = client.post(
        f"/api/v1/duxin/sessions/{session_id}/chat/stream",
        headers=headers,
        json={"content": "我想死"},
    )

    assert response.status_code == 200
    body = response.text
    assert "988" in body
    assert '"type": "risk"' in body
    assert '"type": "team"' in body
    assert '"risk_level": "L3"' in body


def test_duxin_memory_crud(client):
    headers = get_auth_headers(client, "duxin_memory_user")

    create_response = client.post(
        "/api/v1/duxin/memories",
        headers=headers,
        json={
            "memory_type": "preference",
            "content": "我不喜欢被催促",
            "user_editable": True
        },
    )
    assert create_response.status_code == 200
    memory_id = create_response.json()["id"]

    list_response = client.get("/api/v1/duxin/memories", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    delete_response = client.delete(f"/api/v1/duxin/memories/{memory_id}", headers=headers)
    assert delete_response.status_code == 200

    list_response_after_delete = client.get("/api/v1/duxin/memories", headers=headers)
    assert list_response_after_delete.status_code == 200
    assert list_response_after_delete.json() == []


def test_duxin_memory_update_and_summary(client):
    headers = get_auth_headers(client, "duxin_memory_update_user")

    create_response = client.post(
        "/api/v1/duxin/memories",
        headers=headers,
        json={
            "memory_type": "note",
            "content": "原始记忆",
            "user_editable": True,
        },
    )
    assert create_response.status_code == 200
    memory_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/duxin/memories/{memory_id}",
        headers=headers,
        json={
            "memory_type": "goal",
            "content": "更新后的记忆",
            "user_editable": False,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["memory_type"] == "goal"
    assert update_response.json()["user_editable"] is False

    summary_response = client.get("/api/v1/duxin/memories/summary", headers=headers)
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["total"] == 1
    assert summary["by_type"]["goal"] == 1
    assert len(summary["recent"]) == 1


def test_duxin_feedback_flow_creates_memory(client):
    headers = get_auth_headers(client, "duxin_feedback_user")
    session_response = client.post(
        "/api/v1/duxin/sessions",
        headers=headers,
        json={"mode": "support", "title": "反馈测试"},
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["id"]

    feedback_response = client.post(
        "/api/v1/duxin/safety/feedback",
        headers=headers,
        json={
            "session_id": session_id,
            "rating": "needs_follow_up",
            "content": "这次支持很有帮助，但我还想继续整理。",
            "risk_level": "L1",
            "save_as_memory": True,
            "memory_type": "note",
        },
    )
    assert feedback_response.status_code == 200
    feedback = feedback_response.json()
    assert feedback["linked_memory_id"] is not None

    feedback_list = client.get("/api/v1/duxin/safety/feedback", headers=headers)
    assert feedback_list.status_code == 200
    assert len(feedback_list.json()) == 1

    feedback_summary = client.get("/api/v1/duxin/safety/feedback/summary", headers=headers)
    assert feedback_summary.status_code == 200
    summary = feedback_summary.json()
    assert summary["total"] == 1
    assert summary["needs_follow_up"] == 1
    assert summary["by_risk_level"]["L1"] == 1
