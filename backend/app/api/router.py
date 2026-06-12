from fastapi import APIRouter

from app.api.routes_health import router as health_router
from app.api.routes_ingest import router as ingest_router
from app.api.routes_status import router as status_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(ingest_router, tags=["ingestion"])
api_router.include_router(status_router, tags=["jobs"])
