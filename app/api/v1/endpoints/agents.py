from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional, Any
from pydantic import BaseModel
import json
import logging
from urllib.parse import urljoin

from utils import get_chat_completion, LLMServiceError
from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas import MessageResponse
from app.crud import create_message, get_forum_messages, save_chat_message, get_chat_history, clear_chat_history
from app.agent.agent import ParticipantAgent
from app.agent.memory import SharedMemory

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentChatRequest(BaseModel):
    agent_name: str
    persona_json: dict
    context_messages: List[dict]
    theme: str = "AI对未来的影响"


class AgentChatResponse(BaseModel):
    content: str
    thought: Optional[dict] = None


def _latest_user_message(context_messages: List[dict]) -> str:
    for msg in reversed(context_messages):
        speaker = str(msg.get("speaker") or msg.get("role") or "").strip()
        if speaker in {"用户", "user"}:
            content = str(msg.get("content", "")).strip()
            if content:
                return content
    return ""


def _stream_fallback_message(request: Any, reason: str | None = None, error_kind: str | None = None) -> str:
    latest_user = _latest_user_message(getattr(request, "context_messages", []) or [])
    question_hint = f"你刚才的问题是：{latest_user}" if latest_user else "我暂时没有拿到完整的问题内容"

    if error_kind == "auth":
        advice = "请检查后端 API_KEY / BASE_URL 配置，确认密钥有效且拥有对应模型权限后再试。"
    elif error_kind == "permission":
        advice = "请检查当前账号是否具备该模型的调用权限后再试。"
    elif error_kind == "not_found":
        advice = "请检查模型名称和 BASE_URL 是否正确后再试。"
    elif error_kind == "rate_limit":
        advice = "请求过于频繁，请稍后再试。"
    elif error_kind == "timeout":
        advice = "请求超时，请稍后重试，或检查网络与上游服务状态。"
    elif error_kind == "network":
        advice = "无法连接上游服务，请检查网络与 BASE_URL 是否可达。"
    elif error_kind == "empty_stream":
        advice = "上游模型虽然连接成功，但没有返回可用内容，请稍后重试。"
    else:
        advice = "请稍后再试。"

    if reason:
        return f"抱歉，时空之门当前无法调用大模型服务，原因是：{reason}。{question_hint}。{advice}"

    return f"抱歉，时空之门当前无法调用大模型服务。{question_hint}。{advice}"


def _chunk_content(chunk: Any, use_vision: bool = False) -> str:
    if chunk is None:
        return ""

    if use_vision:
        if isinstance(chunk, dict):
            choices = chunk.get("choices") or []
            if not choices:
                return ""
            delta = choices[0].get("delta") or {}
            return str(delta.get("content") or "")
        return ""

    choices = getattr(chunk, "choices", None)
    if not choices:
        return ""

    try:
        delta = choices[0].delta
        return str(getattr(delta, "content", "") or "")
    except Exception:
        return ""


