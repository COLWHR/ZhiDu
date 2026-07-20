from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas import (
    ArtifactResponse,
    AttachmentResponse,
    TaskRunCreate,
    TaskRunResponse,
    TaskRunUpdate,
)
from app.crud import create_task_run, get_attachment, get_artifact, get_task_run, update_task_run
from app.services.skill_runtime import PROJECT_ROOT

router = APIRouter()


def _safe_local_path(storage_url: str) -> Path:
    rel = storage_url.lstrip("/")
    return PROJECT_ROOT / rel


@router.get("/attachments/{attachment_id}", response_model=AttachmentResponse)
def read_attachment(attachment_id: int, db=Depends(get_db), current_user: Any = Depends(get_current_user)):
    attachment = get_attachment(db, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if attachment.owner_id != current_user.id and current_user.role != "god":
        raise HTTPException(status_code=403, detail="Not authorized")
    return attachment


@router.get("/attachments/{attachment_id}/download")
def download_attachment(attachment_id: int, db=Depends(get_db), current_user: Any = Depends(get_current_user)):
    attachment = get_attachment(db, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if attachment.owner_id != current_user.id and current_user.role != "god":
        raise HTTPException(status_code=403, detail="Not authorized")

    path = _safe_local_path(attachment.storage_url)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(path), filename=attachment.file_name)


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
def read_artifact(artifact_id: int, db=Depends(get_db), current_user: Any = Depends(get_current_user)):
    artifact = get_artifact(db, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if artifact.owner_id != current_user.id and current_user.role != "god":
        raise HTTPException(status_code=403, detail="Not authorized")
    return artifact


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: int, db=Depends(get_db), current_user: Any = Depends(get_current_user)):
    artifact = get_artifact(db, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if artifact.owner_id != current_user.id and current_user.role != "god":
        raise HTTPException(status_code=403, detail="Not authorized")

    path = _safe_local_path(artifact.storage_url)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(path), filename=artifact.file_name)


@router.post("/task-runs", response_model=TaskRunResponse)
def create_task_run_endpoint(payload: TaskRunCreate, db=Depends(get_db), current_user: Any = Depends(get_current_user)):
    if payload.owner_id != current_user.id and current_user.role != "god":
        payload.owner_id = current_user.id
    return create_task_run(db, payload)


@router.get("/task-runs/{task_run_id}", response_model=TaskRunResponse)
def read_task_run(task_run_id: int, db=Depends(get_db), current_user: Any = Depends(get_current_user)):
    task_run = get_task_run(db, task_run_id)
    if not task_run:
        raise HTTPException(status_code=404, detail="Task run not found")
    if task_run.owner_id != current_user.id and current_user.role != "god":
        raise HTTPException(status_code=403, detail="Not authorized")
    return task_run


@router.patch("/task-runs/{task_run_id}", response_model=TaskRunResponse)
def patch_task_run(task_run_id: int, payload: TaskRunUpdate, db=Depends(get_db), current_user: Any = Depends(get_current_user)):
    task_run = get_task_run(db, task_run_id)
    if not task_run:
        raise HTTPException(status_code=404, detail="Task run not found")
    if task_run.owner_id != current_user.id and current_user.role != "god":
        raise HTTPException(status_code=403, detail="Not authorized")
    return update_task_run(db, task_run_id, payload)
