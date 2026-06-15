from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.duxin import (
    DuxinMemoryCreate,
    DuxinMemoryResponse,
    DuxinMemorySummaryResponse,
    DuxinMemoryUpdate,
    DuxinMessageCreate,
    DuxinSafetyFeedbackCreate,
    DuxinSafetyFeedbackResponse,
    DuxinSafetyFeedbackStats,
    DuxinSessionCreate,
    DuxinSessionResponse,
)
from app.services.duxin_chat_orchestrator import stream_session_chat
import app.services.duxin_chat_orchestrator as duxin_chat_orchestrator
from app.services.duxin_memory_service import duxin_memory_service
from app.services.duxin_serializers import (
    feedback_summary_to_dict,
    feedback_to_dict,
    memory_summary_to_dict,
    memory_to_dict,
    session_to_dict,
)
from app.services.duxin_session_service import duxin_session_service
from utils import get_chat_completion

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sessions", response_model=DuxinSessionResponse)
async def create_session(
    payload: DuxinSessionCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    session = duxin_session_service.create_session_with_message(
        db,
        user_id=current_user.id,
        mode=payload.mode,
        title=payload.title,
        initial_message=payload.initial_message,
    )
    if not session:
        raise HTTPException(status_code=500, detail="Failed to create duxin session")
    return session_to_dict(session)


@router.get("/sessions", response_model=list[DuxinSessionResponse])
async def list_sessions(db=Depends(get_db), current_user=Depends(get_current_user)):
    return [session_to_dict(session) for session in duxin_session_service.list_sessions(db, user_id=current_user.id)]


@router.get("/sessions/{session_id}", response_model=DuxinSessionResponse)
async def get_session(session_id: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    session = duxin_session_service.get_session(db, user_id=current_user.id, session_id=session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Duxin session not found")
    return session_to_dict(session)


@router.get("/sessions/{session_id}/messages")
async def list_messages(session_id: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    session = duxin_session_service.get_session(db, user_id=current_user.id, session_id=session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Duxin session not found")
    messages = duxin_session_service.list_messages(db, user_id=current_user.id, session_id=session_id)
    from app.services.duxin_serializers import message_to_dict

    return [message_to_dict(message) for message in messages]


@router.post("/sessions/{session_id}/archive", response_model=DuxinSessionResponse)
async def archive_session(session_id: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    session = duxin_session_service.archive_session(db, user_id=current_user.id, session_id=session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Duxin session not found")
    return session_to_dict(session)


@router.post("/sessions/{session_id}/chat/stream")
async def chat_stream(
    session_id: int,
    payload: DuxinMessageCreate = Body(...),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        duxin_chat_orchestrator.get_chat_completion = get_chat_completion
        return await stream_session_chat(session_id=session_id, payload=payload, db=db, current_user=current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/memories", response_model=list[DuxinMemoryResponse])
async def list_memories(db=Depends(get_db), current_user=Depends(get_current_user)):
    memories = duxin_memory_service.list_memories(db, user_id=current_user.id)
    return [memory_to_dict(memory) for memory in memories]


@router.get("/memories/summary", response_model=DuxinMemorySummaryResponse)
async def memory_summary(db=Depends(get_db), current_user=Depends(get_current_user)):
    summary = duxin_memory_service.get_memory_summary(db, user_id=current_user.id)
    return memory_summary_to_dict(summary)


@router.post("/memories", response_model=DuxinMemoryResponse)
async def create_memory(payload: DuxinMemoryCreate, db=Depends(get_db), current_user=Depends(get_current_user)):
    memory = duxin_memory_service.create_memory(
        db,
        user_id=current_user.id,
        memory_type=payload.memory_type,
        content=payload.content,
        source_session_id=payload.source_session_id,
        user_editable=payload.user_editable,
    )
    if not memory:
        raise HTTPException(status_code=500, detail="Failed to save memory")
    return memory_to_dict(memory)


@router.patch("/memories/{memory_id}", response_model=DuxinMemoryResponse)
async def update_memory(
    memory_id: int,
    payload: DuxinMemoryUpdate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    memory = duxin_memory_service.update_memory(
        db,
        user_id=current_user.id,
        memory_id=memory_id,
        memory_type=payload.memory_type,
        content=payload.content,
        user_editable=payload.user_editable,
    )
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory_to_dict(memory)


@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    ok = duxin_memory_service.delete_memory(db, user_id=current_user.id, memory_id=memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True}


@router.delete("/memories")
async def clear_memories(db=Depends(get_db), current_user=Depends(get_current_user)):
    ok = duxin_memory_service.clear_memories(db, user_id=current_user.id)
    return {"success": ok}


@router.get("/safety/feedback", response_model=list[DuxinSafetyFeedbackResponse])
async def list_safety_feedback(
    session_id: Optional[int] = None,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    feedback = duxin_session_service.list_feedback(db, user_id=current_user.id, session_id=session_id)
    return [feedback_to_dict(item) for item in feedback]


@router.get("/safety/feedback/summary", response_model=DuxinSafetyFeedbackStats)
async def safety_feedback_summary(db=Depends(get_db), current_user=Depends(get_current_user)):
    summary = duxin_session_service.build_feedback_summary(db, user_id=current_user.id)
    return feedback_summary_to_dict(summary)


@router.post("/safety/feedback", response_model=DuxinSafetyFeedbackResponse)
async def submit_safety_feedback(
    payload: DuxinSafetyFeedbackCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    feedback = duxin_session_service.save_feedback(
        db,
        user_id=current_user.id,
        session_id=payload.session_id,
        rating=payload.rating,
        content=payload.content,
        risk_level=payload.risk_level,
    )
    if not feedback:
        raise HTTPException(status_code=500, detail="Failed to save feedback")

    linked_memory_id = None
    if payload.save_as_memory and payload.content:
        memory_content = payload.content.strip()
        if payload.risk_level:
            memory_content += f" / 风险：{payload.risk_level}"
        memory = duxin_memory_service.create_memory(
            db,
            user_id=current_user.id,
            memory_type=payload.memory_type or "note",
            content=memory_content,
            source_session_id=payload.session_id,
            user_editable=True,
        )
        linked_memory_id = getattr(memory, "id", None) if memory else None

    feedback_dict = feedback_to_dict(feedback)
    if linked_memory_id:
        feedback_dict["linked_memory_id"] = linked_memory_id
    return feedback_dict
