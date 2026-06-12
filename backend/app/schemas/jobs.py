from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class JobStatusResponse(BaseModel):
    job_id: UUID
    email_id: UUID
    message_id: str
    job_type: str
    status: str
    progress_percentage: int
    error_message: str | None
    result_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
