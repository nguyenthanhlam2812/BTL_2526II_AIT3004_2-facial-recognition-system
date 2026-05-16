from __future__ import annotations

from pydantic import BaseModel


class RedisConnectionInfo(BaseModel):
    scheme: str
    host: str
    port: int | None
    database: int | None


class SystemSettingsResponse(BaseModel):
    environment: str
    api_prefix: str
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
