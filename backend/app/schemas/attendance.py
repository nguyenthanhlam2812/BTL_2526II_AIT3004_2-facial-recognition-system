from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AttendanceActionType = Literal["check_in", "check_out"]
AttendanceStatus = Literal["recorded", "unknown_face", "multiple_faces"]
AttendanceDailyReportStatus = Literal["present", "late", "missing"]


class AttendanceEmployeeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    full_name: str


class AttendanceFrameResponse(BaseModel):
    matched: bool
    employee: AttendanceEmployeeSummary | None
    score: float | None
    action_type: AttendanceActionType
    attendance_status: AttendanceStatus
    message: str
    event_id: int | None


class AttendanceEventRead(BaseModel):
    id: int
    created_at: datetime
    captured_at: datetime | None
    action_type: AttendanceActionType
    attendance_status: AttendanceStatus
    score: float | None
    camera_id: str | None
    snapshot_object_key: str | None
    employee: AttendanceEmployeeSummary | None


class AttendanceEventListResponse(BaseModel):
    items: list[AttendanceEventRead]
    total: int


class AttendanceEventsDeleteResponse(BaseModel):
    ok: bool
    deleted_count: int


class AttendanceEventsBulkDeleteRequest(BaseModel):
    ids: list[int] = Field(min_length=1)


class AttendanceDailyReportRead(BaseModel):
    date: date
    employee_id: int
    employee_code: str
    full_name: str
    department: str
    first_check_in: datetime | None
    last_check_out: datetime | None
    summary_status: AttendanceDailyReportStatus


class AttendanceDailyReportListResponse(BaseModel):
    items: list[AttendanceDailyReportRead]
    total: int


class AttendanceDashboardTrendPoint(BaseModel):
    date: date
    check_in_count: int


class AttendanceDashboardTodaySummary(BaseModel):
    present: int
    late: int
    absent: int


class AttendanceDashboardSummaryResponse(BaseModel):
    business_timezone: str
    total_employees: int
    today: AttendanceDashboardTodaySummary
    trend: list[AttendanceDashboardTrendPoint]
