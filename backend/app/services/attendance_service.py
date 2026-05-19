from __future__ import annotations

import csv
import inspect
from io import StringIO
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Literal

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.config import get_business_timezone
from backend.app.models.attendance_event import AttendanceEvent
from backend.app.models.employee import Employee
from backend.app.schemas.attendance import (
    AttendanceActionType,
    AttendanceDailyReportListResponse,
    AttendanceDailyReportRead,
    AttendanceDailyReportStatus,
    AttendanceDashboardSummaryResponse,
    AttendanceDashboardTodaySummary,
    AttendanceDashboardTrendPoint,
    AttendanceEmployeeSummary,
    AttendanceEventListResponse,
    AttendanceEventRead,
    AttendanceFrameResponse,
    AttendanceStatus,
)
from backend.app.services import camera_gate_service
from backend.app.services.face_analyzer import analyze_image_bytes
from backend.app.services.qdrant_service import VectorStoreError, search_face_embeddings
from backend.app.services.system_settings_service import get_effective_runtime_settings


class AttendanceInfrastructureError(Exception):
    pass


class AttendanceValidationError(ValueError):
    pass


FACE_SEARCH_LIMIT = 5
RECORDED_EVENT_DEDUPE_WINDOW = timedelta(seconds=10)
CAMERA_MATCH_GATE_TTL = timedelta(minutes=5)
REPORT_LATE_THRESHOLD = time(hour=9)
MAX_REPORT_DAYS = 31
NO_FACE_MESSAGE = "No face detected."
MAX_EXPORT_EVENTS = 50_000


logger = structlog.get_logger(__name__)


def recognize_attendance_frame(
    db: Session,
    *,
    image_bytes: bytes,
    action_type: AttendanceActionType,
    captured_at: datetime | None,
    camera_id: str | None,
    record_unmatched: bool = True,
) -> AttendanceFrameResponse:
    """Recognise a single kiosk frame and record the attendance event if any.

    Pipeline:
        1. Run InsightFace detection + embedding extraction on the bytes.
        2. Query Qdrant for the top ``FACE_SEARCH_LIMIT`` candidates.
        3. Walk candidates in descending score and pick the first ACTIVE employee
           whose score >= the runtime threshold.
        4. Apply the dedupe gates (per-camera 5 min, per-employee 10 s) before
           writing a new ``AttendanceEvent``.

    Policy — inactive-employee silently dropped:
        If the only above-threshold match belongs to an inactive employee we
        intentionally DO NOT record any event (matched or unmatched). The caller
        receives an ``unknown_face`` response with ``record_event=False`` so the
        UI cannot enumerate disabled accounts via score signals. See the
        ``inactive_match_seen`` branch below.
    """
    request_received_at = datetime.now(timezone.utc)
    normalized_captured_at = _normalize_utc_naive(captured_at)
    runtime_settings = get_effective_runtime_settings(db)
    analysis = _analyze_image_bytes(image_bytes, runtime_settings)

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
                captured_at=normalized_captured_at,
                camera_id=camera_id,
                record_event=record_unmatched,
            )

        if error_message == NO_FACE_MESSAGE:
            _clear_camera_match_gate(camera_id=camera_id, action_type=action_type)

        return _save_unmatched_event(
            db,
            action_type=action_type,
            attendance_status="unknown_face",
            message=error_message,
            score=None,
            captured_at=normalized_captured_at,
            camera_id=camera_id,
            record_event=record_unmatched,
        )

    try:
        search_results = search_face_embeddings(
            embedding=list(analysis["embedding"]),
            limit=FACE_SEARCH_LIMIT,
        )
    except VectorStoreError as exc:
        raise AttendanceInfrastructureError(
            "Attendance vector search is unavailable."
        ) from exc

    if not search_results:
        return _save_unmatched_event(
            db,
            action_type=action_type,
            attendance_status="unknown_face",
            message="Face not recognized.",
            score=None,
            captured_at=normalized_captured_at,
            camera_id=camera_id,
            record_event=record_unmatched,
        )

    threshold = runtime_settings.attendance_threshold
    inactive_match_seen = False
    employee: Employee | None = None
    search_result = None

    for candidate_result in search_results:
        if candidate_result.employee_id is None:
            continue

        if candidate_result.score < threshold:
            # Qdrant returns results in descending score order; remaining results
            # are also below threshold so stop scanning here.
            break

        candidate = db.get(Employee, candidate_result.employee_id)
        if candidate is None:
            continue
        if candidate.status != "active":
            inactive_match_seen = True
            continue

        employee = candidate
        search_result = candidate_result
        break

    if employee is None or search_result is None:
        # No active match. If we passed over an inactive match, policy says to
        # hide that fact and not record an event at all.
        if inactive_match_seen:
            logger.warning(
                "attendance.inactive_match_skipped",
                camera_id=camera_id,
                action_type=str(action_type),
            )
            return _save_unmatched_event(
                db,
                action_type=action_type,
                attendance_status="unknown_face",
                message="Face not recognized.",
                score=None,
                captured_at=normalized_captured_at,
                camera_id=camera_id,
                record_event=False,
            )
        return _save_unmatched_event(
            db,
            action_type=action_type,
            attendance_status="unknown_face",
            message="Face not recognized.",
            score=search_results[0].score,
            captured_at=normalized_captured_at,
            camera_id=camera_id,
            record_event=record_unmatched,
        )

    camera_gate_event_id = _find_camera_match_gate_event_id(
        camera_id=camera_id,
        action_type=action_type,
        employee_id=employee.id,
        request_received_at=request_received_at,
    )
    if camera_gate_event_id is not None:
        return AttendanceFrameResponse(
            matched=True,
            employee=AttendanceEmployeeSummary.model_validate(employee),
            score=search_result.score,
            action_type=action_type,
            attendance_status="recorded",
            message=f"{_action_label(action_type)} already recorded recently.",
            event_id=camera_gate_event_id,
        )

    recent_event = _find_recent_recorded_event(
        db,
        employee_id=employee.id,
        action_type=action_type,
        request_received_at=request_received_at,
    )
    if recent_event is not None:
        return AttendanceFrameResponse(
            matched=True,
            employee=AttendanceEmployeeSummary.model_validate(employee),
            score=search_result.score,
            action_type=action_type,
            attendance_status="recorded",
            message=f"{_action_label(action_type)} already recorded recently.",
            event_id=recent_event.id,
        )

    event = AttendanceEvent(
        employee_id=employee.id,
        action_type=action_type,
        attendance_status="recorded",
        score=Decimal(str(search_result.score)),
        camera_id=camera_id,
        snapshot_object_key=None,
        captured_at=normalized_captured_at,
    )
    event = _save_event(db, event)
    _set_camera_match_gate(
        camera_id=camera_id,
        action_type=action_type,
        employee_id=employee.id,
        event_id=event.id,
        updated_at=request_received_at,
    )
    logger.info(
        "attendance.match",
        employee_id=employee.id,
        event_id=event.id,
        score=float(search_result.score),
        camera_id=camera_id,
        action_type=str(action_type),
    )

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
    filters = _build_attendance_filters(
        employee_id=employee_id,
        action_type=action_type,
        from_=from_,
        to=to,
    )
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
        items=[_build_event_read(db, item) for item in items],
        total=total,
    )


