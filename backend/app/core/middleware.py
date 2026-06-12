import time
import uuid

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import get_settings
from app.core.errors import error_payload


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        start = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["x-request-id"] = request_id
        response.headers["x-process-time-ms"] = f"{elapsed_ms:.2f}"
        return response


class PayloadSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content=error_payload(
                    "PAYLOAD_TOO_LARGE",
                    "Request body exceeds the configured payload size limit.",
                    {"max_bytes": self.max_bytes},
                ),
            )
        return await call_next(request)


def add_app_middleware(app: FastAPI) -> None:
    settings = get_settings()
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(PayloadSizeLimitMiddleware, max_bytes=settings.max_request_bytes)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
