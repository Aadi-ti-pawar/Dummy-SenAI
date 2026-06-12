from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Contact


def infer_name(email: str) -> str:
    local_part = email.split("@", 1)[0]
    return local_part.replace(".", " ").replace("_", " ").title()


def infer_company(email: str) -> str:
    domain = email.split("@", 1)[1]
    company = domain.split(".", 1)[0]
    return company.replace("-", " ").title()


def get_or_create_contact(db: Session, email: str, seen_at: datetime) -> Contact:
    contact = db.execute(select(Contact).where(Contact.email == email)).scalar_one_or_none()
    if contact is None:
        contact = Contact(
            email=email,
            name=infer_name(email),
            company=infer_company(email),
            status="Active",
            last_contact_at=seen_at,
        )
        db.add(contact)
        db.flush()
        return contact

    if contact.last_contact_at is None or seen_at > contact.last_contact_at:
        contact.last_contact_at = seen_at
    return contact
