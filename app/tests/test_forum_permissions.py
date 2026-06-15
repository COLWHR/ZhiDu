import pytest
from uuid import uuid4


def register_and_login(client, username, role="user"):
    username = f"{username}_{uuid4().hex[:8]}"
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "password123", "role": role},
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_forum(client, headers, topic="Private forum"):
    persona_res = client.post(
        "/api/v1/personas/",
        headers=headers,
        json={
            "name": f"{topic}-persona",
            "title": "T",
            "bio": "B",
            "theories": ["X"],
            "stance": "S",
            "system_prompt": "SP",
            "is_public": True,
        },
    )
    assert persona_res.status_code == 200
    persona_id = persona_res.json()["id"]

    forum_res = client.post(
        "/api/v1/forums/",
        headers=headers,
        json={
            "topic": topic,
            "participant_ids": [persona_id],
            "duration_minutes": 10,
        },
    )
    assert forum_res.status_code == 200
    return forum_res.json(), persona_res.json()


def test_forum_detail_requires_auth_and_owner_access(client):
    owner_headers = register_and_login(client, "forum_owner", role="admin")
    other_headers = register_and_login(client, "forum_guest")
    forum, _ = create_forum(client, owner_headers, topic="Ownership gate")

    unauth_res = client.get(f"/api/v1/forums/{forum['id']}")
    assert unauth_res.status_code == 401

    forbidden_res = client.get(f"/api/v1/forums/{forum['id']}", headers=other_headers)
    assert forbidden_res.status_code == 403

    ok_res = client.get(f"/api/v1/forums/{forum['id']}", headers=owner_headers)
    assert ok_res.status_code == 200
    assert ok_res.json()["topic"] == "Ownership gate"


def test_forum_messages_and_logs_require_auth(client):
    owner_headers = register_and_login(client, "forum_owner_messages", role="admin")
    other_headers = register_and_login(client, "forum_guest_messages")
    forum, persona = create_forum(client, owner_headers, topic="Messages gate")

    unauth_messages = client.get(f"/api/v1/forums/{forum['id']}/messages")
    assert unauth_messages.status_code == 401

    forbidden_messages = client.get(
        f"/api/v1/forums/{forum['id']}/messages",
        headers=other_headers,
    )
    assert forbidden_messages.status_code == 403

    ok_messages = client.get(f"/api/v1/forums/{forum['id']}/messages", headers=owner_headers)
    assert ok_messages.status_code == 200
    assert isinstance(ok_messages.json(), list)

    unauth_logs = client.get(f"/api/v1/forums/{forum['id']}/logs")
    assert unauth_logs.status_code == 401

    forbidden_logs = client.get(
        f"/api/v1/forums/{forum['id']}/logs",
        headers=other_headers,
    )
    assert forbidden_logs.status_code == 403

    ok_logs = client.get(f"/api/v1/forums/{forum['id']}/logs", headers=owner_headers)
    assert ok_logs.status_code == 200
    assert isinstance(ok_logs.json(), list)


def test_forum_message_post_requires_auth_and_owner_access(client):
    owner_headers = register_and_login(client, "forum_owner_post", role="admin")
    other_headers = register_and_login(client, "forum_guest_post")
    forum, persona = create_forum(client, owner_headers, topic="Post gate")

    unauth_post = client.post(
        f"/api/v1/forums/{forum['id']}/messages",
        json={
            "forum_id": forum["id"],
            "persona_id": persona["id"],
            "speaker_name": "P",
            "content": "Hello",
            "turn_count": 1,
        },
    )
    assert unauth_post.status_code == 401

    forbidden_post = client.post(
        f"/api/v1/forums/{forum['id']}/messages",
        headers=other_headers,
        json={
            "forum_id": forum["id"],
            "persona_id": persona["id"],
            "speaker_name": "P",
            "content": "Hello",
            "turn_count": 1,
        },
    )
    assert forbidden_post.status_code == 403

    ok_post = client.post(
        f"/api/v1/forums/{forum['id']}/messages",
        headers=owner_headers,
        json={
            "forum_id": forum["id"],
            "persona_id": persona["id"],
            "speaker_name": "P",
            "content": "Hello",
            "turn_count": 1,
        },
    )
    assert ok_post.status_code == 200
    assert ok_post.json()["content"] == "Hello"


def test_forum_chat_requires_auth_and_owner_access(client):
    owner_headers = register_and_login(client, "forum_owner_chat", role="admin")
    other_headers = register_and_login(client, "forum_guest_chat")
    forum, _ = create_forum(client, owner_headers, topic="Chat gate")

    unauth_chat = client.post(
        f"/api/v1/forums/{forum['id']}/chat",
        json={"speaker": "User", "content": "Hi"},
    )
    assert unauth_chat.status_code == 401

    forbidden_chat = client.post(
        f"/api/v1/forums/{forum['id']}/chat",
        headers=other_headers,
        json={"speaker": "User", "content": "Hi"},
    )
    assert forbidden_chat.status_code == 403

    ok_chat = client.post(
        f"/api/v1/forums/{forum['id']}/chat",
        headers=owner_headers,
        json={"speaker": "User", "content": "Hi"},
    )
    assert ok_chat.status_code == 202
    assert ok_chat.json()["status"] == "queued"


def test_forum_stop_endpoint_closes_forum_and_requires_auth(client):
    owner_headers = register_and_login(client, "forum_owner_stop", role="admin")
    other_headers = register_and_login(client, "forum_guest_stop")
    forum, _ = create_forum(client, owner_headers, topic="Stop gate")

    unauth_stop = client.post(f"/api/v1/forums/{forum['id']}/stop")
    assert unauth_stop.status_code == 401

    forbidden_stop = client.post(f"/api/v1/forums/{forum['id']}/stop", headers=other_headers)
    assert forbidden_stop.status_code == 403

    ok_stop = client.post(f"/api/v1/forums/{forum['id']}/stop", headers=owner_headers)
    assert ok_stop.status_code == 200
    assert ok_stop.json()["status"] == "stopped"

    updated_forum = client.get(f"/api/v1/forums/{forum['id']}", headers=owner_headers)
    assert updated_forum.status_code == 200
    assert updated_forum.json()["status"] == "closed"


def test_forum_websocket_requires_token_and_accepts_authorized_client(client):
    owner_headers = register_and_login(client, "forum_owner_ws", role="admin")
    forum, _ = create_forum(client, owner_headers, topic="WS gate")

    with pytest.raises(Exception):
        with client.websocket_connect(f"/api/v1/forums/{forum['id']}/ws"):
            pass

    token = owner_headers["Authorization"].split(" ", 1)[1]
    with client.websocket_connect(f"/api/v1/forums/{forum['id']}/ws?token={token}") as websocket:
        websocket.send_text("ping")
        assert websocket.receive_text() == "pong"
