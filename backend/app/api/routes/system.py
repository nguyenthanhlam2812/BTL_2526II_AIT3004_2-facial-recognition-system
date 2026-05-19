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
from backend.app.services.audit_log_service import record_audit_log


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
    updated_keys = sorted(payload.model_dump(exclude_unset=True, exclude_none=True).keys())
    try:
        response = update_system_settings(
            db,
            payload,
            updated_by_user_id=current_user.id,
        )
    except SystemSettingsValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record_audit_log(
        db,
        actor=current_user,
        action="system_setting.update",
        resource_type="system_setting",
        resource_label=", ".join(updated_keys) if updated_keys else "settings",
        metadata={"keys": updated_keys},
    )
    return response


@router.post("/settings/reset", response_model=SystemSettingsResponse)
def reset_system_settings_route(
    payload: SystemSettingsResetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> SystemSettingsResponse:
    try:
        response = reset_system_settings(db, keys=payload.keys)
    except SystemSettingsValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record_audit_log(
        db,
        actor=current_user,
        action="system_setting.reset",
        resource_type="system_setting",
        resource_label=", ".join(payload.keys) if payload.keys else "all settings",
        metadata={"keys": payload.keys, "reset_all": payload.keys is None},
    )
    return response
