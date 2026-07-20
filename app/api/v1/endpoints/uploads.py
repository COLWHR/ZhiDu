from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_current_user
from app.crud import create_attachment
from app.db.session import get_db
from app.schemas import AttachmentCreate, AttachmentResponse
from app.services.skill_runtime import (
    UPLOADS_ROOT,
    attachment_public_url,
    file_sha256,
    infer_attachment_kind,
    make_attachment_path,
)

router = APIRouter()


def _store_upload(file: UploadFile, current_user, db, image_only: bool = False) -> AttachmentResponse:
    file_name = file.filename or "upload.bin"
    kind = infer_attachment_kind(file.content_type, file_name)
    if image_only and kind != "image":
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    target_path = make_attachment_path(file_name)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    relative_path = target_path.relative_to(UPLOADS_ROOT.parent)
    storage_url = attachment_public_url(relative_path)
    preview_url = storage_url if kind == "image" else None
    size = target_path.stat().st_size
    sha256 = file_sha256(target_path)

    attachment = create_attachment(
        db,
        AttachmentCreate(
            owner_id=current_user.id,
            file_name=file_name,
            mime_type=file.content_type,
            size=size,
            kind=kind,
            storage_url=storage_url,
            preview_url=preview_url,
            sha256=sha256,
            meta={
                "original_name": file_name,
                "path": str(relative_path).replace("\\", "/"),
            },
        ),
    )

    return AttachmentResponse.model_validate(attachment)


@router.post("/upload/asset", response_model=AttachmentResponse)
async def upload_asset(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    try:
        return _store_upload(file, current_user, db, image_only=False)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"File upload failed: {exc}")


@router.post("/upload/image", response_model=AttachmentResponse)
async def upload_image(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    try:
        return _store_upload(file, current_user, db, image_only=True)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {exc}")
