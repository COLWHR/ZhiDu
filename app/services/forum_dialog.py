from __future__ import annotations

import json
from typing import Any, Iterable, List
from urllib.parse import urljoin

from app.agent.memory import SharedMemory


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    return ""


def _absolute_image_url(url: str, base_url: str = "") -> str:
    clean_url = _coerce_text(url)
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
                text = _coerce_text(part.get("text"))
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

    text = _coerce_text(content)
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


def build_shared_memory_context(context_messages: List[dict], n_participants: int = 3, base_url: str = "") -> str:
    memory = SharedMemory(n_participants=n_participants)

    for msg in context_messages:
        speaker = str(msg.get("speaker") or msg.get("speaker_name") or msg.get("role") or "").strip() or "Unknown"
        role = "user" if speaker in {"用户", "user", "观众"} else "assistant"
        normalized_content, _ = _normalize_message_content(msg.get("content", ""), role, base_url)

        if isinstance(normalized_content, list):
            text_parts = []
            for part in normalized_content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "text":
                    text = _coerce_text(part.get("text"))
                    if text:
                        text_parts.append(text)
            content_text = "\n".join(text_parts).strip()
        else:
            content_text = _coerce_text(normalized_content)

        if content_text:
            memory.add_message(speaker, content_text)

    return memory.get_context_str()


def chunk_content(chunk: Any, use_vision: bool = False) -> str:
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


def persona_to_agent_payload(persona: Any) -> dict:
    if persona is None:
        return {
            "name": "未命名智能体",
            "title": "智能体",
            "bio": "",
            "theories": [],
            "stance": "中立",
            "system_prompt": "",
        }

    theories = getattr(persona, "theories", []) or []
    if isinstance(theories, str):
        try:
            parsed = json.loads(theories)
            theories = parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            theories = []

    return {
        "name": _coerce_text(getattr(persona, "name", None)),
        "title": _coerce_text(getattr(persona, "title", None)) or "智能体",
        "bio": _coerce_text(getattr(persona, "bio", None)),
        "theories": theories,
        "stance": _coerce_text(getattr(persona, "stance", None)) or "中立",
        "system_prompt": _coerce_text(getattr(persona, "system_prompt", None)),
    }
