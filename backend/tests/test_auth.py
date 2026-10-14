from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import anyio
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.models.auth import UserResponse, UserRole
from app.routes import auth as auth_routes
from app.services import auth as auth_service
from app.utils import auth_dependencies
from app.utils.security import create_access_token, hash_password, verify_password


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def sample_user(role: str = "student") -> dict:
    return {
        "_id": ObjectId("68f2d4800955a4f027ef02aa"),
        "name": "Sam Student",
        "email": "sam@example.com",
        "role": role,
        "profile": {"college": "Example University"},
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "password_hash": hash_password("correct horse battery staple"),
    }


@pytest.mark.parametrize(
    ("role", "profile"),
    [
        ("student", {"college": "Example University", "branch": "Computer Science", "year": 2}),
        ("problem-owner", {"organization_name": "City Office", "organization_type": "government"}),
        ("mentor", {"organization_name": "Example Tech", "expertise": "Data systems"}),
        ("faculty", {"university": "Example University", "department": "Engineering"}),
    ],
)
def test_role_registration_returns_jwt_without_password_hash(role, profile, monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-secret-key-that-is-at-least-32-bytes")
    created_user = sample_user(role.replace("-", "_") if role != "faculty" else "faculty")
    create_user_mock = AsyncMock(return_value=created_user)
    monkeypatch.setattr(auth_routes, "create_user", create_user_mock)
    payload = {
        "name": "Sam Student",
        "email": "sam@example.com",
        "password": "correct horse battery staple",
        "profile": profile,
    }

    with TestClient(app) as client:
        response = client.post(f"/api/auth/register/{role}", json=payload)

    assert response.status_code == 201
    result = response.json()
    assert result["user"]["role"] == created_user["role"]
    assert "password_hash" not in result["user"]
    assert create_user_mock.await_args.args[1].value == created_user["role"]
    assert result["access_token"]


def test_login_returns_bearer_token(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-secret-key-that-is-at-least-32-bytes")
    monkeypatch.setattr(auth_routes, "authenticate_user", AsyncMock(return_value=sample_user()))

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"email": "sam@example.com", "password": "correct horse battery staple"},
        )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["user"]["role"] == "student"


def test_registration_requires_only_email_and_password(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-secret-key-that-is-at-least-32-bytes")
    create_user_mock = AsyncMock(return_value=sample_user())
    monkeypatch.setattr(auth_routes, "create_user", create_user_mock)

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/register/student",
            json={"email": "sam@example.com", "password": "correct horse battery staple"},
        )

    assert response.status_code == 201
    registration = create_user_mock.await_args.args[0]
    assert registration.name is None
    assert registration.profile.model_dump(exclude_unset=True) == {}


def test_google_login_returns_bearer_token(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-secret-key-that-is-at-least-32-bytes")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id.apps.googleusercontent.com")
    authenticate_google_mock = AsyncMock(return_value=sample_user())
    monkeypatch.setattr(auth_routes, "authenticate_google_user", authenticate_google_mock)

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/google",
            json={"id_token": "verified-google-token", "role": "student"},
        )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["user"]["role"] == "student"
    assert authenticate_google_mock.await_args.args[1] == UserRole.STUDENT


def test_google_login_reports_missing_server_configuration(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with TestClient(app) as client:
        response = client.post("/api/auth/google", json={"id_token": "test-token"})

    assert response.status_code == 503
    assert "GOOGLE_CLIENT_ID" in response.json()["detail"]


def test_google_login_reports_verifier_dependency_failure(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-secret-key-that-is-at-least-32-bytes")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id.apps.googleusercontent.com")
    authenticate_google_mock = AsyncMock(
        side_effect=auth_service.GoogleIdentityProviderError(
            "Google identity verification requires the backend cryptography dependency."
        )
    )
    monkeypatch.setattr(auth_routes, "authenticate_google_user", authenticate_google_mock)

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/google",
            json={"id_token": "verified-google-token", "role": "student"},
        )

    assert response.status_code == 503
    assert "cryptography dependency" in response.json()["detail"]


