from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import PyMongoError

from app.database.client import MongoDBNotConfigured
from app.models.auth import (
    AuthResponse,
    FacultyRegistration,
    GoogleLoginRequest,
    LoginRequest,
    LogoutResponse,
    MentorRegistration,
    ProblemOwnerRegistration,
    ProfileUpdateRequest,
    StudentRegistration,
    UserResponse,
    UserRole,
)
from app.services.auth import (
    DuplicateEmailError,
    GoogleIdentityProviderError,
    GoogleAccountLinkError,
    InactiveGoogleAccountError,
    InvalidGoogleTokenError,
    GoogleSignInNotConfigured,
    authenticate_user,
    authenticate_google_user,
    create_auth_response,
    create_user,
    is_token_revoked,
    revoke_token,
    to_user_response,
    update_user_profile,
)
from app.utils.auth_dependencies import get_current_user, get_token_claims
from app.utils.security import AuthConfigurationError, validate_auth_configuration
from app.utils.settings import get_google_client_id

router = APIRouter(prefix="/auth", tags=["authentication"])


def _raise_service_error(error: Exception) -> None:
    if isinstance(error, (MongoDBNotConfigured, PyMongoError)):
        raise HTTPException(status_code=503, detail="Database is not available") from error
    if isinstance(error, AuthConfigurationError):
        raise HTTPException(status_code=503, detail=f"Authentication is not configured: {error}") from error
    raise error


async def _register(payload, role: UserRole) -> AuthResponse:
    try:
        validate_auth_configuration()
        user = await create_user(payload, role)
        return create_auth_response(user)
    except DuplicateEmailError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (MongoDBNotConfigured, PyMongoError, AuthConfigurationError) as error:
        _raise_service_error(error)


@router.post("/register/student", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_student(payload: StudentRegistration) -> AuthResponse:
    return await _register(payload, UserRole.STUDENT)


@router.post("/register/problem-owner", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_problem_owner(payload: ProblemOwnerRegistration) -> AuthResponse:
    return await _register(payload, UserRole.PROBLEM_OWNER)


@router.post("/register/mentor", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_mentor(payload: MentorRegistration) -> AuthResponse:
    return await _register(payload, UserRole.MENTOR)


@router.post("/register/faculty", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_faculty(payload: FacultyRegistration) -> AuthResponse:
    return await _register(payload, UserRole.FACULTY)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest) -> AuthResponse:
    try:
        validate_auth_configuration()
        user = await authenticate_user(str(payload.email), payload.password)
    except (MongoDBNotConfigured, PyMongoError, AuthConfigurationError) as error:
        _raise_service_error(error)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return create_auth_response(user)


@router.post("/google", response_model=AuthResponse)
async def google_login(payload: GoogleLoginRequest) -> AuthResponse:
    try:
        if get_google_client_id() is None:
            raise GoogleSignInNotConfigured("Set GOOGLE_CLIENT_ID in the backend environment.")
        validate_auth_configuration()
        user = await authenticate_google_user(payload.id_token, UserRole(payload.role))
    except InvalidGoogleTokenError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    except InactiveGoogleAccountError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except GoogleAccountLinkError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except GoogleSignInNotConfigured as error:
        raise HTTPException(
            status_code=503,
            detail=f"Google sign-in is not configured on the server. {error}",
        ) from error
    except GoogleIdentityProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (MongoDBNotConfigured, PyMongoError, AuthConfigurationError) as error:
        _raise_service_error(error)
    return create_auth_response(user)


@router.get("/me", response_model=UserResponse)
async def current_user(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    try:
        document = await update_user_profile(current_user.id, payload)
    except (MongoDBNotConfigured, PyMongoError) as error:
        _raise_service_error(error)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if document is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return to_user_response(document)


@router.post("/logout", response_model=LogoutResponse)
async def logout(claims: dict = Depends(get_token_claims)) -> LogoutResponse:
    try:
        expires_at = datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc)
        await revoke_token(str(claims["jti"]), expires_at)
    except (MongoDBNotConfigured, PyMongoError) as error:
        _raise_service_error(error)
    return LogoutResponse(message="Access token revoked")