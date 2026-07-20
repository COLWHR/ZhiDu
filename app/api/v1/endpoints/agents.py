from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.crud import (
    clear_chat_history,
    create_artifact,
    create_task_run,
    get_chat_history,
    get_task_run,
    save_chat_attachments,
    save_chat_message,
    update_task_run,
)
from app.db.session import get_db
from app.schemas import ArtifactCreate, ArtifactResponse, AttachmentResponse, TaskRunCreate, TaskRunUpdate
from app.agent.agent import ParticipantAgent
from app.agent.memory import SharedMemory
from app.services.skill_runtime import (
    build_llm_messages,
    infer_skill_route,
    render_csv_artifact,
    render_png_artifact,
    render_text_artifact,
)
from utils import LLMServiceError, get_chat_completion

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatAttachmentInput(BaseModel):
    id: Optional[int] = None
    file_name: str
    mime_type: Optional[str] = None
    kind: Optional[str] = None
    storage_url: Optional[str] = None
    preview_url: Optional[str] = None
    size: Optional[int] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class AgentChatRequest(BaseModel):
    agent_name: str
    persona_json: Dict[str, Any]
    context_messages: List[Dict[str, Any]] = Field(default_factory=list)
    attachments: List[ChatAttachmentInput] = Field(default_factory=list)
    theme: str = "自由对话"
    skill_hints: List[str] = Field(default_factory=list)


class AgentChatResponse(BaseModel):
    content: str
    thought: Optional[dict] = None
    artifacts: List[ArtifactResponse] = Field(default_factory=list)
    route: Optional[Dict[str, Any]] = None


class ChatMessageCreate(BaseModel):
    persona_id: int
    role: str
    content: str
    message_type: str = "text"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    attachment_ids: List[int] = Field(default_factory=list)


def _latest_user_message(context_messages: List[dict]) -> str:
    for msg in reversed(context_messages or []):
        speaker = str(msg.get("speaker") or msg.get("role") or "").strip().lower()
        if speaker in {"user", "用户", "鐢ㄦ埛"}:
            content = str(msg.get("content", "")).strip()
            if content:
                return content
    return ""


def _chunk_content(chunk: Any, use_vision: bool = False) -> str:
    if chunk is None:
        return ""

    if use_vision and isinstance(chunk, dict):
        choices = chunk.get("choices") or []
        if not choices:
            return ""
        delta = choices[0].get("delta") or {}
        return str(delta.get("content") or "")

    choices = getattr(chunk, "choices", None)
    if not choices:
        return ""

    try:
        delta = choices[0].delta
        return str(getattr(delta, "content", "") or "")
    except Exception:
        return ""


def _absolute_image_url(url: str, base_url: str = "") -> str:
    clean_url = str(url or "").strip()
    if not clean_url:
        return ""
    if clean_url.startswith(("http://", "https://")):
        return clean_url
    if base_url:
        return urljoin(base_url.rstrip("/") + "/", clean_url.lstrip("/"))
    return clean_url


def _build_context_messages_with_attachments(
    persona: Dict[str, Any],
    context_messages: List[dict],
    attachments: List[dict],
    base_url: str = "",
) -> tuple[list[dict], bool, dict[str, Any]]:
    messages, use_vision, route = build_llm_messages(persona, context_messages, attachments, base_url=base_url)
    return messages, use_vision, route


def _artifact_from_text(
    db,
    owner_id: int,
    persona_id: Optional[int],
    task_run_id: Optional[int],
    artifact_type: str,
    title: str,
    text: str,
) -> ArtifactResponse:
    artifact_type = (artifact_type or "docx").lower()
    if artifact_type in {"csv", "sheet"}:
        file_name, mime_type, storage_url = render_csv_artifact([{"content": text}], title=title)
    elif artifact_type in {"png", "image"}:
        file_name, mime_type, storage_url = render_png_artifact(text, title=title)
    else:
        file_name, mime_type, storage_url = render_text_artifact(text, title=title)

    artifact = create_artifact(
        db,
        ArtifactCreate(
            owner_id=owner_id,
            persona_id=persona_id,
            task_run_id=task_run_id,
            artifact_type=artifact_type,
            file_name=file_name,
            mime_type=mime_type,
            storage_url=storage_url,
            preview_url=storage_url,
            version=1,
            status="ready",
            meta={"title": title},
        ),
    )
    return ArtifactResponse.model_validate(artifact)


