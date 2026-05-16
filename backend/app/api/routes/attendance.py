from datetime import date, datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status as http_status,
)
from sqlalchemy.orm import Session

from backend.app.api.deps import require_admin, require_kiosk_token, require_operator
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.rate_limit import limiter
from backend.app.schemas.attendance import (
    AttendanceActionType,
    AttendanceDailyReportListResponse,
    AttendanceDailyReportStatus,
    AttendanceDashboardSummaryResponse,
    AttendanceEventsBulkDeleteRequest,
    AttendanceEventsDeleteResponse,
    AttendanceEventListResponse,
    AttendanceFrameResponse,
)
from backend.app.services.attendance_service import (
    AttendanceInfrastructureError,
    AttendanceValidationError,
    delete_attendance_events as delete_attendance_events_service,
    delete_attendance_events_by_ids as delete_attendance_events_by_ids_service,
    export_daily_attendance_reports_csv as export_daily_attendance_reports_csv_service,
    export_attendance_events_csv as export_attendance_events_csv_service,
    get_attendance_dashboard_summary as get_attendance_dashboard_summary_service,
    list_daily_attendance_reports as list_daily_attendance_reports_service,
    list_attendance_events as list_attendance_events_service,
    recognize_attendance_frame as recognize_attendance_frame_service,
)

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/frame", response_model=AttendanceFrameResponse)
@limiter.limit("10/second")
def recognize_attendance_frame(
    request: Request,
    response: Response,
    image: UploadFile = File(...),
    action_type: AttendanceActionType = Form(...),
    captured_at: datetime | None = Form(default=None),
    camera_id: str | None = Form(default=None),
    record_unmatched: bool = Form(default=True),
    _: None = Depends(require_kiosk_token),
    db: Session = Depends(get_db),
) -> AttendanceFrameResponse:
    image_bytes = image.file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Image file is empty.",
        )

    try:
        return recognize_attendance_frame_service(
            db,
            image_bytes=image_bytes,
            action_type=action_type,
            captured_at=captured_at,
            camera_id=camera_id,
            record_unmatched=record_unmatched,
        )
    except AttendanceInfrastructureError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
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


@router.get("/reports/daily", response_model=AttendanceDailyReportListResponse)
def list_daily_attendance_reports(
    date_: date | None = Query(default=None, alias="date"),
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
    employee_id: int | None = Query(default=None),
    department: str | None = Query(default=None),
    status: AttendanceDailyReportStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AttendanceDailyReportListResponse:
    try:
        return list_daily_attendance_reports_service(
            db,
            date_=date_,
            from_=from_,
            to=to,
            employee_id=employee_id,
            department=department,
            status=status,
            page=page,
            page_size=page_size,
        )
    except AttendanceValidationError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/reports/daily/export.csv")
def export_daily_attendance_reports_csv(
    date_: date | None = Query(default=None, alias="date"),
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
    employee_id: int | None = Query(default=None),
    department: str | None = Query(default=None),
    status: AttendanceDailyReportStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Response:
    try:
        csv_content = export_daily_attendance_reports_csv_service(
            db,
            date_=date_,
            from_=from_,
            to=to,
            employee_id=employee_id,
            department=department,
            status=status,
        )
    except AttendanceValidationError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return Response(
        content="\ufeff" + csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="attendance-daily-report.csv"'
        },
    )


@router.get("/reports/dashboard-summary", response_model=AttendanceDashboardSummaryResponse)
def get_attendance_dashboard_summary(
    days: int = Query(default=7, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AttendanceDashboardSummaryResponse:
    if days not in {7, 30}:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Dashboard summary supports only 7 or 30 days.",
        )
    return get_attendance_dashboard_summary_service(db, days=days)


@router.get("/events/export.csv")
def export_attendance_events_csv(
    employee_id: int | None = Query(default=None),
    action_type: AttendanceActionType | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Response:
    try:
        csv_content = export_attendance_events_csv_service(
            db,
            employee_id=employee_id,
            action_type=action_type,
            from_=from_,
            to=to,
        )
    except AttendanceValidationError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return Response(
        content="\ufeff" + csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="attendance-events.csv"'
        },
    )


@router.delete("/events/selected", response_model=AttendanceEventsDeleteResponse)
def delete_selected_attendance_events(
    payload: AttendanceEventsBulkDeleteRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_operator),
) -> AttendanceEventsDeleteResponse:
    deleted_count = delete_attendance_events_by_ids_service(db, payload.ids)
    return AttendanceEventsDeleteResponse(ok=True, deleted_count=deleted_count)


@router.delete("/events", response_model=AttendanceEventsDeleteResponse)
def delete_attendance_events(
    db: Session = Depends(get_db),
    _: User = Depends(require_operator),
) -> AttendanceEventsDeleteResponse:
    deleted_count = delete_attendance_events_service(db)
    return AttendanceEventsDeleteResponse(ok=True, deleted_count=deleted_count)
