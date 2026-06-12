from datetime import datetime
from uuid import UUID
from typing import Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Contact, Thread, Email, Action, AuditLog
from app.core.errors import AppError
from app.schemas.crm import (
    DashboardStatsResponse,
    ThreadHistoryResponse,
    ThreadMessageResponse,
    ActionResponse,
    DraftEditRequest,
    DraftApproveResponse,
    CategoryBreakdownPoint,
    AuditLogResponse,
    ContactProfileResponse,
    ContactStatusPatch,
)
from app.services.knowledge_service import KnowledgeService

router = APIRouter()

@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(db: Session = Depends(get_db)) -> DashboardStatsResponse:
    # 1. Pending (Received + Processing)
    pending_count = db.query(Email).filter(Email.status.in_(["Received", "Processing"])).count()
    # 2. Replied (Replied status)
    replied_count = db.query(Email).filter(Email.status == "Replied").count()
    # 3. Escalated (Escalated status)
    escalated_count = db.query(Email).filter(Email.status == "Escalated").count()
    # 4. Critical (urgency = 'Critical')
    critical_count = db.query(Email).filter(Email.urgency == "Critical").count()
    # 5. Spam (is_spam = True)
    spam_count = db.query(Email).filter(Email.is_spam == True).count()

    return DashboardStatsResponse(
        pending=pending_count,
        replied=replied_count,
        escalated=escalated_count,
        critical=critical_count,
        spam=spam_count,
    )

