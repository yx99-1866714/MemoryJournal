from datetime import datetime
from typing import Any

from pydantic import BaseModel


class FeedbackResponse(BaseModel):
    id: str
    journal_id: str
    agent_role: str
    response_text: str
    response_json: dict[str, Any] | None = None
    model_name: str | None = None
    created_at: datetime


class FeedbackListResponse(BaseModel):
    feedback: list[FeedbackResponse]


class ProcessingStatusResponse(BaseModel):
    journal_id: str
    status: str  # draft | submitted | processing | processed | failed
    evermemos_status: str | None = None
    has_feedback: bool = False
