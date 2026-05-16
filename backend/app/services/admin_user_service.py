from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.user import USER_ROLE_OWNER, User
from backend.app.schemas.admin_user import AdminUserCreate, AdminUserUpdate
from backend.app.security import get_password_hash


class DuplicateUsernameError(ValueError):
    pass


class UserSafetyError(ValueError):
    pass


def list_admin_users(
    db: Session,
    *,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[User], int]:
    stmt = select(User)
    count_stmt = select(func.count()).select_from(User)

    query = (q or "").strip()
    if query:
        pattern = f"%{query.lower()}%"
        stmt = stmt.where(func.lower(User.username).like(pattern))
        count_stmt = count_stmt.where(func.lower(User.username).like(pattern))

    total = int(db.scalar(count_stmt) or 0)
    items = list(
        db.scalars(
            stmt.order_by(User.id.asc()).offset((page - 1) * page_size).limit(page_size)
        )
    )
    return items, total


def create_admin_user(db: Session, payload: AdminUserCreate) -> User:
    username = payload.username.strip()
    if _username_exists(db, username):
        raise DuplicateUsernameError("Username already exists.")

    user = User(
        username=username,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_admin_user(
    db: Session,
    *,
    user_id: int,
    payload: AdminUserUpdate,
) -> User | None:
    user = db.get(User, user_id)
    if user is None:
        return None

    next_role = payload.role if payload.role is not None else user.role
    next_is_active = payload.is_active if payload.is_active is not None else user.is_active
    if _would_remove_last_active_owner(db, user, next_role, next_is_active):
        raise UserSafetyError("At least one active owner must remain.")

    if payload.username is not None:
        username = payload.username.strip()
        if _username_exists(db, username, exclude_user_id=user.id):
            raise DuplicateUsernameError("Username already exists.")
        user.username = username

    user.role = next_role
    user.is_active = next_is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def reset_admin_user_password(
    db: Session,
    *,
    user_id: int,
    password: str,
) -> User | None:
    user = db.get(User, user_id)
    if user is None:
        return None

    user.password_hash = get_password_hash(password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_admin_user(
    db: Session,
    *,
    user_id: int,
    current_user_id: int,
) -> bool | None:
    user = db.get(User, user_id)
    if user is None:
        return None

    if user.id == current_user_id:
        raise UserSafetyError("You cannot delete your own account.")

    if user.role == USER_ROLE_OWNER and user.is_active and _active_owner_count(db) <= 1:
        raise UserSafetyError("At least one active owner must remain.")

    db.delete(user)
    db.commit()
    return True


def _username_exists(
    db: Session,
    username: str,
    *,
    exclude_user_id: int | None = None,
) -> bool:
    stmt = select(User.id).where(func.lower(User.username) == username.lower())
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    return db.scalar(stmt) is not None


def _active_owner_count(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == USER_ROLE_OWNER, User.is_active.is_(True))
        )
        or 0
    )


def _would_remove_last_active_owner(
    db: Session,
    user: User,
    next_role: str,
    next_is_active: bool,
) -> bool:
    if user.role != USER_ROLE_OWNER or not user.is_active:
        return False
    if next_role == USER_ROLE_OWNER and next_is_active:
        return False
    return _active_owner_count(db) <= 1
