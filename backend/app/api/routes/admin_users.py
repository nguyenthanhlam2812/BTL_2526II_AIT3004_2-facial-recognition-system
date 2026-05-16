from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import require_owner
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.admin_user import (
    AdminUserCreate,
    AdminUserDeleteResponse,
    AdminUserListResponse,
    AdminUserRead,
    AdminUserResetPassword,
    AdminUserUpdate,
    AdminUserWriteResponse,
)
from backend.app.services.admin_user_service import (
    DuplicateUsernameError,
    UserSafetyError,
    create_admin_user as create_admin_user_service,
    delete_admin_user as delete_admin_user_service,
    list_admin_users as list_admin_users_service,
    reset_admin_user_password as reset_admin_user_password_service,
    update_admin_user as update_admin_user_service,
)


router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=AdminUserListResponse)
def list_admin_users(
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_owner),
) -> AdminUserListResponse:
    items, total = list_admin_users_service(db, q=q, page=page, page_size=page_size)
    return AdminUserListResponse(items=items, total=total)


@router.post("", response_model=AdminUserRead, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_owner),
) -> AdminUserRead:
    try:
        return create_admin_user_service(db, payload)
    except DuplicateUsernameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists.",
        ) from exc


@router.put("/{user_id}", response_model=AdminUserRead)
def update_admin_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_owner),
) -> AdminUserRead:
    try:
        user = update_admin_user_service(db, user_id=user_id, payload=payload)
    except DuplicateUsernameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists.",
        ) from exc
    except UserSafetyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@router.post("/{user_id}/reset-password", response_model=AdminUserWriteResponse)
def reset_admin_user_password(
    user_id: int,
    payload: AdminUserResetPassword,
    db: Session = Depends(get_db),
    _: User = Depends(require_owner),
) -> AdminUserWriteResponse:
    user = reset_admin_user_password_service(db, user_id=user_id, password=payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return AdminUserWriteResponse(ok=True, user=user)


@router.delete("/{user_id}", response_model=AdminUserDeleteResponse)
def delete_admin_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> AdminUserDeleteResponse:
    try:
        deleted = delete_admin_user_service(
            db,
            user_id=user_id,
            current_user_id=current_user.id,
        )
    except UserSafetyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if deleted is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return AdminUserDeleteResponse(ok=True)
