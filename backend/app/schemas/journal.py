from datetime import datetime

from pydantic import BaseModel


class JournalCreate(BaseModel):
    title: str | None = None
    content: str
    submit: bool = False
    source_surface: str | None = None  # popup | sidepanel | fullpage
    mood_label: str | None = None


class JournalUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    submit: bool | None = None
    mood_label: str | None = None


class JournalResponse(BaseModel):
    id: str
    user_id: str
    title: str | None
    raw_text: str
    status: str
    word_count: int | None
    mood_label: str | None
    source_surface: str | None
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None

    model_config = {"from_attributes": True}


class JournalListResponse(BaseModel):
    journals: list[JournalResponse]
    total: int
