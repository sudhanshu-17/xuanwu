"""Request/response schemas for the identity (authentication) endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


# --- responses ---------------------------------------------------------------
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    uid: str
    email: EmailStr
    username: str | None
    role: str
    state: str
    level: int
    otp: bool
    created_at: datetime


class SessionOut(BaseModel):
    user: UserOut
    csrf_token: str


class CsrfOut(BaseModel):
    csrf_token: str


class ValidityOut(BaseModel):
    valid: bool


class EmailCodeOut(BaseModel):
    message: str
    confirmation_token: str | None = None  # populated only outside production


class PasswordCodeOut(BaseModel):
    message: str
    reset_token: str | None = None  # populated only outside production


class PasswordPolicyOut(BaseModel):
    min_length: int
    max_length: int
    min_score: int


class ConfigsOut(BaseModel):
    password: PasswordPolicyOut
    captcha_provider: str
    recaptcha_site_key: str | None = None


class VersionOut(BaseModel):
    version: str
    git_tag: str
    git_sha: str


# --- requests ----------------------------------------------------------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    username: str | None = None
    captcha_response: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    otp_code: str | None = None
    captcha_response: str | None = None


class EmailGenerateIn(BaseModel):
    email: EmailStr


class EmailConfirmIn(BaseModel):
    token: str


class PasswordGenerateIn(BaseModel):
    email: EmailStr


class PasswordConfirmIn(BaseModel):
    token: str
    password: str
