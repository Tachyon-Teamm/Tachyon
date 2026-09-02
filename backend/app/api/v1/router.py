from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.materials import router as materials_router
from app.api.v1.matching import router as matching_router
from app.api.v1.review import router as review_router
from app.api.v1.crosswalk import router as crosswalk_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.export import router as export_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(ingestion_router)
api_router.include_router(materials_router)
api_router.include_router(matching_router)
api_router.include_router(review_router)
api_router.include_router(crosswalk_router)
api_router.include_router(analytics_router)
api_router.include_router(export_router)
