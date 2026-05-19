from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.app.schemas.validation import validate_password_strength

UserRole = Literal["owner", "admin", "viewer"]


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthUser(BaseModel):
    id: int
    username: str
    role: UserRole


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: AuthUser


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)


class ChangePasswordResponse(BaseModel):
    ok: bool
    message: str