def export_attendance_events_csv(
    db: Session,
    *,
    employee_id: int | None,
    action_type: AttendanceActionType | None,
    from_: datetime | None,
    to: datetime | None,
) -> str:
    filters = _build_attendance_filters(
        employee_id=employee_id,
        action_type=action_type,
        from_=from_,
        to=to,
    )
    items_stmt = (
        select(AttendanceEvent)
        .options(selectinload(AttendanceEvent.employee))
        .order_by(AttendanceEvent.id.desc())
    )
    if filters:
        items_stmt = items_stmt.where(*filters)

    total_stmt = select(func.count()).select_from(AttendanceEvent)
    if filters:
        total_stmt = total_stmt.where(*filters)
    total = db.scalar(total_stmt) or 0
    if total > MAX_EXPORT_EVENTS:
        raise AttendanceValidationError(
            f"Attendance event export exceeds {MAX_EXPORT_EVENTS} rows. Narrow the filters and try again."
        )

    events = db.scalars(items_stmt).all()
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer, lineterminator="\n")
    writer.writerow(
        [
            "event_id",
            "event_time",
            "employee_code",
            "full_name",
            "action_type",
            "attendance_status",
            "score",
            "camera_id",
        ]
    )
    for event in events:
        event_time = _get_business_local_event_datetime(db, event)
        writer.writerow(
            [
                event.id,
                event_time.isoformat() if event_time is not None else "",
                event.employee.employee_code if event.employee is not None else "",
                event.employee.full_name if event.employee is not None else "",
                event.action_type,
                event.attendance_status,
                float(event.score) if event.score is not None else "",
                event.camera_id or "",
            ]
        )

    return csv_buffer.getvalue()


