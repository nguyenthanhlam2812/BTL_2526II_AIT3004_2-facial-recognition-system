from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt 
from passlib.context import CryptContext

from backend.app.config import get_settings


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict[str, Any]) -> str:
    settings = get_settings()
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload["exp"] = expire
    
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