def test_google_verifier_uses_configured_client_as_audience(monkeypatch) -> None:
    class FakeJwksClient:
        def get_signing_key_from_jwt(self, token):
            assert token == "google-id-token"
            return SimpleNamespace(key="google-public-signing-key")

    decode_calls = {}

    def decode_token(token, key, **kwargs):
        decode_calls.update(token=token, key=key, **kwargs)
        return {
            "email": "sam@example.com",
            "email_verified": True,
            "sub": "google-user",
        }

    monkeypatch.setattr(auth_service, "GOOGLE_JWKS_CLIENT", FakeJwksClient())
    monkeypatch.setattr(auth_service.jwt, "decode", decode_token)

    claims = anyio.run(
        auth_service._verify_google_id_token,
        "google-id-token",
        "client-id.apps.googleusercontent.com",
    )

    assert claims["email"] == "sam@example.com"
    assert decode_calls["audience"] == "client-id.apps.googleusercontent.com"
    assert decode_calls["algorithms"] == ["RS256"]
    assert decode_calls["options"]["require"] == [
        "aud",
        "email",
        "email_verified",
        "exp",
        "iat",
        "iss",
        "sub",
    ]


def test_google_verifier_rejects_mismatched_audience(monkeypatch) -> None:
    class FakeJwksClient:
        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key="google-public-signing-key")

    def decode_token(_token, _key, **kwargs):
        assert kwargs["audience"] == "client-id.apps.googleusercontent.com"
        raise auth_service.jwt.InvalidAudienceError("Audience doesn't match")

    monkeypatch.setattr(auth_service, "GOOGLE_JWKS_CLIENT", FakeJwksClient())
    monkeypatch.setattr(auth_service.jwt, "decode", decode_token)

    with pytest.raises(auth_service.InvalidGoogleTokenError):
        anyio.run(
            auth_service._verify_google_id_token,
            "google-id-token",
            "client-id.apps.googleusercontent.com",
        )


def test_google_verifier_reports_missing_cryptography_dependency(monkeypatch) -> None:
    def decode_token(_token, _client_id):
        raise auth_service.jwt.exceptions.MissingCryptographyError(
            "RS256 requires 'cryptography' to be installed."
        )

    monkeypatch.setattr(auth_service, "_decode_google_id_token", decode_token)

    with pytest.raises(auth_service.GoogleIdentityProviderError, match="cryptography dependency"):
        anyio.run(
            auth_service._verify_google_id_token,
            "google-id-token",
            "client-id.apps.googleusercontent.com",
        )