def list_daily_attendance_reports(
    db: Session,
    *,
    date_: date | None,
    from_: date | None,
    to: date | None,
    employee_id: int | None,
    department: str | None,
    status: AttendanceDailyReportStatus | None,
    page: int,
    page_size: int,
) -> AttendanceDailyReportListResponse:
    rows = _build_daily_attendance_report_rows(
        db,
        date_=date_,
        from_=from_,
        to=to,
        employee_id=employee_id,
        department=department,
        status=status,
    )
    total = len(rows)
    items = rows[(page - 1) * page_size : page * page_size]
    return AttendanceDailyReportListResponse(items=items, total=total)


def export_daily_attendance_reports_csv(
    db: Session,
    *,
    date_: date | None,
    from_: date | None,
    to: date | None,
    employee_id: int | None,
    department: str | None,
    status: AttendanceDailyReportStatus | None,
) -> str:
    rows = _build_daily_attendance_report_rows(
        db,
        date_=date_,
        from_=from_,
        to=to,
        employee_id=employee_id,
        department=department,
        status=status,
    )
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer, lineterminator="\n")
    writer.writerow(
        [
            "date",
            "employee_code",
            "full_name",
            "department",
            "first_check_in",
            "last_check_out",
            "summary_status",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.date.isoformat(),
                row.employee_code,
                row.full_name,
                row.department,
                row.first_check_in.isoformat() if row.first_check_in else "",
                row.last_check_out.isoformat() if row.last_check_out else "",
                row.summary_status,
            ]
        )
    return csv_buffer.getvalue()


def get_attendance_dashboard_summary(
    db: Session,
    *,
    days: Literal[7, 30],
) -> AttendanceDashboardSummaryResponse:
    business_today = _call_business_now(db).date()
    from_day = business_today - timedelta(days=days - 1)
    rows = _build_daily_attendance_report_rows(
        db,
        date_=None,
        from_=from_day,
        to=business_today,
        employee_id=None,
        department=None,
        status=None,
    )
    today_rows = [row for row in rows if row.date == business_today]
    trend_days = _iter_days(from_day, business_today)
    trend_counts = {current_day: 0 for current_day in trend_days}
    for row in rows:
        if row.summary_status != "missing":
            trend_counts[row.date] = trend_counts.get(row.date, 0) + 1

    return AttendanceDashboardSummaryResponse(
        business_timezone=get_effective_runtime_settings(db).business_timezone,
        total_employees=len({row.employee_id for row in today_rows}),
        today=AttendanceDashboardTodaySummary(
            present=sum(1 for row in today_rows if row.summary_status == "present"),
            late=sum(1 for row in today_rows if row.summary_status == "late"),
            absent=sum(1 for row in today_rows if row.summary_status == "missing"),
        ),
        trend=[
            AttendanceDashboardTrendPoint(
                date=current_day,
                check_in_count=trend_counts[current_day],
            )
            for current_day in trend_days
        ],
    )


def delete_attendance_events(db: Session) -> int:
    result = db.execute(delete(AttendanceEvent))
    db.commit()
    _clear_all_camera_match_gates()
    return int(result.rowcount or 0)


def delete_attendance_events_by_ids(db: Session, event_ids: list[int]) -> int:
    unique_ids = sorted(set(event_ids))
    if not unique_ids:
        return 0

    result = db.execute(delete(AttendanceEvent).where(AttendanceEvent.id.in_(unique_ids)))
    db.commit()
    _clear_camera_match_gates_for_event_ids(set(unique_ids))
    return int(result.rowcount or 0)


def _save_unmatched_event(
    db: Session,
    *,
    action_type: AttendanceActionType,
    attendance_status: AttendanceStatus,
    message: str,
    score: float | None,
    captured_at: datetime | None,
    camera_id: str | None,
    record_event: bool,
) -> AttendanceFrameResponse:
    if not record_event:
        return AttendanceFrameResponse(
            matched=False,
            employee=None,
            score=score,
            action_type=action_type,
            attendance_status=attendance_status,
            message=message,
            event_id=None,
        )

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


