from datetime import date, datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class DashboardStatsResponse(BaseModel):
    pending: int
    replied: int
    escalated: int
    critical: int
    spam: int

class ThreadMessageResponse(BaseModel):
    id: UUID
    sender: str
    recipient: str | None
    subject: str | None
    body: str | None
    category: str | None
    urgency: str | None
    sentiment: str | None
    sentiment_score: float | None
    requires_human: bool
    status: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class ActionResponse(BaseModel):
    id: UUID
    email_id: UUID
    action_type: str
    proposed_content: str | None
    is_approved: bool
    approved_by: str | None
    approved_at: datetime | None
    execution_status: str | None
    rag_citations: list[dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ThreadHistoryResponse(BaseModel):
    thread_pk: UUID
    thread_id: str
    subject: str | None
    sender_email: str
    status: str
    priority: str
    last_updated_at: datetime
    emails: list[ThreadMessageResponse]
    actions: list[ActionResponse]

    model_config = ConfigDict(from_attributes=True)

class DraftEditRequest(BaseModel):
    proposed_content: str = Field(..., min_length=1)

class DraftApproveResponse(BaseModel):
    success: bool
    action_id: UUID
    email_id: UUID
    status: str

class CategoryBreakdownPoint(BaseModel):
    category: str
    count: int

class AuditLogResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    performed_by: str
    old_values: dict[str, Any]
    new_values: dict[str, Any]
    ip_address: str | None
    user_agent: str | None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class ContactProfileResponse(BaseModel):
    id: UUID
    email: str
    name: str | None
    company: str | None
    status: str
    account_value: float
    churn_risk_score: float
    created_at: datetime
    last_contact_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

class ContactStatusPatch(BaseModel):
    status: str

    model_config = ConfigDict(from_attributes=True)
