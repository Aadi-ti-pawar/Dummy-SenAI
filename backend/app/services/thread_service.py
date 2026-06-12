from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Thread
from app.services.priority_service import higher_priority


def get_or_create_thread(
    db: Session,
    *,
    external_thread_id: str,
    sender_email: str,
    subject: str,
    timestamp: datetime,
    priority: str,
    escalated: bool,
) -> Thread:
    thread = db.execute(select(Thread).where(Thread.thread_id == external_thread_id)).scalar_one_or_none()
    if thread is None:
        thread = Thread(
            thread_id=external_thread_id,
            sender_email=sender_email,
            subject=subject,
            first_seen_at=timestamp,
            last_updated_at=timestamp,
            status="Escalated" if escalated else "Open",
            priority=priority,
        )
        db.add(thread)
        db.flush()
        return thread

    if timestamp < thread.first_seen_at:
        thread.first_seen_at = timestamp
    if timestamp > thread.last_updated_at:
        thread.last_updated_at = timestamp
    thread.priority = higher_priority(thread.priority, priority)
    if escalated:
        thread.status = "Escalated"
    if not thread.subject and subject:
        thread.subject = subject
    return thread
