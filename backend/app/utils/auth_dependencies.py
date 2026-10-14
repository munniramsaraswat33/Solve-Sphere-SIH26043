from collections.abc import Callable
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.errors import PyMongoError

from app.database.client import MongoDBNotConfigured
from app.models.auth import UserResponse, UserRole
from app.services.auth import get_user_by_id, is_token_revoked
from app.utils.security import AuthConfigurationError, decode_access_token

http_bearer = HTTPBearer(auto_error=False)


async def get_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_access_token(credentials.credentials)
    except AuthConfigurationError as error:
        raise HTTPException(status_code=503, detail="Authentication is not configured") from error
    except jwt.InvalidTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    try:
        if await is_token_revoked(str(claims["jti"])):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except MongoDBNotConfigured as error:
        raise HTTPException(status_code=503, detail="Database is not available") from error
    except PyMongoError as error:
        raise HTTPException(status_code=503, detail="Database is not available") from error

    return claims


async def get_current_user(claims: dict[str, Any] = Depends(get_token_claims)) -> UserResponse:
    try:
        document = await get_user_by_id(str(claims["sub"]))
    except MongoDBNotConfigured as error:
        raise HTTPException(status_code=503, detail="Database is not available") from error
    except PyMongoError as error:
        raise HTTPException(status_code=503, detail="Database is not available") from error

    if document is None or not document.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is unavailable",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserResponse(
        id=str(document["_id"]),
        name=document["name"],
        email=document["email"],
        role=document["role"],
        profile=document.get("profile", {}),
        created_at=document["created_at"],
    )


def require_roles(*allowed_roles: UserRole) -> Callable[..., Any]:
    async def role_dependency(
        current_user: UserResponse = Depends(get_current_user),
    ) -> UserResponse:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="You do not have permission to access this resource")
        return current_user

    return role_dependency