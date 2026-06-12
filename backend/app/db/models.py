from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def uuid_pk() -> Mapped[UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)


class Contact(Base):
    __tablename__ = "contacts"

    id = uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="Active")
    account_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    churn_risk_score: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.00"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    threads: Mapped[list["Thread"]] = relationship(back_populates="contact")


class Thread(Base):
    __tablename__ = "threads"

    id = uuid_pk()
    thread_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    subject: Mapped[str | None] = mapped_column(String(500))
    sender_email: Mapped[str] = mapped_column(ForeignKey("contacts.email"), nullable=False, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(50), default="Open")
    assigned_to: Mapped[str | None] = mapped_column(String(255))
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contact: Mapped[Contact] = relationship(back_populates="threads")
    emails: Mapped[list["Email"]] = relationship(back_populates="thread")


class Email(Base):
    __tablename__ = "emails"

    id = uuid_pk()
    thread_id: Mapped[UUID] = mapped_column(ForeignKey("threads.id"), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    recipient: Mapped[str | None] = mapped_column(String(255))
    subject: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    category: Mapped[str | None] = mapped_column(String(50), index=True)
    sentiment: Mapped[str | None] = mapped_column(String(20))
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), index=True)
    urgency: Mapped[str | None] = mapped_column(String(20), index=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))

    requires_human: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="Received", index=True)
    raw_entities: Mapped[dict] = mapped_column(JSONB, default=dict)

    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    is_spam: Mapped[bool] = mapped_column(Boolean, default=False)
    is_security_alert: Mapped[bool] = mapped_column(Boolean, default=False)
    is_legal_threat: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    thread: Mapped[Thread] = relationship(back_populates="emails")
    jobs: Mapped[list["ProcessingJob"]] = relationship(back_populates="email")
    actions: Mapped[list["Action"]] = relationship(back_populates="email")


class Action(Base):
    __tablename__ = "actions"

    id = uuid_pk()
    email_id: Mapped[UUID] = mapped_column(ForeignKey("emails.id"), nullable=False, index=True)
    thread_id: Mapped[UUID] = mapped_column(ForeignKey("threads.id"), nullable=False, index=True)
    agent_reasoning_log: Mapped[dict | list] = mapped_column(JSONB, default=dict)
    agent_model: Mapped[str | None] = mapped_column(String(50))
    reasoning_trace: Mapped[str | None] = mapped_column(Text)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    proposed_content: Mapped[str | None] = mapped_column(Text)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(255))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime)
    execution_status: Mapped[str | None] = mapped_column(String(50), default="Pending", index=True)
    rag_citations: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    email: Mapped[Email] = relationship(back_populates="actions")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = uuid_pk()
    email_id: Mapped[UUID] = mapped_column(ForeignKey("emails.id"), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Pending", index=True)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    result_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    email: Mapped[Email] = relationship(back_populates="jobs")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = uuid_pk()
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    performed_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    old_values: Mapped[dict] = mapped_column(JSONB, default=dict)
    new_values: Mapped[dict] = mapped_column(JSONB, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class SentimentTrend(Base):
    __tablename__ = "sentiment_trend"

    id = uuid_pk()
    sender_email: Mapped[str] = mapped_column(ForeignKey("contacts.email"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    avg_sentiment: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    min_sentiment: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    max_sentiment: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    email_count: Mapped[int] = mapped_column(Integer, default=0)
    moving_avg_7d: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    moving_avg_30d: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WebIntelligenceCache(Base):
    __tablename__ = "web_intelligence_cache"

    id = uuid_pk()
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    target_entity: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_type: Mapped[str | None] = mapped_column(String(50), index=True)
    scraped_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    http_status: Mapped[int | None] = mapped_column(Integer)
    scrape_success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
