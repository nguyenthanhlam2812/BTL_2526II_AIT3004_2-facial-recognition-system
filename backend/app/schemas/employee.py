from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.schemas.validation import normalize_business_text, normalize_employee_code


EmployeeStatus = Literal["active", "inactive"]
EmployeeFaceDataStatus = Literal["missing", "pending", "enrolled", "failed"]


class EmployeeBase(BaseModel):
    employee_code: str = Field(min_length=2, max_length=32)
    full_name: str = Field(min_length=2, max_length=100)
    department: str = Field(min_length=2, max_length=64)
    position: str = Field(min_length=2, max_length=64)
    status: EmployeeStatus = "active"

    @field_validator("employee_code", mode="before")
    @classmethod
    def validate_employee_code(cls, value: str) -> str:
        return normalize_employee_code(value)

    @field_validator("full_name", mode="before")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        return normalize_business_text(
            value,
            field_label="Full name",
            min_length=2,
            max_length=100,
        )

    @field_validator("department", mode="before")
    @classmethod
    def validate_department(cls, value: str) -> str:
        return normalize_business_text(
            value,
            field_label="Department",
            min_length=2,
            max_length=64,
        )

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, value: str) -> str:
        return normalize_business_text(
            value,
            field_label="Position",
            min_length=2,
            max_length=64,
        )


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(EmployeeBase):
    pass


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    face_data_status: EmployeeFaceDataStatus
    created_at: datetime
    updated_at: datetime


class EmployeeListResponse(BaseModel):
    items: list[EmployeeRead]
    total: int


class DeleteResponse(BaseModel):
    ok: bool
