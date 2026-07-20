from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any
from datetime import datetime

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas import SkillResponse
from app.services.skill_runtime import get_skill_catalog
from app.services import skillhub_repository

router = APIRouter()


@router.get("/catalog", response_model=list[SkillResponse])
def read_skill_catalog(current_user: Any = Depends(get_current_user), db=Depends(get_db)):
    del current_user, db
    return [
        SkillResponse(
            id=index + 1,
            created_at=datetime.now(),
            updated_at=None,
            **skill,
        )
        for index, skill in enumerate(get_skill_catalog())
    ]


@router.post("/sync/skillhub")
def sync_skillhub_catalog(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: Any = Depends(get_current_user),
    db=Depends(get_db),
):
    del current_user, db
    synced = skillhub_repository.sync_skillhub_skills(limit=limit)
    timestamp = datetime.now()
    return {
        "count": len(synced),
        "skills": [
            SkillResponse(id=index + 1, created_at=timestamp, updated_at=None, **skill).model_dump(mode="json")
            for index, skill in enumerate(synced)
        ],
    }


@router.get("/{skill_key}", response_model=SkillResponse)
def read_skill(skill_key: str, current_user: Any = Depends(get_current_user), db=Depends(get_db)):
    del current_user, db
    for index, skill in enumerate(get_skill_catalog()):
        if skill["skill_key"] == skill_key:
            return SkillResponse(id=index + 1, created_at=datetime.now(), updated_at=None, **skill)
    raise HTTPException(status_code=404, detail="Skill not found")
