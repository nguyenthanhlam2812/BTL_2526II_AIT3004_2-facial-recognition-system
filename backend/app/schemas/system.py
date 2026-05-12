from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RedisConnectionInfo(BaseModel):
    scheme: str
    host: str
    port: int | None
    database: int | None


class SystemSettingFieldMeta(BaseModel):
    key: str
    value: float | bool | str
    source: Literal["env", "db"]
    editable: bool
    value_type: Literal["float", "boolean", "enum"]
    requires_restart: bool = False
    min_value: float | None = None
    max_value: float | None = None
    allowed_values: list[str] | None = None


class SystemSettingsResponse(BaseModel):
    environment: str
    api_prefix: str
    business_timezone: str
    attendance_threshold: float
    insightface_model_name: str
    face_min_det_score: float
    face_min_area_ratio: float
    face_secondary_area_ratio: float
    warmup_face_model: bool
    qdrant_url: str
    qdrant_collection_employee_faces: str
    minio_endpoint: str
    redis: RedisConnectionInfo
    fields: list[SystemSettingFieldMeta] = Field(default_factory=list)


class SystemSettingsUpdate(BaseModel):
    attendance_threshold: float | None = Field(default=None, gt=0.0, le=1.0)
    face_min_det_score: float | None = Field(default=None, ge=0.0, le=1.0)
    face_min_area_ratio: float | None = Field(default=None, ge=0.001, le=0.5)
    face_secondary_area_ratio: float | None = Field(default=None, ge=0.05, le=1.0)
    business_timezone: Literal["UTC", "Asia/Bangkok", "Asia/Ho_Chi_Minh"] | None = None
    warmup_face_model: bool | None = None


class SystemSettingsResetRequest(BaseModel):
    keys: list[str] | None = None
