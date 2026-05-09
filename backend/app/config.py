from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="AI Facial Recognition Backend")
    environment: str = Field(default="development")
    debug: bool = Field(default=True)
    api_prefix: str = Field(default="/api")

    jwt_secret_key: str = Field(default="change-me")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60)


    mysql_host: str = Field(default="127.0.0.1")
    mysql_port: int = Field(default=3306)
    mysql_database: str = Field(default="face_attendance")
    mysql_user: str = Field(default="app")
    mysql_password: str = Field(default="app_password")
    mysql_root_password: str = Field(default="root_password")
    mysql_charset: str = Field(default="utf8mb4")

    redis_url: str = Field(default="redis://127.0.0.1:6379/0")
    enrollment_queue: str = Field(default="enrollment")

    minio_endpoint: str = Field(default="127.0.0.1:9000")
    minio_access_key: str = Field(default="minioadmin")
    minio_secret_key: str = Field(default="minioadmin")
    minio_secure: bool = Field(default=False)
    minio_bucket_enrollments: str = Field(default="enrollments")
    minio_bucket_snapshots: str = Field(default="snapshots")

    qdrant_url: str = Field(default="http://127.0.0.1:6333")
    attendance_threshold: float = Field(default=0.3)
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
