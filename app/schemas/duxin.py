from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

DuxinMode = Literal["support", "relationship", "growth", "crisis"]
DuxinRiskLevel = Literal["L0", "L1", "L2", "L3"]
DuxinMemoryType = Literal["preference", "trigger", "support_method", "goal", "note"]
DuxinFeedbackRating = Literal["helpful", "not_helpful", "needs_follow_up"]


class DuxinSessionCreate(BaseModel):
    mode: DuxinMode = "support"
    title: Optional[str] = None
    initial_message: Optional[str] = None


class DuxinSessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    mode: DuxinMode
    risk_level: DuxinRiskLevel
    status: str
    summary: Optional[str] = None
    latest_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DuxinMessageCreate(BaseModel):
    content: str = Field(min_length=1)


class DuxinMessageResponse(BaseModel):
    id: int
    session_id: int
    user_id: int
    role: Literal["user", "assistant", "system"]
    agent_name: Optional[str] = None
    content: str
    risk_level: DuxinRiskLevel = "L0"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("metadata", mode="before")
    @classmethod
    def _parse_metadata(cls, value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}


class DuxinMemoryCreate(BaseModel):
    memory_type: DuxinMemoryType = "note"
    content: str = Field(min_length=1)
    source_session_id: Optional[int] = None
    user_editable: bool = True


class DuxinMemoryUpdate(BaseModel):
    memory_type: Optional[DuxinMemoryType] = None
    content: Optional[str] = Field(default=None, min_length=1)
    user_editable: Optional[bool] = None


class DuxinMemoryResponse(BaseModel):
    id: int
    user_id: int
    memory_type: DuxinMemoryType
    content: str
    source_session_id: Optional[int] = None
    user_editable: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DuxinMemorySummaryItem(BaseModel):
    id: int
    memory_type: DuxinMemoryType
    content: str
    source_session_id: Optional[int] = None
    user_editable: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DuxinMemorySummaryResponse(BaseModel):
    total: int
    by_type: Dict[DuxinMemoryType, int]
    recent: List[DuxinMemorySummaryItem]


class DuxinRiskAssessment(BaseModel):
    risk_level: DuxinRiskLevel
    signals: List[str] = Field(default_factory=list)
    response_mode: Literal["support", "stabilize", "crisis"] = "support"
    should_escalate: bool = False
    summary: str
    recommended_actions: List[str] = Field(default_factory=list)


class DuxinSafetyFeedbackCreate(BaseModel):
    session_id: Optional[int] = None
    rating: DuxinFeedbackRating = "helpful"
    content: Optional[str] = None
    risk_level: Optional[DuxinRiskLevel] = None
    save_as_memory: bool = False
    memory_type: Optional[DuxinMemoryType] = None


class DuxinSafetyFeedbackResponse(BaseModel):
    id: int
    user_id: int
    session_id: Optional[int] = None
    rating: DuxinFeedbackRating
    content: Optional[str] = None
    risk_level: Optional[DuxinRiskLevel] = None
    linked_memory_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DuxinSafetyFeedbackStats(BaseModel):
    total: int
    helpful: int
    not_helpful: int
    needs_follow_up: int
    by_risk_level: Dict[DuxinRiskLevel, int]
    recent: List[DuxinSafetyFeedbackResponse]


class DuxinStreamRequest(BaseModel):
    session_id: int
    content: str = Field(min_length=1)
