from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class UserRole(str, Enum):
    STUDENT = "student"
    PROBLEM_OWNER = "problem_owner"
    MENTOR = "mentor"
    FACULTY = "faculty"
    ADMIN = "admin"


class ProfileBase(BaseModel):
    pass


class StudentProfile(ProfileBase):
    college: str | None = Field(default=None, min_length=2, max_length=160)
    branch: str | None = Field(default=None, min_length=2, max_length=120)
    year: int | None = Field(default=None, ge=1, le=8)
    skills: list[str] = Field(default_factory=list, max_length=50)
    interests: list[str] = Field(default_factory=list, max_length=50)
    experience: str | None = Field(default=None, max_length=2000)
    github: HttpUrl | None = None
    linkedin: HttpUrl | None = None
    portfolio: HttpUrl | None = None


class ProblemOwnerProfile(ProfileBase):
    organization_name: str | None = Field(default=None, min_length=2, max_length=160)
    organization_type: Literal["government", "ngo", "industry", "citizen", "other"] | None = None
    location: str | None = Field(default=None, max_length=160)


class MentorProfile(ProfileBase):
    organization_name: str | None = Field(default=None, min_length=2, max_length=160)
    expertise: str | None = Field(default=None, min_length=2, max_length=500)
    skills: list[str] = Field(default_factory=list, max_length=50)


class FacultyProfile(ProfileBase):
    university: str | None = Field(default=None, min_length=2, max_length=160)
    department: str | None = Field(default=None, min_length=2, max_length=160)


class RegistrationBase(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class StudentRegistration(RegistrationBase):
    profile: StudentProfile = Field(default_factory=StudentProfile)


class ProblemOwnerRegistration(RegistrationBase):
    profile: ProblemOwnerProfile = Field(default_factory=ProblemOwnerProfile)


class MentorRegistration(RegistrationBase):
    profile: MentorProfile = Field(default_factory=MentorProfile)


class FacultyRegistration(RegistrationBase):
    profile: FacultyProfile = Field(default_factory=FacultyProfile)


class AdminRegistration(RegistrationBase):
    pass


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1)
    role: Literal["student", "problem_owner", "mentor", "faculty"] = "student"


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    profile: dict[str, Any] = Field(default_factory=dict)


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: UserRole
    profile: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserResponse


class LogoutResponse(BaseModel):
    message: str