def _owner_id_from_request(persona_json: Dict[str, Any]) -> int:
    try:
        return int(persona_json.get("owner_id") or 1)
    except Exception:
        return 1


def _maybe_create_artifact(
    db,
    request: AgentChatRequest,
    route: dict[str, Any],
    content: str,
    task_run_id: Optional[int] = None,
) -> list[ArtifactResponse]:
    if not route.get("should_generate_artifact"):
        return []

    owner_id = _owner_id_from_request(request.persona_json)
    persona_id = request.persona_json.get("id")
    artifact_type = route.get("artifact_type") or "docx"
    artifact = _artifact_from_text(
        db=db,
        owner_id=owner_id,
        persona_id=persona_id,
        task_run_id=task_run_id,
        artifact_type=artifact_type,
        title=request.agent_name or "artifact",
        text=content,
    )
    return [artifact]


def _stream_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _message_timestamp_ms(value: Any) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, datetime):
        return int(value.timestamp() * 1000)
    if isinstance(value, str):
        try:
            return int(float(value))
        except Exception:
            try:
                return int(datetime.fromisoformat(value).timestamp() * 1000)
            except Exception:
                return int(datetime.now().timestamp() * 1000)
    return int(datetime.now().timestamp() * 1000)


def _json_value(value: Any, fallback: Any = None) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return fallback if fallback is not None else value
    return value if value is not None else fallback


