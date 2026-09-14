from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ReviewStatus(str, Enum):
    ai_generated = "ai_generated"
    human_reviewed = "human_reviewed"


class EmailLink(BaseModel):
    provider: Literal["gmail"] = "gmail"
    provider_message_id: str | None = None
    subject: str = ""
    sender: str = ""
    received_at: datetime | None = None
    snippet: str = ""


class GmailConnectionStatus(BaseModel):
    configured: bool
    connected: bool
    pending: bool
    error: str | None = None


class GmailAuthorization(BaseModel):
    authorization_url: str


class GmailMessagePage(BaseModel):
    messages: list[EmailLink]
    next_page_token: str | None = None


class GmailMessageDetail(BaseModel):
    email: EmailLink
    truncated: bool
    snippet_only: bool


class GmailDisconnectResult(BaseModel):
    connected: Literal[False] = False
    revoked: bool


class ExtractRequest(BaseModel):
    memo: str = Field(min_length=1)
    email: EmailLink | None = None

    @field_validator("memo")
    @classmethod
    def nonblank_memo(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class ExtractedContext(BaseModel):
    summary: str
    event_datetime: str | None = None
    location: str | None = None
    deadline: str | None = None
    people: list[str] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    ai_model: str = "local-deterministic-extractor"
    review_status: ReviewStatus = ReviewStatus.ai_generated


class NoteCreate(ExtractRequest):
    title: str = Field(min_length=1)

    @field_validator("title")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class WorkNote(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    memo: str
    email: EmailLink | None = None
    context: ExtractedContext
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorEnvelope(BaseModel):
    error: dict


class NoteBackup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    exported_at: datetime
    notes: list[WorkNote] = Field(max_length=1000)

    @model_validator(mode="after")
    def validate_notes(self):
        ids = set()
        for note in self.notes:
            if str(UUID(note.id)) != note.id:
                raise ValueError("backup IDs must be canonical UUIDs")
            if note.id in ids or not note.title.strip() or not note.memo.strip():
                raise ValueError("invalid backup note")
            if note.created_at.tzinfo is None or note.updated_at.tzinfo is None:
                raise ValueError("backup timestamps require timezones")
            if note.updated_at < note.created_at:
                raise ValueError("invalid backup timestamps")
            note.created_at = note.created_at.astimezone(timezone.utc)
            note.updated_at = note.updated_at.astimezone(timezone.utc)
            ids.add(note.id)
        return self


class RestoreResult(BaseModel):
    restored: int
    skipped: int
