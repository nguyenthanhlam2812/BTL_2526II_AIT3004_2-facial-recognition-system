from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi import Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.db.session import get_db
from backend.app.models.user import (
    USER_ROLE_ADMIN,
    USER_ROLE_OWNER,
    USER_ROLE_VIEWER,
    User,
)
from backend.app.security import decode_access_token


bearer_scheme = HTTPBearer()
ADMIN_READ_ROLES = {USER_ROLE_OWNER, USER_ROLE_ADMIN, USER_ROLE_VIEWER}
ADMIN_WRITE_ROLES = {USER_ROLE_OWNER, USER_ROLE_ADMIN}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        user_id = payload.get("user_id")
    except JWTError as exc:
        raise credentials_exception from exc

    if user_id is None:
        raise credentials_exception

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ADMIN_READ_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin console access is required.",
        )

    return current_user


def require_operator(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ADMIN_WRITE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner or admin role is required.",
        )

    return current_user


def require_owner(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != USER_ROLE_OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner role is required.",
        )

    return current_user


def require_kiosk_token(
    x_kiosk_token: str | None = Header(default=None, alias="X-Kiosk-Token"),
) -> None:
    settings = get_settings()
    expected = settings.kiosk_api_token
    provided = (x_kiosk_token or "").strip()

    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid kiosk token.",
        )
