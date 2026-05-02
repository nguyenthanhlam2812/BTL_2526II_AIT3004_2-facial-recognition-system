from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthUser(BaseModel):
    id: int
    username: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: AuthUser
