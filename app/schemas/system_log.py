from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class SystemLogBase(BaseModel):
    level: str
    source: Optional[str] = None
    content: str

class SystemLogCreate(SystemLogBase):
    forum_id: int
    timestamp: Optional[datetime] = None

class SystemLogResponse(SystemLogBase):
    id: int
    forum_id: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)
