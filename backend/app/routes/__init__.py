from fastapi import APIRouter

from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.matching import router as matching_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(health_router)
api_router.include_router(matching_router)