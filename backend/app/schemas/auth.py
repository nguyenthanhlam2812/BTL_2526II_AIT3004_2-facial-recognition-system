from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

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


class ChangePasswordResponse(BaseModel):
    ok: bool
    message: str
