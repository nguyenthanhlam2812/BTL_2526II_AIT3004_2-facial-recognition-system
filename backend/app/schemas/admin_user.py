from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.schemas.auth import UserRole
from backend.app.schemas.validation import normalize_username as normalize_username_value
from backend.app.schemas.validation import validate_password_strength


class AdminUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserRead]
    total: int


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = "admin"
    is_active: bool = True

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return normalize_username_value(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class AdminUserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=64)
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("username", mode="before")
    @classmethod
    def normalize_optional_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_username_value(value)


class AdminUserResetPassword(BaseModel):
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class AdminUserWriteResponse(BaseModel):
    ok: bool
    user: AdminUserRead


class AdminUserDeleteResponse(BaseModel):
    ok: bool
