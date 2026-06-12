from datetime import datetime
from uuid import UUID

from app.db.models import ProcessingJob
from app.db.session import SessionLocal
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.process_ingested_email")
def process_ingested_email(job_id: str) -> dict[str, str]:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, UUID(job_id))
        if job is None:
            return {"status": "missing", "job_id": job_id}

        job.status = "Processing"
        job.progress_percentage = 10
        job.started_at = datetime.utcnow()
        db.commit()

        # Later milestones call heuristic refinement, RAG, and the LangGraph agent here.
        job.status = "Completed"
        job.progress_percentage = 100
        job.completed_at = datetime.utcnow()
        job.result_data = {
            **(job.result_data or {}),
            "worker": "post_ingestion_stub",
            "next_stage": "llm_classification",
        }
        db.commit()
        return {"status": "completed", "job_id": job_id}
    except Exception as exc:
        db.rollback()
        job = db.get(ProcessingJob, UUID(job_id))
        if job is not None:
            job.status = "Failed"
            job.error_message = str(exc)
            job.completed_at = datetime.utcnow()
            db.commit()
        raise
    finally:
        db.close()