@router.get("/emails")
def list_emails(
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    emails = db.execute(
        select(Email).order_by(Email.timestamp.desc()).limit(limit)
    ).scalars().all()
    return [
        {
            "id": str(e.id),
            "thread_id": str(e.thread_id),
            "message_id": e.message_id,
            "sender": e.sender,
            "recipient": e.recipient,
            "subject": e.subject,
            "body": e.body,
            "timestamp": e.timestamp.isoformat(),
            "category": e.category or "Other",
            "sentiment": e.sentiment or "Neutral",
            "sentiment_score": float(e.sentiment_score) if e.sentiment_score is not None else 0.0,
            "urgency": e.urgency or "Medium",
            "confidence": float(e.confidence) if e.confidence is not None else 1.0,
            "requires_human": e.requires_human,
            "status": e.status,
            "is_internal": e.is_internal,
            "is_spam": e.is_spam,
            "is_security_alert": e.is_security_alert,
            "is_legal_threat": e.is_legal_threat,
        }
        for e in emails
    ]

@router.get("/threads/{contact_email}", response_model=list[ThreadHistoryResponse])
def get_threads_by_contact(contact_email: str, db: Session = Depends(get_db)) -> list[ThreadHistoryResponse]:
    # Verify contact exists
    contact = db.execute(select(Contact).where(Contact.email == contact_email)).scalar_one_or_none()
    if contact is None:
        raise AppError(
            status_code=404,
            error_code="CONTACT_NOT_FOUND",
            message="Contact was not found.",
            details={"email": contact_email},
        )

    # Fetch all threads for the contact
    threads = db.execute(
        select(Thread)
        .where(Thread.sender_email == contact_email)
        .order_by(Thread.last_updated_at.desc())
    ).scalars().all()

    result = []
    for t in threads:
        # Fetch emails for this thread
        emails = db.execute(
            select(Email)
            .where(Email.thread_id == t.id)
            .order_by(Email.timestamp.asc())
        ).scalars().all()

        # Fetch actions for this thread
        actions = db.execute(
            select(Action)
            .where(Action.thread_id == t.id)
            .order_by(Action.created_at.asc())
        ).scalars().all()

        # Build list of ThreadMessageResponse
        email_responses = [
            ThreadMessageResponse(
                id=e.id,
                sender=e.sender,
                recipient=e.recipient,
                subject=e.subject,
                body=e.body,
                category=e.category,
                urgency=e.urgency,
                sentiment=e.sentiment,
                sentiment_score=float(e.sentiment_score) if e.sentiment_score is not None else 0.0,
                requires_human=e.requires_human,
                status=e.status,
                timestamp=e.timestamp,
            )
            for e in emails
        ]

        # Build list of ActionResponse
        action_responses = [
            ActionResponse(
                id=a.id,
                email_id=a.email_id,
                action_type=a.action_type,
                proposed_content=a.proposed_content,
                is_approved=a.is_approved,
                approved_by=a.approved_by,
                approved_at=a.approved_at,
                execution_status=a.execution_status,
                rag_citations=a.rag_citations or [],
                created_at=a.created_at,
            )
            for a in actions
        ]

        result.append(
            ThreadHistoryResponse(
                thread_pk=t.id,
                thread_id=t.thread_id,
                subject=t.subject,
                sender_email=t.sender_email,
                status=t.status,
                priority=t.priority,
                last_updated_at=t.last_updated_at,
                emails=email_responses,
                actions=action_responses,
            )
        )

    return result

@router.post("/respond/{email_id}", response_model=ActionResponse)
def respond_email(email_id: UUID, db: Session = Depends(get_db)) -> ActionResponse:
    email = db.get(Email, email_id)
    if email is None:
        raise AppError(
            status_code=404,
            error_code="EMAIL_NOT_FOUND",
            message="Email was not found.",
            details={"email_id": str(email_id)},
        )

    # Create manual response action entry
    action = Action(
        email_id=email.id,
        thread_id=email.thread_id,
        agent_reasoning_log=[{"step": 1, "thought": "Manual response recorded.", "action": None, "observation": None}],
        agent_model="human-operator",
        reasoning_trace="Response processed by operator.",
        action_type="Auto-Reply",
        proposed_content="Response sent by human agent.",
        is_approved=True,
        approved_by="human-operator",
        approved_at=datetime.utcnow(),
        executed_at=datetime.utcnow(),
        execution_status="Executed",
        rag_citations=[],
    )
    db.add(action)

    # Update email status
    email.status = "Replied"

    # Log to audit trail
    db.add(
        AuditLog(
            entity_type="email",
            entity_id=email.id,
            action="EMAIL_MANUAL_RESPONDED",
            performed_by="human-operator",
            old_values={"status": "Received"},
            new_values={"status": "Replied"},
        )
    )
    db.commit()
    db.refresh(action)

    return ActionResponse.model_validate(action)

@router.patch("/drafts/{id}", response_model=ActionResponse)
def edit_draft(id: UUID, payload: DraftEditRequest, db: Session = Depends(get_db)) -> ActionResponse:
    action = db.get(Action, id)
    if action is None:
        raise AppError(
            status_code=404,
            error_code="DRAFT_NOT_FOUND",
            message="Draft action was not found.",
            details={"action_id": str(id)},
        )

    action.proposed_content = payload.proposed_content
    db.add(
        AuditLog(
            entity_type="action",
            entity_id=action.id,
            action="AGENT_DRAFT_EDITED",
            performed_by="operator",
            old_values={"proposed_content": action.proposed_content},
            new_values={"proposed_content": payload.proposed_content},
        )
    )
    db.commit()
    db.refresh(action)

    return ActionResponse.model_validate(action)

@router.post("/drafts/{id}/approve", response_model=DraftApproveResponse)
def approve_draft(id: UUID, db: Session = Depends(get_db)) -> DraftApproveResponse:
    action = db.get(Action, id)
    if action is None:
        raise AppError(
            status_code=404,
            error_code="DRAFT_NOT_FOUND",
            message="Draft action was not found.",
            details={"action_id": str(id)},
        )

    # Update Action status
    action.is_approved = True
    action.approved_by = "admin"
    action.approved_at = datetime.utcnow()
    action.executed_at = datetime.utcnow()
    action.execution_status = "Executed"

    # Update corresponding email status
    email = db.get(Email, action.email_id)
    if email:
        email.status = "Replied"

    db.add(
        AuditLog(
            entity_type="action",
            entity_id=action.id,
            action="AGENT_DRAFT_APPROVED",
            performed_by="admin",
            old_values={"is_approved": False, "execution_status": "Pending"},
            new_values={"is_approved": True, "execution_status": "Executed"},
        )
    )
    db.commit()

    return DraftApproveResponse(
        success=True,
        action_id=action.id,
        email_id=action.email_id,
        status="Executed",
    )

@router.get("/analytics/category-breakdown", response_model=list[CategoryBreakdownPoint])
def get_category_breakdown(
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CategoryBreakdownPoint]:
    query = select(Email.category, func.count(Email.id).label("count"))
    
    filters = []
    if start_date:
        filters.append(Email.timestamp >= start_date)
    if end_date:
        filters.append(Email.timestamp <= end_date)

    if filters:
        query = query.where(and_(*filters))

    query = query.group_by(Email.category)
    rows = db.execute(query).all()

    return [
        CategoryBreakdownPoint(category=row[0] or "Unknown", count=row[1])
        for row in rows
    ]

@router.get("/rag/search")
def rag_search_debug(
    query: str,
    limit: int = Query(default=3, ge=1, le=10),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    service = KnowledgeService(db)
    chunks = service.search(query, limit)
    return {
        "query": query,
        "results": chunks,
        "citations": KnowledgeService.citations(chunks),
    }

@router.get("/audit/{entity_type}/{entity_id}", response_model=list[AuditLogResponse])
def get_audit_trail(
    entity_type: str,
    entity_id: UUID,
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    logs = db.execute(
        select(AuditLog)
        .where(AuditLog.entity_type == entity_type)
        .where(AuditLog.entity_id == entity_id)
        .order_by(AuditLog.timestamp.desc())
    ).scalars().all()

    return [AuditLogResponse.model_validate(log) for log in logs]

@router.get("/contacts/{email}", response_model=ContactProfileResponse)
def get_contact_profile(email: str, db: Session = Depends(get_db)) -> ContactProfileResponse:
    contact = db.execute(select(Contact).where(Contact.email == email)).scalar_one_or_none()
    if contact is None:
        raise AppError(
            status_code=404,
            error_code="CONTACT_NOT_FOUND",
            message="Contact was not found.",
            details={"email": email},
        )
    return ContactProfileResponse.model_validate(contact)

@router.patch("/contacts/{email}/status", response_model=ContactProfileResponse)
def update_contact_status(
    email: str,
    payload: ContactStatusPatch,
    db: Session = Depends(get_db),
) -> ContactProfileResponse:
    contact = db.execute(select(Contact).where(Contact.email == email)).scalar_one_or_none()
    if contact is None:
        raise AppError(
            status_code=404,
            error_code="CONTACT_NOT_FOUND",
            message="Contact was not found.",
            details={"email": email},
        )

    contact.status = payload.status
    db.add(
        AuditLog(
            entity_type="contact",
            entity_id=contact.id,
            action="CONTACT_STATUS_UPDATED",
            performed_by="operator",
            old_values={"status": contact.status},
            new_values={"status": payload.status},
        )
    )
    db.commit()
    db.refresh(contact)

    return ContactProfileResponse.model_validate(contact)
