from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.email import EmailIngestRequest, IngestResponse
from app.services.ingestion_service import IngestionService

router = APIRouter()


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_email(
    payload: EmailIngestRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> IngestResponse:
    service = IngestionService(db)
    return service.ingest(
        payload=payload,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
