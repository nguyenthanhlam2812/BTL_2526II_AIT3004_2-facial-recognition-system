from __future__ import annotations

from datetime import timedelta, timezone
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_SEED_ADMIN_USERNAME = "admin"
DEFAULT_SEED_ADMIN_PASSWORD = "admin123"
DEFAULT_JWT_SECRET_KEY = "change-me"
DEFAULT_KIOSK_API_TOKEN = "local-kiosk-token"
DEFAULT_BUSINESS_TIMEZONE = "Asia/Ho_Chi_Minh"
SUPPORTED_BUSINESS_TIMEZONES = {
    "UTC": timezone.utc,
    "Asia/Bangkok": timezone(timedelta(hours=7), name="Asia/Bangkok"),
    "Asia/Ho_Chi_Minh": timezone(timedelta(hours=7), name="Asia/Ho_Chi_Minh"),
}


class RuntimeConfigurationError(RuntimeError):
    pass


class Settings(BaseSettings):
    app_name: str = Field(default="AI Facial Recognition Backend")
    environment: str = Field(default="development")
    debug: bool = Field(default=True)
    api_prefix: str = Field(default="/api")

    jwt_secret_key: str = Field(default=DEFAULT_JWT_SECRET_KEY)
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60)

    seed_admin_username: str = Field(default=DEFAULT_SEED_ADMIN_USERNAME)
    seed_admin_password: str = Field(default=DEFAULT_SEED_ADMIN_PASSWORD)
    kiosk_api_token: str = Field(default=DEFAULT_KIOSK_API_TOKEN)
    public_demo_mode: bool = Field(default=False)
    business_timezone: str = Field(default=DEFAULT_BUSINESS_TIMEZONE)

    mysql_host: str = Field(default="127.0.0.1")
    mysql_port: int = Field(default=3306)
    mysql_database: str = Field(default="face_attendance")
    mysql_user: str = Field(default="app")
    mysql_password: str = Field(default="app_password")
    mysql_root_password: str = Field(default="root_password")
    mysql_charset: str = Field(default="utf8mb4")

    redis_url: str = Field(default="redis://127.0.0.1:6379/0")
    enrollment_queue: str = Field(default="enrollment")
    rate_limit_storage_uri: str | None = Field(default=None)

    minio_endpoint: str = Field(default="127.0.0.1:9000")
    minio_access_key: str = Field(default="minioadmin")
    minio_secret_key: str = Field(default="minioadmin")
    minio_secure: bool = Field(default=False)
    minio_bucket_enrollments: str = Field(default="enrollments")
    minio_bucket_snapshots: str = Field(default="snapshots")

    qdrant_url: str = Field(default="http://127.0.0.1:6333")
    attendance_threshold: float = Field(default=0.3)
    duplicate_enroll_threshold: float = Field(default=0.6)
    insightface_model_name: str = Field(default="buffalo_l")
    qdrant_collection_employee_faces: str = Field(default="employee_faces")
    face_min_det_score: float = Field(default=0.5)
    face_min_area_ratio: float = Field(default=0.015)
    face_secondary_area_ratio: float = Field(default=0.35)
    warmup_face_model: bool = Field(default=False)


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def model_post_init(self, _context) -> None:
        if not self.rate_limit_storage_uri:
            object.__setattr__(self, "rate_limit_storage_uri", self.redis_url)

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset={self.mysql_charset}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_business_timezone(name: str) -> timezone:
    try:
        return SUPPORTED_BUSINESS_TIMEZONES[name]
    except KeyError as exc:
        supported = ", ".join(sorted(SUPPORTED_BUSINESS_TIMEZONES))
        raise RuntimeConfigurationError(
            f"Unsupported BUSINESS_TIMEZONE '{name}'. Supported values: {supported}."
        ) from exc


def validate_runtime_settings(settings: Settings) -> None:
    get_business_timezone(settings.business_timezone)

    if not settings.public_demo_mode:
        return

    if settings.seed_admin_password == DEFAULT_SEED_ADMIN_PASSWORD:
        raise RuntimeConfigurationError(
            "PUBLIC_DEMO_MODE requires SEED_ADMIN_PASSWORD to be changed from the default value."
        )

    if settings.jwt_secret_key == DEFAULT_JWT_SECRET_KEY:
        raise RuntimeConfigurationError(
            "PUBLIC_DEMO_MODE requires JWT_SECRET_KEY to be changed from the default value."
        )

    if not settings.kiosk_api_token.strip() or settings.kiosk_api_token == DEFAULT_KIOSK_API_TOKEN:
        raise RuntimeConfigurationError(
            "PUBLIC_DEMO_MODE requires KIOSK_API_TOKEN to be changed from the default value."
        )