def _build_daily_attendance_report_rows(
    db: Session,
    *,
    date_: date | None,
    from_: date | None,
    to: date | None,
    employee_id: int | None,
    department: str | None,
    status: AttendanceDailyReportStatus | None,
) -> list[AttendanceDailyReportRead]:
    from_day, to_day = _resolve_report_day_range(
        db,
        date_=date_,
        from_=from_,
        to=to,
    )
    employees = _list_report_employees(
        db,
        employee_id=employee_id,
        department=department,
    )
    if not employees:
        return []

    rows_by_key: dict[tuple[date, int], AttendanceDailyReportRead] = {}
    for current_day in _iter_days(from_day, to_day):
        for employee in employees:
            rows_by_key[(current_day, employee.id)] = AttendanceDailyReportRead(
                date=current_day,
                employee_id=employee.id,
                employee_code=employee.employee_code,
                full_name=employee.full_name,
                department=employee.department,
                first_check_in=None,
                last_check_out=None,
                summary_status="missing",
            )

    event_time = func.coalesce(
        AttendanceEvent.captured_at,
        AttendanceEvent.created_at,
    )
    range_start_utc, range_end_utc = _business_day_range_to_utc_bounds(db, from_day, to_day)
    events = db.scalars(
        select(AttendanceEvent)
        .options(selectinload(AttendanceEvent.employee))
        .where(
            AttendanceEvent.attendance_status == "recorded",
            AttendanceEvent.employee_id.in_([employee.id for employee in employees]),
            event_time >= range_start_utc,
            event_time <= range_end_utc,
        )
        .order_by(event_time.asc(), AttendanceEvent.id.asc())
    ).all()

    for event in events:
        if event.employee is None:
            continue
        event_datetime = _get_business_local_event_datetime(db, event)
        if event_datetime is None:
            continue
        key = (event_datetime.date(), event.employee.id)
        row = rows_by_key.get(key)
        if row is None:
            continue
        if event.action_type == "check_in":
            if row.first_check_in is None or event_datetime < row.first_check_in:
                row.first_check_in = event_datetime
        elif row.last_check_out is None or event_datetime > row.last_check_out:
            row.last_check_out = event_datetime

    rows = []
    for row in rows_by_key.values():
        if row.first_check_in is not None:
            row.summary_status = (
                "late"
                if row.first_check_in.time() > REPORT_LATE_THRESHOLD
                else "present"
            )
        if status is None or row.summary_status == status:
            rows.append(row)

    rows.sort(key=lambda row: (row.date, row.employee_code))
    return rows


def _resolve_report_day_range(
    db: Session,
    *,
    date_: date | None,
    from_: date | None,
    to: date | None,
) -> tuple[date, date]:
    if date_ is not None:
        from_day, to_day = date_, date_
    else:
        today = _call_business_now(db).date()
        from_day = from_ or to or today
        to_day = to or from_ or today
        if from_day > to_day:
            from_day, to_day = to_day, from_day

    day_count = (to_day - from_day).days + 1
    if day_count > MAX_REPORT_DAYS:
        raise AttendanceValidationError(
            f"Report range cannot exceed {MAX_REPORT_DAYS} days."
        )
    return from_day, to_day


def _iter_days(from_day: date, to_day: date) -> list[date]:
    day_count = (to_day - from_day).days + 1
    return [from_day + timedelta(days=index) for index in range(day_count)]


def _list_report_employees(
    db: Session,
    *,
    employee_id: int | None,
    department: str | None,
) -> list[Employee]:
    filters: list = [Employee.status == "active"]
    if employee_id is not None:
        filters.append(Employee.id == employee_id)
    if department and department.strip():
        filters.append(func.lower(Employee.department) == department.strip().lower())

    stmt = select(Employee).where(*filters).order_by(Employee.id.asc())
    return list(db.scalars(stmt).all())


def _build_attendance_filters(
    *,
    employee_id: int | None,
    action_type: AttendanceActionType | None,
    from_: datetime | None,
    to: datetime | None,
) -> list[object]:
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
        filters.append(event_time >= _normalize_utc_naive(from_))

    if to is not None:
        filters.append(event_time <= _normalize_utc_naive(to))

    return filters


def _find_recent_recorded_event(
    db: Session,
    *,
    employee_id: int,
    action_type: AttendanceActionType,
    request_received_at: datetime,
) -> AttendanceEvent | None:
    recent_event = db.scalar(
        select(AttendanceEvent)
        .where(
            AttendanceEvent.employee_id == employee_id,
            AttendanceEvent.action_type == action_type,
            AttendanceEvent.attendance_status == "recorded",
        )
        .order_by(AttendanceEvent.created_at.desc(), AttendanceEvent.id.desc())
        .limit(1)
    )
    if recent_event is None:
        return None

    normalized_request_received_at = _normalize_utc_naive(request_received_at)
    normalized_event_created_at = _normalize_utc_naive(recent_event.created_at)
    if (
        normalized_event_created_at
        <= normalized_request_received_at
        <= normalized_event_created_at + RECORDED_EVENT_DEDUPE_WINDOW
    ):
        return recent_event

    return None