def _coerce_text_content(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    return ""


def _absolute_image_url(url: str, base_url: str = "") -> str:
    clean_url = _coerce_text_content(url)
    if not clean_url:
        return ""
    if clean_url.startswith(("http://", "https://")):
        return clean_url
    if base_url:
        return urljoin(base_url.rstrip("/") + "/", clean_url.lstrip("/"))
    return clean_url


def _normalize_message_content(content: Any, role: str, base_url: str = "") -> tuple[Any, bool]:
    if isinstance(content, list):
        normalized_parts = []
        for part in content:
            if not isinstance(part, dict):
                continue
            part_type = str(part.get("type") or "").strip()
            if part_type == "text":
                text = _coerce_text_content(part.get("text"))
                if text:
                    normalized_parts.append({"type": "text", "text": text})
            elif part_type == "image_url":
                image_url = part.get("image_url")
                if isinstance(image_url, dict):
                    url = _absolute_image_url(image_url.get("url"), base_url)
                    if url:
                        normalized_parts.append({"type": "image_url", "image_url": {"url": url}})
        if normalized_parts:
            return normalized_parts, True
        return "", False

    text = _coerce_text_content(content)
    if not text:
        return "", False

    has_image = "![image]" in text or "<img src=" in text
    if has_image and role == "user":
        content_parts = []
        import re

        img_pattern = r"!\[image\]\((.*?)\)|<img[^>]+src=[\"'](.*?)[\"']"
        matches = list(re.finditer(img_pattern, text))

        last_idx = 0
        for match in matches:
            if match.start() > last_idx:
                text_part = text[last_idx:match.start()].strip()
                if text_part:
                    content_parts.append({"type": "text", "text": text_part})

            img_url = match.group(1) or match.group(2)
            img_url = _absolute_image_url(img_url, base_url)
            if img_url:
                content_parts.append({"type": "image_url", "image_url": {"url": img_url}})
            last_idx = match.end()

        if last_idx < len(text):
            text_part = text[last_idx:].strip()
            if text_part:
                content_parts.append({"type": "text", "text": text_part})

        if content_parts:
            return content_parts, True

    return text, False


def _build_llm_messages(persona: dict, context_messages: List[dict], base_url: str = "") -> tuple[List[dict], bool]:
    system_prompt = _coerce_text_content(persona.get("system_prompt")) or "你是一个专业的智能助手。"
    messages = [{"role": "system", "content": system_prompt}]
    use_vision = False

    for msg in context_messages:
        speaker = str(msg.get("speaker") or msg.get("role") or "").strip()
        role = "user" if speaker in {"用户", "user"} else "assistant"
        content = _coerce_text_content(msg.get("content", ""))
        if not content:
            continue
        normalized_content, contains_image = _normalize_message_content(content, role, base_url)

        if normalized_content == "":
            continue

        if contains_image:
            use_vision = True

        messages.append({"role": role, "content": normalized_content})

    return messages, use_vision


def _build_shared_memory_context(context_messages: List[dict], n_participants: int = 3) -> str:
    memory = SharedMemory(n_participants=n_participants)

    for msg in context_messages:
        speaker = str(msg.get("speaker") or msg.get("role") or "").strip() or "Unknown"
        role = "user" if speaker in {"用户", "user"} else "assistant"
        normalized_content, _ = _normalize_message_content(msg.get("content", ""), role)

        if isinstance(normalized_content, list):
            text_parts = []
            for part in normalized_content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "text":
                    text = _coerce_text_content(part.get("text"))
                    if text:
                        text_parts.append(text)
            content_text = "\n".join(text_parts).strip()
        else:
            content_text = _coerce_text_content(normalized_content)

        if content_text:
            memory.add_message(speaker, content_text)

    return memory.get_context_str()


def _message_timestamp_ms(value: Any) -> int:
    if value is None:
        return int(__import__("time").time() * 1000)

    if isinstance(value, (int, float)):
        return int(value if value > 10_000_000_000 else value * 1000)

    timestamp = getattr(value, "timestamp", None)
    if callable(timestamp):
        try:
            return int(timestamp() * 1000)
        except Exception:
            pass

    try:
        return int(float(value))
    except Exception:
        return int(__import__("time").time() * 1000)


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(request: AgentChatRequest):
    """
    Directly invoke an agent to think and speak based on provided context.
    """
    try:
        agent = ParticipantAgent(
            name=request.agent_name,
            persona=request.persona_json,
            n_participants=3,
            theme=request.theme,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to initialize agent: {str(e)}")

    context_str = _build_shared_memory_context(request.context_messages, n_participants=3)
    thought = agent.think(context_str)

    if not thought:
        raise HTTPException(status_code=500, detail="Agent failed to think")

    if thought.get("action") == "listen":
        return AgentChatResponse(
            content=_stream_fallback_message(request, "模型判断当前更适合倾听，未生成发言内容", error_kind="empty_stream"),
            thought=thought,
        )

    response_stream = agent.speak(thought, context_str)
    full_content = ""
    if response_stream:
        for chunk in response_stream:
            full_content += _chunk_content(chunk)

    if not full_content.strip():
        full_content = _stream_fallback_message(request, "模型没有返回可解析的回答", error_kind="empty_stream")

    return AgentChatResponse(content=full_content, thought=thought)


@router.post("/chat/stream")
async def chat_with_agent_stream(request: AgentChatRequest, http_request: Request):
    """
    Streaming chat endpoint for time gate conversations.
    """
    messages, use_vision = _build_llm_messages(request.persona_json, request.context_messages, str(http_request.base_url))

    if len(messages) <= 1:
        async def empty_stream():
            yield f"data: {json.dumps({'content': _stream_fallback_message(request, '缺少有效的用户消息', error_kind='empty_stream')}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    async def generate():
        try:
            stream = get_chat_completion(messages, stream=True, use_vision=use_vision, raise_error=True)
            if not stream:
                yield f"data: {json.dumps({'content': _stream_fallback_message(request, '上游模型未返回有效流', error_kind='empty_stream')}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
                return

            emitted_any = False
            for chunk in stream:
                content = _chunk_content(chunk, use_vision=use_vision)
                if content:
                    emitted_any = True
                    yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"

            if not emitted_any:
                yield f"data: {json.dumps({'content': _stream_fallback_message(request, '上游模型返回了空内容', error_kind='empty_stream')}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except LLMServiceError as e:
            logger.error(f"Stream LLM error ({e.kind}): {e.details or e.message}")
            yield f"data: {json.dumps({'content': _stream_fallback_message(request, e.message, error_kind=e.kind)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'content': _stream_fallback_message(request, str(e), error_kind='unknown')}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/chat/history/{persona_id}")
async def get_user_chat_history(persona_id: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    """Get chat history for a specific persona."""
    history = get_chat_history(db, current_user.id, persona_id)
    return [
        {
            "role": msg.role,
            "content": msg.content,
            "timestamp": _message_timestamp_ms(getattr(msg, "created_at", None)),
        }
        for msg in history
    ]


@router.delete("/chat/history/{persona_id}")
async def clear_user_chat_history(persona_id: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    """Clear chat history for a specific persona."""
    success = clear_chat_history(db, current_user.id, persona_id)
    return {"success": success}


class ChatMessageCreate(BaseModel):
    persona_id: int
    role: str
    content: str


@router.post("/chat/message")
async def save_chat_message_endpoint(
    request: ChatMessageCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Persist a chat message."""
    msg = save_chat_message(
        db,
        user_id=current_user.id,
        persona_id=request.persona_id,
        role=request.role,
        content=request.content,
    )
    return {"success": msg is not None, "id": msg.id if msg else None}
