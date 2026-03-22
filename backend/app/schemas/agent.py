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
    unread_count: int = 0

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]


class AgentCreateRequest(BaseModel):
    name: str
    purpose: str
    tone: str
    system_prompt: str | None = None


class AgentUpdateRequest(BaseModel):
    name: str | None = None
    purpose: str | None = None
    tone: str | None = None
    system_prompt: str | None = None
    is_active: bool | None = None


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
