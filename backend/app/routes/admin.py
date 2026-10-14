from fastapi import APIRouter, Depends

from app.models.auth import UserResponse, UserRole
from app.utils.auth_dependencies import require_roles

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health")
async def admin_health(
    _: UserResponse = Depends(require_roles(UserRole.ADMIN)),
) -> dict[str, str]:
    return {"status": "ok", "access": "admin"}