def _find_camera_match_gate_event_id(
    *,
    camera_id: str | None,
    action_type: AttendanceActionType,
    employee_id: int,
    request_received_at: datetime,
) -> int | None:
    normalized = _normalize_camera_id(camera_id)
    if normalized is None:
        return None

    gate = camera_gate_service.get_gate(normalized, str(action_type))
    if gate is None or gate.employee_id != employee_id:
        return None

    # Slide the dedupe window forward on a confirmed re-scan so a continuous
    # presence at the kiosk does not get re-recorded after 5 minutes.
    camera_gate_service.set_gate(
        normalized,
        str(action_type),
        record=camera_gate_service.CameraGateRecord(
            employee_id=gate.employee_id,
            event_id=gate.event_id,
            updated_at=request_received_at,
        ),
    )
    return gate.event_id


def _set_camera_match_gate(
    *,
    camera_id: str | None,
    action_type: AttendanceActionType,
    employee_id: int,
    event_id: int,
    updated_at: datetime,
) -> None:
    normalized = _normalize_camera_id(camera_id)
    if normalized is None:
        return
    camera_gate_service.set_gate(
        normalized,
        str(action_type),
        record=camera_gate_service.CameraGateRecord(
            employee_id=employee_id,
            event_id=event_id,
            updated_at=updated_at,
        ),
    )


def _clear_camera_match_gate(
    *,
    camera_id: str | None,
    action_type: AttendanceActionType,
) -> None:
    normalized = _normalize_camera_id(camera_id)
    if normalized is None:
        return
    camera_gate_service.clear_gate(normalized, str(action_type))


def _clear_all_camera_match_gates() -> None:
    camera_gate_service.clear_all_gates()


def _clear_camera_match_gates_for_event_ids(event_ids: set[int]) -> None:
    camera_gate_service.clear_gates_for_event_ids(event_ids)


def _normalize_camera_id(camera_id: str | None) -> str | None:
    normalized = (camera_id or "").strip()
    return normalized or None


def _build_event_read(db: Session, event: AttendanceEvent) -> AttendanceEventRead:
    employee = (
        AttendanceEmployeeSummary.model_validate(event.employee)
        if event.employee is not None
        else None
    )

    return AttendanceEventRead(
        id=event.id,
        created_at=_get_business_local_datetime(db, event.created_at),
        captured_at=_get_business_local_datetime(db, event.captured_at),
        action_type=event.action_type,
        attendance_status=event.attendance_status,
        score=float(event.score) if event.score is not None else None,
        camera_id=event.camera_id,
        snapshot_object_key=event.snapshot_object_key,
        employee=employee,
    )


def _action_label(action_type: AttendanceActionType) -> str:
    return "Check-in" if action_type == "check_in" else "Check-out"


def _analyze_image_bytes(
    image_bytes: bytes,
    runtime_settings: object,
) -> dict[str, object]:
    parameters = inspect.signature(analyze_image_bytes).parameters
    if len(parameters) == 1:
        return analyze_image_bytes(image_bytes)
    return analyze_image_bytes(image_bytes, runtime_settings)


def _normalize_utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _get_business_local_datetime(db: Session, value: datetime | None) -> datetime | None:
    normalized_value = _normalize_utc_naive(value)
    if normalized_value is None:
        return None
    runtime_settings = get_effective_runtime_settings(db)
    business_timezone = get_business_timezone(runtime_settings.business_timezone)
    aware_utc = normalized_value.replace(tzinfo=timezone.utc)
    return aware_utc.astimezone(business_timezone).replace(tzinfo=None)


def _get_business_local_event_datetime(
    db: Session,
    event: AttendanceEvent,
) -> datetime | None:
    return _get_business_local_datetime(db, event.captured_at or event.created_at)


def _business_day_range_to_utc_bounds(
    db: Session,
    from_day: date,
    to_day: date,
) -> tuple[datetime, datetime]:
    runtime_settings = get_effective_runtime_settings(db)
    business_timezone = get_business_timezone(runtime_settings.business_timezone)
    start_local = datetime.combine(from_day, time.min, tzinfo=business_timezone)
    end_local = datetime.combine(to_day, time.max, tzinfo=business_timezone)
    return (
        start_local.astimezone(timezone.utc).replace(tzinfo=None),
        end_local.astimezone(timezone.utc).replace(tzinfo=None),
    )


def _business_now(db: Session) -> datetime:
    runtime_settings = get_effective_runtime_settings(db)
    business_timezone = get_business_timezone(runtime_settings.business_timezone)
    return datetime.now(timezone.utc).astimezone(business_timezone).replace(tzinfo=None)


def _call_business_now(db: Session) -> datetime:
    parameters = inspect.signature(_business_now).parameters
    if len(parameters) == 0:
        return _business_now()  # type: ignore[call-arg]
    return _business_now(db)
