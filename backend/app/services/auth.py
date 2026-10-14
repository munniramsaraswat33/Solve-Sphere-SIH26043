from datetime import datetime, timezone
from typing import Any

import anyio
import jwt
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.database.client import get_database
from app.models.auth import (
    AdminRegistration,
    AuthResponse,
    FacultyProfile,
    FacultyRegistration,
    MentorProfile,
    MentorRegistration,
    ProblemOwnerProfile,
    ProblemOwnerRegistration,
    ProfileUpdateRequest,
    StudentProfile,
    StudentRegistration,
    ProfileBase,
    UserResponse,
    UserRole,
)
from app.utils.security import create_access_token, hash_password, verify_password
from app.utils.settings import get_google_client_id

RegistrationPayload = (
    StudentRegistration
    | ProblemOwnerRegistration
    | MentorRegistration
    | FacultyRegistration
    | AdminRegistration
)


class DuplicateEmailError(ValueError):
    """Raised when an account already uses the submitted email address."""


class InvalidGoogleTokenError(ValueError):
    """Raised when Google cannot verify the supplied identity token."""


class GoogleIdentityProviderError(RuntimeError):
    """Raised when Google's identity verification service is unavailable."""


class GoogleSignInNotConfigured(RuntimeError):
    """Raised when the Google OAuth client ID is not configured."""


class GoogleAccountLinkError(ValueError):
    """Raised when a Google identity conflicts with an already linked account."""


class InactiveGoogleAccountError(ValueError):
    """Raised when a Google identity belongs to a disabled account."""


GOOGLE_JWKS_CLIENT = jwt.PyJWKClient(
    "https://www.googleapis.com/oauth2/v3/certs",
    cache_keys=True,
    timeout=5,
)


PROFILE_MODELS = {
    UserRole.STUDENT: StudentProfile,
    UserRole.PROBLEM_OWNER: ProblemOwnerProfile,
    UserRole.MENTOR: MentorProfile,
    UserRole.FACULTY: FacultyProfile,
    UserRole.ADMIN: ProfileBase,
}


def normalize_email(email: str) -> str:
    return email.strip().lower()


def to_user_response(document: dict[str, Any]) -> UserResponse:
    return UserResponse(
        id=str(document["_id"]),
        name=document["name"],
        email=document["email"],
        role=document["role"],
        profile=document.get("profile", {}),
        created_at=document["created_at"],
    )


async def create_user(payload: RegistrationPayload, role: UserRole) -> dict[str, Any]:
    profile = getattr(payload, "profile", None)
    email = normalize_email(str(payload.email))
    document = {
        "name": (payload.name or "").strip() or email.split("@", 1)[0],
        "email": email,
        "password_hash": hash_password(payload.password),
        "role": role.value,
        "profile": profile.model_dump(mode="json", exclude_none=True) if profile else {},
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }

    try:
        result = await get_database()["users"].insert_one(document)
    except DuplicateKeyError as error:
        raise DuplicateEmailError("An account with this email already exists") from error

    document["_id"] = result.inserted_id
    return document


async def authenticate_google_user(id_token: str, role: UserRole) -> dict[str, Any]:
    client_id = get_google_client_id()
    if client_id is None:
        raise GoogleSignInNotConfigured("Set GOOGLE_CLIENT_ID in the backend environment.")
    claims = await _verify_google_id_token(id_token, client_id)
    if (
        claims.get("email_verified") not in {True, "true"}
        or not claims.get("sub")
        or not claims.get("email")
    ):
        raise InvalidGoogleTokenError("Google credential is invalid or expired")

    email = normalize_email(claims["email"])
    users = get_database()["users"]
    user = await users.find_one({"google_sub": claims["sub"]})
    if user is not None:
        if not user.get("is_active", True):
            raise InactiveGoogleAccountError("This account is unavailable")
        return user

    user = await get_user_by_email(email)
    if user is not None:
        if not user.get("is_active", True):
            raise InactiveGoogleAccountError("This account is unavailable")
        existing_sub = user.get("google_sub")
        if existing_sub and existing_sub != claims["sub"]:
            raise GoogleAccountLinkError("This email is already linked to a different Google account.")
        try:
            link_result = await users.update_one(
                {
                    "_id": user["_id"],
                    "$or": [
                        {"google_sub": {"$exists": False}},
                        {"google_sub": None},
                        {"google_sub": claims["sub"]},
                    ],
                },
                {"$set": {"google_sub": claims["sub"]}},
            )
            if link_result.matched_count == 0:
                linked_user = await users.find_one({"_id": user["_id"]})
                if linked_user is None:
                    raise GoogleIdentityProviderError("The account could not be loaded after sign-in.")
                if not linked_user.get("is_active", True):
                    raise InactiveGoogleAccountError("This account is unavailable")
                if linked_user.get("google_sub") != claims["sub"]:
                    raise GoogleAccountLinkError(
                        "This email is already linked to a different Google account."
                    )
                return linked_user
        except DuplicateKeyError:
            linked_user = await users.find_one({"google_sub": claims["sub"]})
            if linked_user is not None and linked_user.get("is_active", True):
                return linked_user
            raise GoogleAccountLinkError(
                "This Google account is already linked to another Solve Sphere account."
            ) from None
        linked_user = await users.find_one({"_id": user["_id"]})
        if linked_user is None:
            raise GoogleIdentityProviderError("The account could not be loaded after sign-in.")
        return linked_user

    document = {
        "name": (claims.get("name") or "").strip() or email.split("@", 1)[0],
        "email": email,
        "role": role.value,
        "profile": {},
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "google_sub": claims["sub"],
    }
    try:
        result = await users.insert_one(document)
    except DuplicateKeyError:
        user = await users.find_one({"google_sub": claims["sub"]})
        if user is None:
            user = await get_user_by_email(email)
        if user is None:
            raise
        if not user.get("is_active", True):
            raise InactiveGoogleAccountError("This account is unavailable")
        if user.get("google_sub") not in {None, claims["sub"]}:
            raise GoogleAccountLinkError(
                "This email is already linked to a different Google account."
            )
        return user

    document["_id"] = result.inserted_id
    return document


