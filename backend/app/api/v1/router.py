from fastapi import APIRouter
from app.api.v1.endpoints import auth, integrations, playback, security, tenants, videos

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Organizations & Quotas"])
api_router.include_router(videos.router, prefix="/videos", tags=["Videos & Ingestion"])
api_router.include_router(playback.router, prefix="/playback", tags=["Playback & Security"])
api_router.include_router(security.router, prefix="/security", tags=["Security & Anti-Piracy Intelligence"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["BYOS Storage Integrations"])
