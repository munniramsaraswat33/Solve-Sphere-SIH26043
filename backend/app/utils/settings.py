import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def get_cors_origins() -> list[str]:
    configured_origins = os.getenv("CORS_ORIGINS")
    if not configured_origins:
        return list(DEFAULT_CORS_ORIGINS)

    return [
        origin.strip().rstrip("/")
        for origin in configured_origins.split(",")
        if origin.strip()
    ]


def get_mongodb_uri() -> str | None:
    uri = os.getenv("MONGODB_URI", "").strip()
    return uri or None


def get_mongodb_database_name() -> str:
    return os.getenv("MONGODB_DATABASE", "solve_sphere").strip() or "solve_sphere"


def get_jwt_secret_key() -> str | None:
    secret_key = os.getenv("JWT_SECRET_KEY", "").strip()
    return secret_key or None


def get_google_client_id() -> str | None:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    return client_id or None


def get_jwt_access_token_minutes() -> int:
    try:
        lifetime = int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "30"))
    except ValueError as error:
        raise ValueError("JWT_ACCESS_TOKEN_MINUTES must be an integer") from error

    if lifetime < 1:
        raise ValueError("JWT_ACCESS_TOKEN_MINUTES must be at least 1")
    return lifetime