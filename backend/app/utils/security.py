from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.utils.settings import get_jwt_access_token_minutes, get_jwt_secret_key

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "solve-sphere-api"
password_hasher = PasswordHash.recommended()


class AuthConfigurationError(RuntimeError):
    """Raised when required authentication configuration is missing or invalid."""


def validate_auth_configuration() -> tuple[str, int]:
    secret_key = get_jwt_secret_key()
    if secret_key is None or len(secret_key.encode("utf-8")) < 32:
        raise AuthConfigurationError("JWT_SECRET_KEY must contain at least 32 characters")

    try:
        lifetime_minutes = get_jwt_access_token_minutes()
    except ValueError as error:
        raise AuthConfigurationError(str(error)) from error

    return secret_key, lifetime_minutes * 60


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


def create_access_token(*, user_id: str, email: str, role: str) -> tuple[str, int]:
    secret_key, expires_in = validate_auth_configuration()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=expires_in)
    token = jwt.encode(
        {
            "sub": user_id,
            "email": email,
            "role": role,
            "iss": JWT_ISSUER,
            "iat": now,
            "exp": expires_at,
            "jti": str(uuid4()),
        },
        secret_key,
        algorithm=JWT_ALGORITHM,
    )
    return token, expires_in


def decode_access_token(token: str) -> dict[str, object]:
    secret_key, _ = validate_auth_configuration()
    return jwt.decode(
        token,
        secret_key,
        algorithms=[JWT_ALGORITHM],
        issuer=JWT_ISSUER,
        options={"require": ["sub", "iss", "iat", "exp", "jti"]},
    )