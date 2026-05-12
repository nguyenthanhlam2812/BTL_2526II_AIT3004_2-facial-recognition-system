from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EmployeeStatus = Literal["active", "inactive"]
EmployeeFaceDataStatus = Literal["missing", "pending", "enrolled", "failed"]


class EmployeeBase(BaseModel):
    employee_code: str = Field(min_length=1, max_length=32)
    full_name: str = Field(min_length=1, max_length=255)
    department: str = Field(min_length=1, max_length=128)
    position: str = Field(min_length=1, max_length=128)
    status: EmployeeStatus = "active"


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
