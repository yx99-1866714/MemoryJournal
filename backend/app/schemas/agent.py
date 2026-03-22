import uuid
from datetime import datetime

from pydantic import BaseModel


# ---- Agent ----

class AgentResponse(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    purpose: str
    tone: str
    is_builtin: bool
    is_active: bool

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]


# ---- Thread & Messages ----

class AgentRespondRequest(BaseModel):
    message: str
    journal_id: uuid.UUID | None = None
    tz_offset_minutes: int | None = None  # e.g. -420 for PDT (UTC-7)


class MessageResponse(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ThreadResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    journal_id: uuid.UUID | None
    messages: list[MessageResponse]
    created_at: datetime

    model_config = {"from_attributes": True}
