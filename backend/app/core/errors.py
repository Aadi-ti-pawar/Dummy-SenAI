import logging
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        error_code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details or {}


def error_payload(error_code: str, message: str, details: dict[str, Any] | list[Any] | None = None) -> dict[str, Any]:
    return {
        "error_code": error_code,
        "message": message,
        "details": details or {},
    }


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc.error_code, exc.message, exc.details),
    )


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_payload(
            "VALIDATION_ERROR",
            "Invalid request payload.",
            {"errors": exc.errors()},
        ),
    )


async def sqlalchemy_error_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database operation failed", exc_info=exc)

    details: dict[str, Any] = {}
    if get_settings().environment == "development":
        details = {
            "exception": exc.__class__.__name__,
            "message": str(getattr(exc, "orig", exc)),
        }

    if isinstance(exc, IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error_payload(
                "DATABASE_INTEGRITY_ERROR",
                "The request conflicts with an existing database record.",
                details,
            ),
        )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_payload(
            "DATABASE_ERROR",
            "Database operation failed.",
            details,
        ),
    )


async def unhandled_error_handler(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload(
            "INTERNAL_SERVER_ERROR",
            "Unexpected server error.",
        ),
    )
