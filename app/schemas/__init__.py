from typing import List, Optional, Any, Union, Dict, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
import json

# --- User Schemas ---
class UserBase(BaseModel):
    username: str
    role: Optional[str] = "user"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime

class TokenData(BaseModel):
    username: Optional[str] = None

# --- Persona Schemas ---
class PersonaBase(BaseModel):
    name: str
    title: Optional[str] = None
    bio: Optional[str] = None
    theories: Optional[List[str]] = Field(default_factory=list)
    stance: Optional[str] = None
    system_prompt: Optional[str] = None
    is_public: bool = False
    avatar: Optional[str] = None
    skills: List[str] = Field(default_factory=lambda: ["chat.reply"])
    skill_policy: Dict[str, Any] = Field(default_factory=dict)
    modalities: List[str] = Field(default_factory=lambda: ["text"])
    capabilities_version: int = 1

class PersonaCreate(PersonaBase):
    pass

class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    theories: Optional[List[str]] = None
    stance: Optional[str] = None
    system_prompt: Optional[str] = None
    is_public: Optional[bool] = None
    avatar: Optional[str] = None
    skills: Optional[List[str]] = None
    skill_policy: Optional[Dict[str, Any]] = None
    modalities: Optional[List[str]] = None
    capabilities_version: Optional[int] = None