def test_google_login_creates_new_user_after_claim_validation(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id.apps.googleusercontent.com")
    claims = {
        "sub": "google-subject",
        "email": "sam@example.com",
        "email_verified": True,
        "name": "Sam Student",
    }
    monkeypatch.setattr(auth_service, "_verify_google_id_token", AsyncMock(return_value=claims))
    users = SimpleNamespace(
        find_one=AsyncMock(return_value=None),
        insert_one=AsyncMock(return_value=SimpleNamespace(inserted_id=ObjectId())),
    )
    monkeypatch.setattr(auth_service, "get_database", lambda: {"users": users})

    created_user = anyio.run(
        auth_service.authenticate_google_user,
        "verified-id-token",
        UserRole.STUDENT,
    )

    assert created_user["email"] == "sam@example.com"
    assert created_user["google_sub"] == "google-subject"
    users.insert_one.assert_awaited_once()


def test_google_login_reuses_existing_google_account(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id.apps.googleusercontent.com")
    monkeypatch.setattr(
        auth_service,
        "_verify_google_id_token",
        AsyncMock(return_value={
            "sub": "google-subject",
            "email": "sam@example.com",
            "email_verified": True,
        }),
    )
    existing_user = sample_user()
    existing_user["google_sub"] = "google-subject"
    users = SimpleNamespace(
        find_one=AsyncMock(return_value=existing_user),
        insert_one=AsyncMock(),
    )
    monkeypatch.setattr(auth_service, "get_database", lambda: {"users": users})

    authenticated_user = anyio.run(
        auth_service.authenticate_google_user,
        "verified-id-token",
        UserRole.FACULTY,
    )

    assert authenticated_user is existing_user
    assert authenticated_user["role"] == "student"
    users.find_one.assert_awaited_once_with({"google_sub": "google-subject"})
    users.insert_one.assert_not_awaited()


def test_google_login_links_existing_email_account(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id.apps.googleusercontent.com")
    monkeypatch.setattr(
        auth_service,
        "_verify_google_id_token",
        AsyncMock(return_value={
            "sub": "google-subject",
            "email": "sam@example.com",
            "email_verified": True,
        }),
    )
    existing_user = sample_user()
    linked_user = {**existing_user, "google_sub": "google-subject"}
    users = SimpleNamespace(
        find_one=AsyncMock(side_effect=[None, existing_user, linked_user]),
        update_one=AsyncMock(),
    )
    monkeypatch.setattr(auth_service, "get_database", lambda: {"users": users})

    authenticated_user = anyio.run(
        auth_service.authenticate_google_user,
        "verified-id-token",
        UserRole.FACULTY,
    )

    assert authenticated_user is linked_user
    assert authenticated_user["role"] == "student"
    users.update_one.assert_awaited_once()


def test_google_login_rejects_conflicting_existing_link(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id.apps.googleusercontent.com")
    monkeypatch.setattr(
        auth_service,
        "_verify_google_id_token",
        AsyncMock(return_value={
            "sub": "different-google-subject",
            "email": "sam@example.com",
            "email_verified": True,
        }),
    )
    existing_user = {**sample_user(), "google_sub": "already-linked-subject"}
    users = SimpleNamespace(find_one=AsyncMock(side_effect=[None, existing_user]))
    monkeypatch.setattr(auth_service, "get_database", lambda: {"users": users})

    with pytest.raises(auth_service.GoogleAccountLinkError):
        anyio.run(
            auth_service.authenticate_google_user,
            "verified-id-token",
            UserRole.STUDENT,
        )

    users.find_one.assert_awaited()


def test_google_sign_in_rejects_unverified_email(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id.apps.googleusercontent.com")
    monkeypatch.setattr(
        auth_service,
        "_verify_google_id_token",
        AsyncMock(return_value={
            "sub": "google-subject",
            "email": "sam@example.com",
            "email_verified": False,
        }),
    )

    with pytest.raises(auth_service.InvalidGoogleTokenError):
        anyio.run(
            auth_service.authenticate_google_user,
            "unverified-id-token",
            UserRole.STUDENT,
        )


def test_profile_can_be_updated(monkeypatch) -> None:
    user = sample_user()
    current_user = UserResponse(
        id=str(user["_id"]),
        name=user["name"],
        email=user["email"],
        role=UserRole.STUDENT,
        profile=user["profile"],
        created_at=user["created_at"],
    )
    update_profile_mock = AsyncMock(return_value=user)
    monkeypatch.setattr(auth_routes, "update_user_profile", update_profile_mock)
    app.dependency_overrides[auth_dependencies.get_current_user] = lambda: current_user

    with TestClient(app) as client:
        response = client.patch(
            "/api/auth/me",
            json={"name": "Updated Student", "profile": {"college": "New University"}},
        )

    assert response.status_code == 200
    assert response.json()["name"] == user["name"]
    update_profile_mock.assert_awaited_once()
    assert update_profile_mock.await_args.args[0] == current_user.id
    assert update_profile_mock.await_args.args[1].profile == {"college": "New University"}


def test_current_user_requires_valid_bearer_token(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-secret-key-that-is-at-least-32-bytes")
    user = sample_user()
    monkeypatch.setattr(auth_dependencies, "is_token_revoked", AsyncMock(return_value=False))
    monkeypatch.setattr(auth_dependencies, "get_user_by_id", AsyncMock(return_value=user))
    token, _ = create_access_token(user_id=str(user["_id"]), email=user["email"], role=user["role"])

    with TestClient(app) as client:
        missing = client.get("/api/auth/me")
        authenticated = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert missing.status_code == 401
    assert authenticated.status_code == 200
    assert authenticated.json()["email"] == user["email"]


def test_logout_revokes_current_token(monkeypatch) -> None:
    claims = {"jti": "token-id", "exp": int(datetime.now(timezone.utc).timestamp()) + 600}
    revoke_mock = AsyncMock()
    monkeypatch.setattr(auth_routes, "revoke_token", revoke_mock)
    app.dependency_overrides[auth_dependencies.get_token_claims] = lambda: claims

    with TestClient(app) as client:
        response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"message": "Access token revoked"}
    revoke_mock.assert_awaited_once()


def test_admin_route_rejects_non_admin_role() -> None:
    app.dependency_overrides[auth_dependencies.get_current_user] = lambda: UserResponse(
        id="user-id",
        name="Sam Student",
        email="sam@example.com",
        role=UserRole.STUDENT,
        created_at=datetime.now(timezone.utc),
    )

    with TestClient(app) as client:
        response = client.get("/api/admin/health")

    assert response.status_code == 403


def test_admin_route_accepts_admin_role() -> None:
    app.dependency_overrides[auth_dependencies.get_current_user] = lambda: UserResponse(
        id="admin-id",
        name="Platform Admin",
        email="admin@example.com",
        role=UserRole.ADMIN,
        created_at=datetime.now(timezone.utc),
    )

    with TestClient(app) as client:
        response = client.get("/api/admin/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "access": "admin"}


def test_admin_role_cannot_be_registered_publicly() -> None:
    with TestClient(app) as client:
        response = client.post("/api/auth/register/admin", json={})

    assert response.status_code == 404


def test_passwords_are_hashed_and_verified() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_hash != "correct horse battery staple"
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)
