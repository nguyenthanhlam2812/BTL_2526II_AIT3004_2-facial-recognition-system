from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.config import SUPPORTED_BUSINESS_TIMEZONES, Settings, get_settings
from backend.app.models.system_setting import SystemSetting
from backend.app.schemas.system import (
    RedisConnectionInfo,
    SystemSettingFieldMeta,
    SystemSettingsResponse,
    SystemSettingsUpdate,
)


SettingValue = float | bool | str
SettingSource = Literal["env", "db"]


@dataclass(frozen=True)
class SettingDefinition:
    key: str
    value_type: Literal["float", "boolean", "enum"]
    env_attr: str
    min_value: float | None = None
    max_value: float | None = None
    allowed_values: tuple[str, ...] | None = None
    requires_restart: bool = False


@dataclass(frozen=True)
class EffectiveRuntimeSettings:
    business_timezone: str
    attendance_threshold: float
    face_min_det_score: float
    face_min_area_ratio: float
    face_secondary_area_ratio: float
    warmup_face_model: bool


EDITABLE_SETTINGS: dict[str, SettingDefinition] = {
    "attendance_threshold": SettingDefinition(
        key="attendance_threshold",
        value_type="float",
        env_attr="attendance_threshold",
        min_value=0.0,
        max_value=1.0,
    ),
    "face_min_det_score": SettingDefinition(
        key="face_min_det_score",
        value_type="float",
        env_attr="face_min_det_score",
        min_value=0.0,
        max_value=1.0,
    ),
    "face_min_area_ratio": SettingDefinition(
        key="face_min_area_ratio",
        value_type="float",
        env_attr="face_min_area_ratio",
        min_value=0.001,
        max_value=0.5,
    ),
    "face_secondary_area_ratio": SettingDefinition(
        key="face_secondary_area_ratio",
        value_type="float",
        env_attr="face_secondary_area_ratio",
        min_value=0.05,
        max_value=1.0,
    ),
    "business_timezone": SettingDefinition(
        key="business_timezone",
        value_type="enum",
        env_attr="business_timezone",
        allowed_values=tuple(sorted(SUPPORTED_BUSINESS_TIMEZONES)),
    ),
    "warmup_face_model": SettingDefinition(
        key="warmup_face_model",
        value_type="boolean",
        env_attr="warmup_face_model",
        requires_restart=True,
    ),
}


class SystemSettingsValidationError(ValueError):
    pass


def get_effective_runtime_settings(db: Session) -> EffectiveRuntimeSettings:
    values = _get_effective_values(db)
    return EffectiveRuntimeSettings(
        business_timezone=str(values["business_timezone"][0]),
        attendance_threshold=float(values["attendance_threshold"][0]),
        face_min_det_score=float(values["face_min_det_score"][0]),
        face_min_area_ratio=float(values["face_min_area_ratio"][0]),
        face_secondary_area_ratio=float(values["face_secondary_area_ratio"][0]),
        warmup_face_model=bool(values["warmup_face_model"][0]),
    )


def build_system_settings_response(db: Session) -> SystemSettingsResponse:
    settings = get_settings()
    values = _get_effective_values(db)
    runtime = get_effective_runtime_settings(db)

    return SystemSettingsResponse(
        environment=settings.environment,
        api_prefix=settings.api_prefix,
        business_timezone=runtime.business_timezone,
        attendance_threshold=runtime.attendance_threshold,
        insightface_model_name=settings.insightface_model_name,
        face_min_det_score=runtime.face_min_det_score,
        face_min_area_ratio=runtime.face_min_area_ratio,
        face_secondary_area_ratio=runtime.face_secondary_area_ratio,
        warmup_face_model=runtime.warmup_face_model,
        qdrant_url=settings.qdrant_url,
        qdrant_collection_employee_faces=settings.qdrant_collection_employee_faces,
        minio_endpoint=settings.minio_endpoint,
        redis=_parse_redis_url(settings.redis_url),
        fields=[
            _build_field_meta(definition, values[definition.key][0], values[definition.key][1])
            for definition in EDITABLE_SETTINGS.values()
        ],
    )


