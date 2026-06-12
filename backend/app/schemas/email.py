from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class EmailIngestRequest(BaseModel):
    message_id: str = Field(..., min_length=1, max_length=255)
    sender: EmailStr
    recipient: EmailStr | None = None
    subject: str = Field(..., max_length=500)
    body: str = Field(...)
    timestamp: datetime
    thread_id: str = Field(..., min_length=1, max_length=255)

    @field_validator("message_id", "thread_id", mode="before")
    @classmethod
    def strip_required_identifiers(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("subject", "body", mode="before")
    @classmethod
    def coerce_text_fields(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value)


class IngestResponse(BaseModel):
    job_id: UUID | None
    email_id: UUID
    message_id: str
    status: str
    duplicate: bool
    priority: str
    priority_score: int
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
