from __future__ import annotations

from io import BytesIO

from minio import Minio
from minio.error import MinioException

from backend.app.config import get_settings


class ObjectStorageError(Exception):
    pass


def get_minio_client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket_exists(bucket_name: str) -> None:
    client = get_minio_client()
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
    except MinioException as exc:
        raise ObjectStorageError(f"Cannot access bucket '{bucket_name}'.") from exc


def upload_object_bytes(
    bucket_name: str,
    object_key: str,
    content: bytes,
    content_type: str,
) -> None:
    client = get_minio_client()
    try:
        client.put_object(
            bucket_name,
            object_key,
            BytesIO(content),
            length=len(content),
            content_type=content_type,
        )
    except MinioException as exc:
        raise ObjectStorageError(f"Cannot upload object '{object_key}'.") from exc


def delete_objects(bucket_name: str, object_keys: list[str]) -> None:
    client = get_minio_client()
    for object_key in object_keys:
        try:
            client.remove_object(bucket_name, object_key)
        except MinioException:
            # Cleanup is best-effort only.
            continue
