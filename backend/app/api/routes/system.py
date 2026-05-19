from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import require_owner
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.system import (
    SystemSettingsResetRequest,
    SystemSettingsResponse,
    SystemSettingsUpdate,
)
from backend.app.services.system_settings_service import (
    SystemSettingsValidationError,
    build_system_settings_response,
    reset_system_settings,
    update_system_settings,
)


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/settings", response_model=SystemSettingsResponse)
def get_system_settings(
    db: Session = Depends(get_db),
    _: User = Depends(require_owner),
) -> SystemSettingsResponse:
    return build_system_settings_response(db)


@router.patch("/settings", response_model=SystemSettingsResponse)
def update_system_settings_route(
    payload: SystemSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> SystemSettingsResponse:
    try:
        return update_system_settings(
            db,
            payload,
            updated_by_user_id=current_user.id,
        )
    except SystemSettingsValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/settings/reset", response_model=SystemSettingsResponse)
def reset_system_settings_route(
    payload: SystemSettingsResetRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_owner),
) -> SystemSettingsResponse:
    try:
        return reset_system_settings(db, keys=payload.keys)
    except SystemSettingsValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
