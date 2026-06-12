from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    validation_error_handler,
    sqlalchemy_error_handler,
    unhandled_error_handler,
)
from app.core.middleware import add_app_middleware


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )

    add_app_middleware(app)

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.app_name,
            "docs": "/docs",
            "api": settings.api_prefix,
            "readiness": f"{settings.api_prefix}/health",
        }

    @app.get("/health", include_in_schema=False)
    def root_liveness() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "api",
            "database": "not_checked",
            "readiness": f"{settings.api_prefix}/health",
        }

    app.include_router(api_router, prefix=settings.api_prefix)

    return app


app = create_app()
