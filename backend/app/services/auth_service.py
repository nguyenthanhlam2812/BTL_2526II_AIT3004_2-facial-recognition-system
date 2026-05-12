from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.schemas.auth import AuthUser, LoginResponse
from backend.app.security import create_access_token, get_password_hash, verify_password


def authenticate_user(
    db: Session,
    username: str,
    password: str,
) -> LoginResponse | None:
    stmt = select(User).where(User.username == username)
    user = db.scalar(stmt)

    if user is None:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    token = create_access_token(
        {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role,
        }
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=AuthUser(
            id=user.id,
            username=user.username,
            role=user.role,
        ),
    )


def change_user_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
) -> bool:
    if not verify_password(current_password, user.password_hash):
        return False

    user.password_hash = get_password_hash(new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return True
