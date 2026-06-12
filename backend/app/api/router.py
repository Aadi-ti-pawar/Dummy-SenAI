from fastapi import APIRouter

from app.api.routes_health import router as health_router
from app.api.routes_ingest import router as ingest_router
from app.api.routes_intelligence import router as intelligence_router
from app.api.routes_status import router as status_router
from app.api.routes_crm import router as crm_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(ingest_router, tags=["ingestion"])
api_router.include_router(intelligence_router, tags=["intelligence"])
api_router.include_router(status_router, tags=["jobs"])
api_router.include_router(crm_router, tags=["crm"])

