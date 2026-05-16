from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EnrollmentCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: int
    job_id: str
    status: str
    uploaded_count: int


class EnrollmentStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    employee_id: int
    status: str
    message: str | None
    processed_count: int
    failed_count: int
