import logging
from uuid import UUID

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def dispatch_processing_job(job_id: UUID) -> tuple[bool, str | None]:
    settings = get_settings()
    if not settings.enable_celery_dispatch:
        return False, "Celery dispatch is disabled by configuration."

    try:
        from app.workers.tasks import process_ingested_email

        process_ingested_email.delay(str(job_id))
    except Exception as exc:  # Celery or Redis should not make ingestion lose data.
        logger.warning("Failed to dispatch processing job %s: %s", job_id, exc)
        return False, str(exc)

    return True, None