class PersonaResponse(PersonaBase):
    id: int
    owner_id: int
    created_at: datetime
    theories: Optional[Union[List[str], str]] = Field(default_factory=list)
    skills: Optional[Union[List[str], str]] = Field(default_factory=list)
    modalities: Optional[Union[List[str], str]] = Field(default_factory=list)
    skill_policy: Optional[Union[Dict[str, Any], str]] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("theories", "skills", "modalities", mode="before")
    @classmethod
    def parse_json_list(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                return []
            except json.JSONDecodeError:
                return []
        elif v is None:
            return []
        return v

    @field_validator("skill_policy", mode="before")
    @classmethod
    def parse_skill_policy(cls, v: Any) -> Dict[str, Any]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
                return {}
            except json.JSONDecodeError:
                return {}
        if v is None:
            return {}
        return v


class SkillBase(BaseModel):
    skill_key: str
    name: str
    category: str = "general"
    description: Optional[str] = None
    input_modalities: List[str] = Field(default_factory=list)
    output_types: List[str] = Field(default_factory=list)
    required_models: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    params_schema: Dict[str, Any] = Field(default_factory=dict)
    permission_scope: List[str] = Field(default_factory=list)
    cost_level: str = "low"
    status: str = "active"
    source: Optional[str] = None
    source_url: Optional[str] = None
    source_slug: Optional[str] = None
    source_rank: Optional[int] = None
    source_owner: Optional[str] = None
    source_version: Optional[str] = None
    icon_url: Optional[str] = None
    downloads: int = 0
    installs: int = 0
    stars: int = 0
    score: Optional[float] = None
    sub_categories: List[str] = Field(default_factory=list)
    synced_at: Optional[str] = None
    security_reports: Dict[str, Any] = Field(default_factory=dict)


class SkillCreate(SkillBase):
    pass


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    input_modalities: Optional[List[str]] = None
    output_types: Optional[List[str]] = None
    required_models: Optional[List[str]] = None
    required_tools: Optional[List[str]] = None
    params_schema: Optional[Dict[str, Any]] = None
    permission_scope: Optional[List[str]] = None
    cost_level: Optional[str] = None
    status: Optional[str] = None


class SkillResponse(SkillBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AttachmentBase(BaseModel):
    owner_id: int
    file_name: str
    mime_type: Optional[str] = None
    size: Optional[int] = None
    kind: Optional[str] = None
    storage_url: str
    preview_url: Optional[str] = None
    sha256: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class AttachmentCreate(AttachmentBase):
    persona_id: Optional[int] = None
    chat_message_id: Optional[int] = None
    session_id: Optional[int] = None


class AttachmentResponse(AttachmentBase):
    id: int
    persona_id: Optional[int] = None
    chat_message_id: Optional[int] = None
    session_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("meta", mode="before")
    @classmethod
    def parse_meta(cls, v: Any) -> Dict[str, Any]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {}
        if v is None:
            return {}
        return v


class ArtifactBase(BaseModel):
    owner_id: int
    artifact_type: str
    file_name: str
    mime_type: Optional[str] = None
    storage_url: str
    preview_url: Optional[str] = None
    version: int = 1
    status: str = "ready"
    meta: Dict[str, Any] = Field(default_factory=dict)


class ArtifactCreate(ArtifactBase):
    persona_id: Optional[int] = None
    task_run_id: Optional[int] = None


class ArtifactResponse(ArtifactBase):
    id: int
    persona_id: Optional[int] = None
    task_run_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("meta", mode="before")
    @classmethod
    def parse_meta(cls, v: Any) -> Dict[str, Any]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {}
        if v is None:
            return {}
        return v


class TaskRunBase(BaseModel):
    persona_id: Optional[int] = None
    skill_key: Optional[str] = None
    session_id: Optional[int] = None
    status: str = "queued"
    progress: int = 0
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    output_payload: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class TaskRunCreate(TaskRunBase):
    owner_id: int


class TaskRunUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[int] = None
    output_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class TaskRunResponse(TaskRunBase):
    id: int
    owner_id: int
    started_at: datetime
    finished_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("input_payload", "output_payload", mode="before")
    @classmethod
    def parse_payloads(cls, v: Any) -> Dict[str, Any]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {}
        if v is None:
            return {}
        return v

# --- Moderator Schemas ---
class ModeratorBase(BaseModel):
    name: str
    title: Optional[str] = "主持人"
    bio: Optional[str] = None
    system_prompt: Optional[str] = None
    greeting_template: Optional[str] = None
    closing_template: Optional[str] = None
    summary_template: Optional[str] = None

class ModeratorCreate(ModeratorBase):
    pass

class ModeratorUpdate(ModeratorBase):
    pass

class ModeratorResponse(ModeratorBase):
    id: int
    creator_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

from .system_log import SystemLogCreate, SystemLogResponse
from .duxin import (
    DuxinFeedbackRating,
    DuxinMemoryCreate,
    DuxinMemoryResponse,
    DuxinMemorySummaryItem,
    DuxinMemorySummaryResponse,
    DuxinMemoryType,
    DuxinMemoryUpdate,
    DuxinMode,
    DuxinMessageCreate,
    DuxinMessageResponse,
    DuxinRiskAssessment,
    DuxinRiskLevel,
    DuxinSafetyFeedbackCreate,
    DuxinSafetyFeedbackResponse,
    DuxinSafetyFeedbackStats,
    DuxinSessionCreate,
    DuxinSessionResponse,
    DuxinStreamRequest,
)

# --- Forum Schemas ---
class ForumBase(BaseModel):
    topic: str

class ForumCreate(ForumBase):
    participant_ids: List[int]
    moderator_id: Optional[int] = None # Optional for backward compatibility (can use default)
    duration_minutes: int = 30

class ForumParticipantResponse(BaseModel):
    persona_id: int
    thoughts_history: Optional[Union[List[Any], str]] = [] # Changed from List[str] to List[Any] to support dicts
    persona: Optional[PersonaResponse] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator('thoughts_history', mode='before')
    @classmethod
    def parse_thoughts_history(cls, v: Any) -> List[Any]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                # If it's a dict (single thought), wrap in list? Or return empty?
                # Based on log, it seems to be a list of dicts.
                return []
            except json.JSONDecodeError:
                return []
        elif isinstance(v, list):
            return v
        elif v is None:
            return []
        return [v] if v else []

class ForumResponse(ForumBase):
    id: int
    creator_id: int
    moderator_id: Optional[int] = None
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = 30
    summary_history: Optional[Union[List[Any], str]] = [] # Changed to List[Any] for flexibility
    participants: Optional[List[ForumParticipantResponse]] = []
    moderator: Optional[ModeratorResponse] = None # Include moderator info

    model_config = ConfigDict(from_attributes=True)

    @field_validator('summary_history', mode='before')
    @classmethod
    def parse_summary_history(cls, v: Any) -> List[Any]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                return []
            except json.JSONDecodeError:
                return []
        elif isinstance(v, list):
            return v
        elif v is None:
            return []
        return [v] if v else []

# --- Message Schemas ---
class MessageBase(BaseModel):
    speaker_name: str
    content: str
    thought: Optional[str] = None # Added thought field
    turn_count: int = 0

class MessageCreate(MessageBase):
    forum_id: int
    persona_id: Optional[int] = None
    moderator_id: Optional[int] = None

class MessageResponse(MessageBase):
    id: int
    forum_id: int
    persona_id: Optional[int]
    moderator_id: Optional[int] = None
    timestamp: datetime
    thought: Optional[str] = None # Ensure it's in response

    model_config = ConfigDict(from_attributes=True)

class TriggerAgentRequest(BaseModel):
    persona_id: Optional[int] = None

class TriggerModeratorRequest(BaseModel):
    action: str = "auto"  # auto, opening, summary, closing

class GodGenerateRequest(BaseModel):
    prompt: str
    n: int = 1

class ForumStartRequest(BaseModel):
    ablation_flags: Optional[Dict[str, bool]] = None

