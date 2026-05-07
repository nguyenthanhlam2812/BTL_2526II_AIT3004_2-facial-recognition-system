from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.api.deps import require_admin
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.attendance import (
    AttendanceActionType,
    AttendanceEventListResponse,
    AttendanceFrameResponse,
)
from backend.app.services.attendance_service import (
    AttendanceInfrastructureError,
    list_attendance_events as list_attendance_events_service,
    recognize_attendance_frame as recognize_attendance_frame_service,
)

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/frame", response_model=AttendanceFrameResponse)
def recognize_attendance_frame(
    image: UploadFile = File(...),
    action_type: AttendanceActionType = Form(...),
    captured_at: datetime | None = Form(default=None),
    camera_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> AttendanceFrameResponse:
    image_bytes = image.file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image file is empty.",
        )

    try:
        return recognize_attendance_frame_service(
            db,
            image_bytes=image_bytes,
            action_type=action_type,
            captured_at=captured_at,
            camera_id=camera_id,
        )
    except AttendanceInfrastructureError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.get("/events", response_model=AttendanceEventListResponse)
def list_attendance_events(
    employee_id: int | None = Query(default=None),
    action_type: AttendanceActionType | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AttendanceEventListResponse:
    return list_attendance_events_service(
        db,
        employee_id=employee_id,
        action_type=action_type,
        from_=from_,
        to=to,
        page=page,
        page_size=page_size,
    )
