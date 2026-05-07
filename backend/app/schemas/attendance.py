from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


AttendanceActionType = Literal["check_in", "check_out"]
AttendanceStatus = Literal["recorded", "unknown_face", "multiple_faces"]


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
    event_id: int


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
