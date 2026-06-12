from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Email, ProcessingJob
from app.db.session import get_db
from app.schemas.jobs import JobStatusResponse

router = APIRouter()


@router.get("/status/{job_id}", response_model=JobStatusResponse)
def get_processing_status(job_id: UUID, db: Session = Depends(get_db)) -> JobStatusResponse:
    row = db.execute(
        select(ProcessingJob, Email)
        .join(Email, ProcessingJob.email_id == Email.id)
        .where(ProcessingJob.id == job_id)
    ).first()
    if row is None:
        raise AppError(
            status_code=404,
            error_code="JOB_NOT_FOUND",
            message="Processing job was not found.",
            details={"job_id": str(job_id)},
        )

    job, email = row
    return JobStatusResponse(
        job_id=job.id,
        email_id=email.id,
        message_id=email.message_id,
        job_type=job.job_type,
        status=job.status,
        progress_percentage=job.progress_percentage,
        error_message=job.error_message,
        result_data=job.result_data or {},
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )
