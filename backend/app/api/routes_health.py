from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import error_payload
from app.db.session import get_db

router = APIRouter()

REQUIRED_TABLES = (
    "contacts",
    "threads",
    "emails",
    "processing_jobs",
    "audit_log",
)


def _database_details() -> dict[str, object]:
    url = make_url(get_settings().database_url)
    return {
        "driver": url.drivername,
        "host": url.host,
        "port": url.port,
        "database": url.database,
    }


@router.get("/health/live")
def liveness_check() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@router.get("/health", response_model=None)
@router.get("/health/ready", response_model=None)
def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        rows = db.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = ANY(:table_names)
                """
            ),
            {"table_names": list(REQUIRED_TABLES)},
        ).scalars()
        found_tables = set(rows)
        missing_tables = sorted(set(REQUIRED_TABLES) - found_tables)
        if missing_tables:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=error_payload(
                    "DATABASE_SCHEMA_NOT_READY",
                    "PostgreSQL is reachable, but required tables are missing.",
                    {
                        "database": _database_details(),
                        "missing_tables": missing_tables,
                        "hint": "Apply backend/database_schema.sql to this database before running ingestion.",
                    },
                ),
            )
    except SQLAlchemyError as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_payload(
                "DATABASE_UNAVAILABLE",
                "API is running, but PostgreSQL is not reachable.",
                {
                    "database": _database_details(),
                    "exception": exc.__class__.__name__,
                    "hint": "Start PostgreSQL and apply backend/database_schema.sql, or update DATABASE_URL in backend/.env.",
                },
            ),
        )
    return {"status": "ok", "database": "ok"}
