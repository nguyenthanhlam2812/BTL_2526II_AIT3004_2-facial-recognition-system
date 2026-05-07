from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.config import get_settings
from backend.app.models.attendance_event import AttendanceEvent
from backend.app.models.employee import Employee
from backend.app.schemas.attendance import (
    AttendanceActionType,
    AttendanceEmployeeSummary,
    AttendanceEventListResponse,
    AttendanceEventRead,
    AttendanceFrameResponse,
    AttendanceStatus,
)
from backend.app.services.face_analyzer import analyze_image_bytes
from backend.app.services.qdrant_service import VectorStoreError, search_face_embedding


class AttendanceInfrastructureError(Exception):
    pass


def recognize_attendance_frame(
    db: Session,
    *,
    image_bytes: bytes,
    action_type: AttendanceActionType,
    captured_at: datetime | None,
    camera_id: str | None,
) -> AttendanceFrameResponse:
    analysis = analyze_image_bytes(image_bytes)

    if analysis["status"] != "success":
        faces_detected = int(analysis.get("faces_detected", 0))
        error_message = str(
            analysis.get("error_message") or "Cannot process attendance frame."
        )

        if faces_detected > 1:
            return _save_unmatched_event(
                db,
                action_type=action_type,
                attendance_status="multiple_faces",
                message="Multiple faces detected.",
                score=None,
                captured_at=captured_at,
                camera_id=camera_id,
            )

        return _save_unmatched_event(
            db,
            action_type=action_type,
            attendance_status="unknown_face",
            message=error_message,
            score=None,
            captured_at=captured_at,
            camera_id=camera_id,
        )

    try:
        search_result = search_face_embedding(
            embedding=list(analysis["embedding"]),
            limit=1,
        )
    except VectorStoreError as exc:
        raise AttendanceInfrastructureError(
            "Attendance vector search is unavailable."
        ) from exc

    if search_result is None:
        return _save_unmatched_event(
            db,
            action_type=action_type,
            attendance_status="unknown_face",
            message="Face not recognized.",
            score=None,
            captured_at=captured_at,
            camera_id=camera_id,
        )

    threshold = get_settings().attendance_threshold
    if search_result.employee_id is None or search_result.score < threshold:
        return _save_unmatched_event(
            db,
            action_type=action_type,
            attendance_status="unknown_face",
            message="Face not recognized.",
            score=search_result.score,
            captured_at=captured_at,
            camera_id=camera_id,
        )

    employee = db.get(Employee, search_result.employee_id)
    if employee is None:
        return _save_unmatched_event(
            db,
            action_type=action_type,
            attendance_status="unknown_face",
            message="Matched embedding points to a missing employee.",
            score=search_result.score,
            captured_at=captured_at,
            camera_id=camera_id,
        )

    event = AttendanceEvent(
        employee_id=employee.id,
        action_type=action_type,
        attendance_status="recorded",
        score=Decimal(str(search_result.score)),
        camera_id=camera_id,
        snapshot_object_key=None,
        captured_at=captured_at,
    )
    event = _save_event(db, event)

    return AttendanceFrameResponse(
        matched=True,
        employee=AttendanceEmployeeSummary.model_validate(employee),
        score=search_result.score,
        action_type=action_type,
        attendance_status="recorded",
        message=f"{_action_label(action_type)} recorded.",
        event_id=event.id,
    )


def list_attendance_events(
    db: Session,
    *,
    employee_id: int | None,
    action_type: AttendanceActionType | None,
    from_: datetime | None,
    to: datetime | None,
    page: int,
    page_size: int,
) -> AttendanceEventListResponse:
    filters = []
    event_time = func.coalesce(
        AttendanceEvent.captured_at,
        AttendanceEvent.created_at,
    )

    if employee_id is not None:
        filters.append(AttendanceEvent.employee_id == employee_id)

    if action_type is not None:
        filters.append(AttendanceEvent.action_type == action_type)

    if from_ is not None:
        filters.append(event_time >= from_)

    if to is not None:
        filters.append(event_time <= to)

    total_stmt = select(func.count()).select_from(AttendanceEvent)
    items_stmt = (
        select(AttendanceEvent)
        .options(selectinload(AttendanceEvent.employee))
        .order_by(AttendanceEvent.id.desc())
    )

    if filters:
        total_stmt = total_stmt.where(*filters)
        items_stmt = items_stmt.where(*filters)

    total = db.scalar(total_stmt) or 0
    items = db.scalars(
        items_stmt.offset((page - 1) * page_size).limit(page_size)
    ).all()

    return AttendanceEventListResponse(
        items=[_build_event_read(item) for item in items],
        total=total,
    )


def _save_unmatched_event(
    db: Session,
    *,
    action_type: AttendanceActionType,
    attendance_status: AttendanceStatus,
    message: str,
    score: float | None,
    captured_at: datetime | None,
    camera_id: str | None,
) -> AttendanceFrameResponse:
    event = AttendanceEvent(
        employee_id=None,
        action_type=action_type,
        attendance_status=attendance_status,
        score=Decimal(str(score)) if score is not None else None,
        camera_id=camera_id,
        snapshot_object_key=None,
        captured_at=captured_at,
    )
    event = _save_event(db, event)

    return AttendanceFrameResponse(
        matched=False,
        employee=None,
        score=score,
        action_type=action_type,
        attendance_status=attendance_status,
        message=message,
        event_id=event.id,
    )


def _save_event(db: Session, event: AttendanceEvent) -> AttendanceEvent:
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def _build_event_read(event: AttendanceEvent) -> AttendanceEventRead:
    employee = (
        AttendanceEmployeeSummary.model_validate(event.employee)
        if event.employee is not None
        else None
    )

    return AttendanceEventRead(
        id=event.id,
        created_at=event.created_at,
        captured_at=event.captured_at,
        action_type=event.action_type,
        attendance_status=event.attendance_status,
        score=float(event.score) if event.score is not None else None,
        camera_id=event.camera_id,
        snapshot_object_key=event.snapshot_object_key,
        employee=employee,
    )


def _action_label(action_type: AttendanceActionType) -> str:
    return "Check-in" if action_type == "check_in" else "Check-out"
