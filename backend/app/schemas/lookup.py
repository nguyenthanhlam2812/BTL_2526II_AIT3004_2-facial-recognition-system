from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.schemas.validation import normalize_business_text


class LookupItemCreate(BaseModel):
    """Schema for creating a department or position."""

    name: str = Field(min_length=2, max_length=64)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return normalize_business_text(
            value,
            field_label="Tên",
            min_length=2,
            max_length=64,
        )


class LookupItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class LookupItemListResponse(BaseModel):
    items: list[LookupItemRead]
    total: int