async def _verify_google_id_token(id_token: str, client_id: str) -> dict[str, Any]:
    try:
        return await anyio.to_thread.run_sync(
            _decode_google_id_token,
            id_token,
            client_id,
        )
    except jwt.InvalidTokenError as error:
        raise InvalidGoogleTokenError("Google credential is invalid or expired") from error
    except jwt.exceptions.MissingCryptographyError as error:
        raise GoogleIdentityProviderError(
            "Google identity verification requires the backend cryptography dependency."
        ) from error
    except jwt.PyJWKClientError as error:
        raise GoogleIdentityProviderError("Google identity verification is unavailable") from error


def _decode_google_id_token(id_token: str, client_id: str) -> dict[str, Any]:
    signing_key = GOOGLE_JWKS_CLIENT.get_signing_key_from_jwt(id_token)
    claims = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=client_id,
        issuer=["accounts.google.com", "https://accounts.google.com"],
        options={
            "require": [
                "aud",
                "email",
                "email_verified",
                "exp",
                "iat",
                "iss",
                "sub",
            ],
        },
    )
    if (
        claims.get("email_verified") is not True
        or not claims.get("sub")
        or not claims.get("email")
    ):
        raise InvalidGoogleTokenError("Google credential is invalid or expired")
    return claims


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    return await get_database()["users"].find_one({"email": normalize_email(email)})


async def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    if not ObjectId.is_valid(user_id):
        return None
    return await get_database()["users"].find_one({"_id": ObjectId(user_id)})


async def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    user = await get_user_by_email(email)
    if user is None or not user.get("is_active", True) or not user.get("password_hash"):
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


async def update_user_profile(user_id: str, payload: ProfileUpdateRequest) -> dict[str, Any] | None:
    if not ObjectId.is_valid(user_id):
        return None
    collection = get_database()["users"]
    user_object_id = ObjectId(user_id)
    user = await collection.find_one({"_id": user_object_id})
    if user is None:
        return None

    role = UserRole(user["role"])
    profile_model = PROFILE_MODELS.get(role)
    if profile_model is None:
        raise ValueError("This account role does not support profile updates")

    unknown_fields = set(payload.profile) - set(profile_model.model_fields)
    if unknown_fields:
        unexpected = ", ".join(sorted(unknown_fields))
        raise ValueError(f"Unsupported profile field(s): {unexpected}")

    validated_profile = profile_model.model_validate(payload.profile)
    profile_updates = validated_profile.model_dump(mode="json", exclude_unset=True)
    updates: dict[str, Any] = {}
    removals: dict[str, str] = {}
    for field, value in profile_updates.items():
        key = f"profile.{field}"
        if value is None:
            removals[key] = ""
        else:
            updates[key] = value
    if payload.name is not None:
        updates["name"] = payload.name.strip()

    update: dict[str, dict[str, Any]] = {}
    if updates:
        update["$set"] = updates
    if removals:
        update["$unset"] = removals
    if update:
        await collection.update_one({"_id": user_object_id}, update)
    return await collection.find_one({"_id": user_object_id})


def create_auth_response(document: dict[str, Any]) -> AuthResponse:
    user = to_user_response(document)
    token, expires_in = create_access_token(
        user_id=user.id,
        email=str(user.email),
        role=user.role.value,
    )
    return AuthResponse(access_token=token, expires_in=expires_in, user=user)


async def is_token_revoked(token_id: str) -> bool:
    return await get_database()["revoked_tokens"].find_one({"jti": token_id}) is not None


async def revoke_token(token_id: str, expires_at: datetime) -> None:
    await get_database()["revoked_tokens"].replace_one(
        {"jti": token_id},
        {"jti": token_id, "expires_at": expires_at},
        upsert=True,
    )