def _task_run_update(
    status: str,
    progress: int,
    output_payload: Optional[dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> TaskRunUpdate:
    return TaskRunUpdate(
        status=status,
        progress=progress,
        output_payload=output_payload,
        error_message=error_message,
    )


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(request: AgentChatRequest, db=Depends(get_db)):
    try:
        messages, use_vision, route = _build_context_messages_with_attachments(
            request.persona_json,
            request.context_messages,
            [att.model_dump() for att in request.attachments],
            base_url="",
        )

        if len(messages) <= 1:
            return AgentChatResponse(
                content="抱歉，我暂时没有收到有效输入。",
                route=route,
            )

        try:
            response = get_chat_completion(messages, stream=False, use_vision=use_vision, raise_error=True)
            content = ""
            if response and getattr(response, "choices", None):
                content = response.choices[0].message.content or ""
        except LLMServiceError as exc:
            return AgentChatResponse(content=exc.message, thought=None, route=route)

        if not content.strip():
            content = "抱歉，我暂时无法生成内容。"

        task_run = None
        if route.get("should_generate_artifact"):
            task_run = create_task_run(
                db,
                TaskRunCreate(
                    owner_id=_owner_id_from_request(request.persona_json),
                    persona_id=request.persona_json.get("id"),
                    skill_key=route.get("skill_key"),
                    session_id=None,
                    status="done",
                    progress=100,
                    input_payload={"theme": request.theme},
                    output_payload={"preview": content[:200]},
                ),
            )

        artifacts = _maybe_create_artifact(db, request, route, content, task_run_id=getattr(task_run, "id", None))

        return AgentChatResponse(content=content, route=route, artifacts=artifacts)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent failed: {exc}")


@router.post("/chat/stream")
async def chat_with_agent_stream(request: AgentChatRequest, http_request: Request, db=Depends(get_db)):
    try:
        messages, use_vision, route = _build_context_messages_with_attachments(
            request.persona_json,
            request.context_messages,
            [att.model_dump() for att in request.attachments],
            base_url=str(http_request.base_url),
        )

        if len(messages) <= 1:
            async def empty_stream():
                yield _stream_event({"content": "抱歉，我暂时没有收到有效输入。"})
                yield "data: [DONE]\n\n"

            return StreamingResponse(empty_stream(), media_type="text/event-stream")

        owner_id = _owner_id_from_request(request.persona_json)
        task_run = None
        if route.get("should_generate_artifact"):
            task_run = create_task_run(
                db,
                TaskRunCreate(
                    owner_id=owner_id,
                    persona_id=request.persona_json.get("id"),
                    skill_key=route.get("skill_key"),
                    session_id=None,
                    status="running",
                    progress=5,
                    input_payload={"theme": request.theme},
                    output_payload={},
                ),
            )

        async def generate():
            full_content = ""
            artifact_payload: list[ArtifactResponse] = []
            try:
                stream = get_chat_completion(messages, stream=True, use_vision=use_vision, raise_error=True)
                if not stream:
                    yield _stream_event({"content": "抱歉，我暂时无法调用模型服务。"})
                    yield "data: [DONE]\n\n"
                    return

                emitted_any = False
                for chunk in stream:
                    content = _chunk_content(chunk, use_vision=use_vision)
                    if content:
                        emitted_any = True
                        full_content += content
                        yield _stream_event({"content": content})

                if not emitted_any:
                    full_content = "抱歉，我暂时无法调用模型服务。"
                    yield _stream_event({"content": full_content})

                if route.get("should_generate_artifact"):
                    artifact_payload = _maybe_create_artifact(
                        db,
                        request,
                        route,
                        full_content,
                        task_run_id=getattr(task_run, "id", None),
                    )
                    if task_run:
                        update_task_run(
                            db,
                            task_run.id,
                            _task_run_update(
                                status="done",
                                progress=100,
                                output_payload={"artifact_ids": [a.id for a in artifact_payload]},
                            ),
                        )
                    for artifact in artifact_payload:
                        yield _stream_event({"type": "artifact", "artifact": artifact.model_dump(mode="json")})
                yield "data: [DONE]\n\n"
            except LLMServiceError as e:
                if task_run:
                    update_task_run(
                        db,
                        task_run.id,
                        _task_run_update(status="failed", progress=100, error_message=e.message),
                    )
                yield _stream_event({"error": e.message, "kind": e.kind})
                yield "data: [DONE]\n\n"
            except Exception as e:
                if task_run:
                    update_task_run(
                        db,
                        task_run.id,
                        _task_run_update(status="failed", progress=100, error_message=str(e)),
                    )
                yield _stream_event({"error": str(e)})
                yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Stream failed: {exc}")


@router.get("/chat/history/{persona_id}")
async def get_user_chat_history(persona_id: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    history = get_chat_history(db, current_user.id, persona_id)
    return [
        {
            "role": msg.role,
            "content": msg.content,
            "message_type": getattr(msg, "message_type", "text"),
            "metadata": _json_value(getattr(msg, "metadata", {}), {}),
            "attachments": [
                {
                    "id": att.id,
                    "file_name": att.file_name,
                    "mime_type": att.mime_type,
                    "kind": att.kind,
                    "storage_url": att.storage_url,
                    "preview_url": att.preview_url,
                    "size": att.size,
                    "meta": _json_value(getattr(att, "meta", {}), {}),
                }
                for att in (getattr(msg, "attachments", []) or [])
            ],
            "timestamp": _message_timestamp_ms(getattr(msg, "created_at", None)),
        }
        for msg in history
    ]


@router.delete("/chat/history/{persona_id}")
async def clear_user_chat_history(persona_id: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    success = clear_chat_history(db, current_user.id, persona_id)
    return {"success": success}


@router.post("/chat/message")
async def save_chat_message_endpoint(
    request: ChatMessageCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    msg = save_chat_message(
        db,
        user_id=current_user.id,
        persona_id=request.persona_id,
        role=request.role,
        content=request.content,
        message_type=request.message_type,
        metadata=request.metadata,
    )
    if request.attachment_ids:
        save_chat_attachments(db, msg.id, request.attachment_ids)
    return {"success": msg is not None, "id": msg.id if msg else None}