def update_system_settings(
    db: Session,
    payload: SystemSettingsUpdate,
    *,
    updated_by_user_id: int,
) -> SystemSettingsResponse:
    values = payload.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in values.items():
        definition = _get_definition(key)
        parsed = _validate_value(definition, value)
        setting = db.get(SystemSetting, key)
        if setting is None:
            setting = SystemSetting(key=key, value=_serialize_value(parsed))
        else:
            setting.value = _serialize_value(parsed)
        setting.updated_by_user_id = updated_by_user_id
        db.add(setting)

    db.commit()
    return build_system_settings_response(db)


def reset_system_settings(
    db: Session,
    *,
    keys: list[str] | None,
) -> SystemSettingsResponse:
    target_keys = keys or list(EDITABLE_SETTINGS)
    invalid = sorted(set(target_keys) - set(EDITABLE_SETTINGS))
    if invalid:
        raise SystemSettingsValidationError(
            f"Unsupported setting key(s): {', '.join(invalid)}."
        )

    db.execute(delete(SystemSetting).where(SystemSetting.key.in_(target_keys)))
    db.commit()
    return build_system_settings_response(db)


def _get_effective_values(db: Session) -> dict[str, tuple[SettingValue, SettingSource]]:
    settings = get_settings()
    rows = {
        row.key: row.value
        for row in db.scalars(select(SystemSetting).where(SystemSetting.key.in_(EDITABLE_SETTINGS)))
    }

    values: dict[str, tuple[SettingValue, SettingSource]] = {}
    for key, definition in EDITABLE_SETTINGS.items():
        if key in rows:
            values[key] = (_validate_value(definition, _deserialize_value(rows[key])), "db")
        else:
            values[key] = (_validate_value(definition, getattr(settings, definition.env_attr)), "env")
    return values


def _build_field_meta(
    definition: SettingDefinition,
    value: SettingValue,
    source: SettingSource,
) -> SystemSettingFieldMeta:
    return SystemSettingFieldMeta(
        key=definition.key,
        value=value,
        source=source,
        editable=True,
        value_type=definition.value_type,
        requires_restart=definition.requires_restart,
        min_value=definition.min_value,
        max_value=definition.max_value,
        allowed_values=list(definition.allowed_values) if definition.allowed_values else None,
    )


def _get_definition(key: str) -> SettingDefinition:
    try:
        return EDITABLE_SETTINGS[key]
    except KeyError as exc:
        raise SystemSettingsValidationError(f"Unsupported setting key: {key}.") from exc


def _validate_value(definition: SettingDefinition, value: object) -> SettingValue:
    if definition.value_type == "boolean":
        if not isinstance(value, bool):
            raise SystemSettingsValidationError(f"{definition.key} must be a boolean.")
        return value

    if definition.value_type == "enum":
        text = str(value)
        if definition.allowed_values and text not in definition.allowed_values:
            allowed = ", ".join(definition.allowed_values)
            raise SystemSettingsValidationError(
                f"{definition.key} must be one of: {allowed}."
            )
        return text

    number = float(value)
    if definition.min_value is not None and number < definition.min_value:
        raise SystemSettingsValidationError(
            f"{definition.key} must be >= {definition.min_value}."
        )
    if definition.key == "attendance_threshold" and number <= 0.0:
        raise SystemSettingsValidationError("attendance_threshold must be > 0.0.")
    if definition.max_value is not None and number > definition.max_value:
        raise SystemSettingsValidationError(
            f"{definition.key} must be <= {definition.max_value}."
        )
    return number


def _serialize_value(value: SettingValue) -> str:
    return json.dumps(value)


def _deserialize_value(value: str) -> SettingValue:
    parsed = json.loads(value)
    if isinstance(parsed, (str, bool, int, float)):
        return parsed
    raise SystemSettingsValidationError("Stored setting value has an unsupported type.")


def _parse_redis_url(redis_url: str) -> RedisConnectionInfo:
    from urllib.parse import urlparse

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
