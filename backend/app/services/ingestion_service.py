from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import AuditLog, Email, ProcessingJob
from app.schemas.email import EmailIngestRequest, IngestResponse
from app.services.contact_service import get_or_create_contact
from app.services.job_dispatcher import dispatch_processing_job
from app.services.normalization_service import normalize_email_text
from app.services.priority_service import HeuristicResult, score_email
from app.services.thread_service import get_or_create_thread


@dataclass(frozen=True)
class AuditContext:
    ip_address: str | None = None
    user_agent: str | None = None


class IngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ingest(
        self,
        *,
        payload: EmailIngestRequest,
        ip_address: str | None,
        user_agent: str | None,
    ) -> IngestResponse:
        duplicate = self._find_existing_email(payload.message_id)
        if duplicate is not None:
            job = self._find_latest_job(duplicate.id)
            metadata = duplicate.raw_entities.get("ingestion", {}) if duplicate.raw_entities else {}
            return IngestResponse(
                job_id=job.id if job else None,
                email_id=duplicate.id,
                message_id=duplicate.message_id,
                status=job.status if job else duplicate.status,
                duplicate=True,
                priority=duplicate.urgency or "Medium",
                priority_score=int(metadata.get("priority_score", 0)),
                warnings=list(metadata.get("warnings", [])),
            )

        try:
            result = self._ingest_new(payload, AuditContext(ip_address, user_agent))
        except IntegrityError:
            self.db.rollback()
            duplicate = self._find_existing_email(payload.message_id)
            if duplicate is None:
                raise
            job = self._find_latest_job(duplicate.id)
            metadata = duplicate.raw_entities.get("ingestion", {}) if duplicate.raw_entities else {}
            return IngestResponse(
                job_id=job.id if job else None,
                email_id=duplicate.id,
                message_id=duplicate.message_id,
                status=job.status if job else duplicate.status,
                duplicate=True,
                priority=duplicate.urgency or "Medium",
                priority_score=int(metadata.get("priority_score", 0)),
                warnings=list(metadata.get("warnings", [])),
            )

        dispatched, dispatch_error = dispatch_processing_job(result.job_id)
        if not dispatched:
            self._record_dispatch_failure(result.job_id, dispatch_error)
            result.status = "pending_dispatch"

        return result

    def _ingest_new(self, payload: EmailIngestRequest, audit_context: AuditContext) -> IngestResponse:
        timestamp = self._to_naive_utc(payload.timestamp)
        normalized = normalize_email_text(payload.subject, payload.body)
        heuristic = score_email(
            sender=str(payload.sender),
            subject=normalized.subject,
            body=normalized.processing_body,
        )

        contact = get_or_create_contact(self.db, str(payload.sender), timestamp)
        thread = get_or_create_thread(
            self.db,
            external_thread_id=payload.thread_id,
            sender_email=contact.email,
            subject=normalized.subject,
            timestamp=timestamp,
            priority=heuristic.urgency,
            escalated=heuristic.requires_human and heuristic.urgency == "Critical",
        )

        email = Email(
            thread_id=thread.id,
            message_id=payload.message_id,
            sender=str(payload.sender),
            recipient=str(payload.recipient) if payload.recipient else None,
            subject=normalized.subject,
            body=normalized.body,
            timestamp=timestamp,
            category=heuristic.category,
            sentiment="Neutral",
            sentiment_score=Decimal("0.00"),
            urgency=heuristic.urgency,
            confidence=Decimal(str(heuristic.confidence)),
            requires_human=heuristic.requires_human,
            status=self._initial_email_status(heuristic),
            raw_entities=self._raw_entities(payload, normalized, heuristic),
            is_internal=heuristic.is_internal,
            is_spam=heuristic.is_spam,
            is_security_alert=heuristic.is_security_alert,
            is_legal_threat=heuristic.is_legal_threat,
        )
        self.db.add(email)
        self.db.flush()

        job = ProcessingJob(
            email_id=email.id,
            job_type="post_ingestion_triage",
            status="Pending",
            progress_percentage=0,
            result_data={
                "requires_llm": not (heuristic.is_spam or heuristic.is_internal),
                "ingestion_priority": heuristic.urgency,
                "priority_score": heuristic.priority_score,
            },
        )
        self.db.add(job)
        self.db.flush()

        self._audit(
            entity_type="email",
            entity_id=email.id,
            action="INGESTED",
            new_values={
                "message_id": email.message_id,
                "thread_id": payload.thread_id,
                "category": email.category,
                "urgency": email.urgency,
                "requires_human": email.requires_human,
                "status": email.status,
            },
            audit_context=audit_context,
        )
        self._audit(
            entity_type="processing_job",
            entity_id=job.id,
            action="CREATED",
            new_values={"job_type": job.job_type, "status": job.status, "email_id": str(email.id)},
            audit_context=audit_context,
        )

        self.db.commit()

        return IngestResponse(
            job_id=job.id,
            email_id=email.id,
            message_id=email.message_id,
            status="queued",
            duplicate=False,
            priority=heuristic.urgency,
            priority_score=heuristic.priority_score,
            warnings=normalized.warnings,
        )

    def _find_existing_email(self, message_id: str) -> Email | None:
        return self.db.execute(select(Email).where(Email.message_id == message_id)).scalar_one_or_none()

    def _find_latest_job(self, email_id: UUID) -> ProcessingJob | None:
        return self.db.execute(
            select(ProcessingJob)
            .where(ProcessingJob.email_id == email_id)
            .order_by(desc(ProcessingJob.created_at))
            .limit(1)
        ).scalar_one_or_none()

    def _record_dispatch_failure(self, job_id: UUID, error: str | None) -> None:
        job = self.db.get(ProcessingJob, job_id)
        if job is None:
            return
        current = dict(job.result_data or {})
        current["dispatch"] = {"status": "not_dispatched", "error": error}
        job.result_data = current
        self.db.commit()

    def _audit(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        action: str,
        new_values: dict[str, Any],
        audit_context: AuditContext,
    ) -> None:
        self.db.add(
            AuditLog(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                performed_by="ingestion_pipeline",
                old_values={},
                new_values=new_values,
                ip_address=audit_context.ip_address,
                user_agent=audit_context.user_agent,
            )
        )

    @staticmethod
    def _raw_entities(payload: EmailIngestRequest, normalized: Any, heuristic: HeuristicResult) -> dict[str, Any]:
        entities = dict(heuristic.entities)
        entities["ingestion"] = {
            "external_thread_id": payload.thread_id,
            "priority_score": heuristic.priority_score,
            "priority_reasons": heuristic.reasons,
            "warnings": normalized.warnings,
            "original_body_length": normalized.original_body_length,
            "normalized_body_length": len(normalized.body),
            "processing_body": normalized.processing_body,
        }
        return entities

    @staticmethod
    def _initial_email_status(heuristic: HeuristicResult) -> str:
        if heuristic.is_spam or heuristic.is_internal:
            return "Ignored"
        if heuristic.requires_human and heuristic.urgency == "Critical":
            return "Escalated"
        return "Received"

    @staticmethod
    def _to_naive_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)
