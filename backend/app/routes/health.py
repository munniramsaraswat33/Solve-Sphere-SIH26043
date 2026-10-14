from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from app.database.client import MongoDBNotConfigured, ping_database
from app.models.health import DatabaseHealthResponse, HealthResponse
from app.services.health import get_health_status

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return get_health_status()


@router.get(
    "/health/database",
    response_model=DatabaseHealthResponse,
    responses={503: {"model": DatabaseHealthResponse}},
)
async def database_health_check() -> DatabaseHealthResponse | JSONResponse:
    try:
        await ping_database()
    except MongoDBNotConfigured:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "not_configured"},
        )
    except PyMongoError:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "disconnected"},
        )

    return DatabaseHealthResponse(status="ok", database="connected")