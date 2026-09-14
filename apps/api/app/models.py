from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


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


class NoteCreate(BaseModel):
    title: str = Field(min_length=1)
    memo: str = Field(min_length=1)
    email: EmailLink | None = None


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
