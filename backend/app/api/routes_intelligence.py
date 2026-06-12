from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import Action, Email
from app.db.session import get_db
from app.schemas.classification import AgentDecisionResponse, ClassificationResponse, SentimentTrendPoint
from app.services.agent_service import TriageAgentService
from app.services.classification_service import ClassificationService

router = APIRouter()


@router.post("/classify/{email_id}", response_model=ClassificationResponse)
def classify_email(email_id: UUID, db: Session = Depends(get_db)) -> ClassificationResponse:
    return ClassificationService(db).classify_email(email_id)


@router.post("/agent/run/{email_id}", response_model=AgentDecisionResponse)
def run_agent(email_id: UUID, db: Session = Depends(get_db)) -> AgentDecisionResponse:
    return TriageAgentService(db).run(email_id, dry_run=False)


@router.post("/agent/dry-run/{email_id}", response_model=AgentDecisionResponse)
def dry_run_agent(email_id: UUID, db: Session = Depends(get_db)) -> AgentDecisionResponse:
    return TriageAgentService(db).run(email_id, dry_run=True)


@router.get("/analytics/sentiment-trend", response_model=list[SentimentTrendPoint])
def get_sentiment_trend(
    sender_email: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> list[SentimentTrendPoint]:
    return ClassificationService(db).get_sentiment_trend(sender_email, days)


@router.get("/results/actions")
def list_agent_actions(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    rows = db.execute(
        select(Action, Email)
        .join(Email, Action.email_id == Email.id)
        .order_by(desc(Action.created_at))
        .limit(limit)
    ).all()
    return [
        {
            "action_id": action.id,
            "email_id": email.id,
            "message_id": email.message_id,
            "sender": email.sender,
            "subject": email.subject,
            "category": email.category,
            "urgency": email.urgency,
            "sentiment": email.sentiment,
            "requires_human": email.requires_human,
            "action_type": action.action_type,
            "execution_status": action.execution_status,
            "proposed_content": action.proposed_content,
            "rag_citations": action.rag_citations,
            "created_at": action.created_at,
        }
        for action, email in rows
    ]


@router.get("/intelligence/reputation")
def get_reputation(
    entity: str = Query(default="SenAI"),
    db: Session = Depends(get_db),
):
    from app.services.intelligence_service import ReputationScraperService
    service = ReputationScraperService(db)
    return service.get_reputation(entity)

