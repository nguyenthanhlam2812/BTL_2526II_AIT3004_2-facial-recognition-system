from __future__ import annotations

from fastapi import HTTPException, UploadFile, status


ALLOWED_IMAGE_CONTENT_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)
MAX_IMAGE_BYTES: int = 5 * 1024 * 1024  # 5 MiB


def ensure_image_mime(content_type: str | None) -> None:
    """Reject uploads whose declared Content-Type is not in the allow-list."""
    if not content_type or content_type.split(";", 1)[0].strip() not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported image type. Allowed: image/jpeg, image/png, image/webp.",
        )


def ensure_image_size_bytes(size_bytes: int, *, max_bytes: int = MAX_IMAGE_BYTES) -> None:
    """Reject uploads whose payload exceeds the configured size cap."""
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image too large. Maximum allowed is {max_bytes // 1024} KB.",
        )


def read_validated_image(upload: UploadFile, *, max_bytes: int = MAX_IMAGE_BYTES) -> bytes:
    """Validate MIME + size and return the upload bytes ready for processing."""
    ensure_image_mime(upload.content_type)
    data = upload.file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image file is empty.",
        )
    ensure_image_size_bytes(len(data), max_bytes=max_bytes)
    return data
