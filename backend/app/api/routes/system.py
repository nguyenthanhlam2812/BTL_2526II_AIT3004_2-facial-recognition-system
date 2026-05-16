from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends

from backend.app.api.deps import require_admin
from backend.app.config import get_settings
from backend.app.models.user import User
from backend.app.schemas.system import RedisConnectionInfo, SystemSettingsResponse


router = APIRouter(prefix="/system", tags=["system"])


def _parse_redis_url(redis_url: str) -> RedisConnectionInfo:
    parsed = urlparse(redis_url)

    database: int | None = None
    if parsed.path and parsed.path != "/":
        try:
            database = int(parsed.path.lstrip("/").split("/", maxsplit=1)[0])
        except ValueError:
            database = None

    return RedisConnectionInfo(
        scheme=parsed.scheme or "redis",
        host=parsed.hostname or "",
        port=parsed.port,
        database=database,
    )


@router.get("/settings", response_model=SystemSettingsResponse)
def get_system_settings(
    _: User = Depends(require_admin),
) -> SystemSettingsResponse:
    settings = get_settings()

    return SystemSettingsResponse(
        environment=settings.environment,
        api_prefix=settings.api_prefix,
        attendance_threshold=settings.attendance_threshold,
        insightface_model_name=settings.insightface_model_name,
        face_min_det_score=settings.face_min_det_score,
        face_min_area_ratio=settings.face_min_area_ratio,
        face_secondary_area_ratio=settings.face_secondary_area_ratio,
        warmup_face_model=settings.warmup_face_model,
        qdrant_url=settings.qdrant_url,
        qdrant_collection_employee_faces=settings.qdrant_collection_employee_faces,
        minio_endpoint=settings.minio_endpoint,
        redis=_parse_redis_url(settings.redis_url),
    )
