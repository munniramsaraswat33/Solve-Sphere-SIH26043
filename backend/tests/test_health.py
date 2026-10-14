from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from pymongo.errors import ServerSelectionTimeoutError

from app.database.collections import COLLECTION_INDEXES
from app.main import app
from app.routes import health as health_route



def test_health_endpoint_returns_api_status() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "solve-sphere-api"}


def test_health_endpoint_allows_vite_frontend_origin() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_database_health_reports_missing_configuration(monkeypatch) -> None:
    monkeypatch.delenv("MONGODB_URI", raising=False)

    with TestClient(app) as client:
        response = client.get("/api/health/database")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "not_configured"}


def test_database_health_reports_connected_database(monkeypatch) -> None:
    monkeypatch.delenv("MONGODB_URI", raising=False)
    monkeypatch.setattr(health_route, "ping_database", AsyncMock())

    with TestClient(app) as client:
        response = client.get("/api/health/database")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_database_health_reports_disconnected_database(monkeypatch) -> None:
    monkeypatch.delenv("MONGODB_URI", raising=False)
    monkeypatch.setattr(
        health_route,
        "ping_database",
        AsyncMock(side_effect=ServerSelectionTimeoutError("MongoDB is unavailable")),
    )

    with TestClient(app) as client:
        response = client.get("/api/health/database")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "disconnected"}


def test_database_structure_defines_all_requested_collections() -> None:
    assert set(COLLECTION_INDEXES) == {
        "users",
        "challenges",
        "teams",
        "solutions",
        "reviews",
        "tasks",
        "notifications",
        "revoked_tokens",
    }
    assert all(COLLECTION_INDEXES.values())