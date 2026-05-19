from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.models.employee import Employee
from backend.app.models.enrollment import Enrollment
from backend.app.models.enrollment_image import EnrollmentImage
from backend.app.services.face_analyzer import analyze_image_bytes
from backend.app.services.minio_service import (
    ObjectStorageError,
    delete_objects,
    ensure_bucket_exists,
    upload_object_bytes,
)
from backend.app.services.queue_service import (
    QueueUnavailableError,
    enqueue_enrollment_job,
)
from backend.app.services.qdrant_service import (
    VectorStoreError,
    find_duplicate_face_owner,
)


class EmployeeNotFoundError(Exception):
    pass


class InvalidEnrollmentFilesError(Exception):
    pass


class EnrollmentInfrastructureError(Exception):
    pass


class DuplicateFaceEnrollmentError(Exception):
    def __init__(self, employee_id: int, score: float) -> None:
        self.employee_id = employee_id
        self.score = score
        super().__init__(
            f"Khuôn mặt đã được đăng ký cho nhân viên #{employee_id} "
            f"(độ trùng khớp {score:.2f}). Hệ thống từ chối đăng ký mới."
        )


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def create_enrollment(
    db: Session,
    employee_id: int,
    files: list[UploadFile],
) -> Enrollment:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise EmployeeNotFoundError

    validate_enrollment_files(files)
    _check_enrollment_for_duplicates(files, employee_id)

    job_id = f"job_{uuid4().hex[:12]}"
    settings = get_settings()
    prepared_files = build_prepared_files(files, job_id)
    uploaded_object_keys: list[str] = []

    try:
        ensure_bucket_exists(settings.minio_bucket_enrollments)
        for prepared_file in prepared_files:
            upload_object_bytes(
                settings.minio_bucket_enrollments,
                prepared_file["object_key"],
                prepared_file["content"],
                prepared_file["content_type"],
            )
            uploaded_object_keys.append(prepared_file["object_key"])
    except ObjectStorageError as exc:
        delete_objects(settings.minio_bucket_enrollments, uploaded_object_keys)
        raise EnrollmentInfrastructureError(
            "Enrollment storage is unavailable."
        ) from exc

    enrollment = Enrollment(
        job_id=job_id,
        employee_id=employee_id,
        status="pending",
        uploaded_count=len(prepared_files),
        processed_count=0,
        failed_count=0,
        message="Enrollment stored. Waiting for worker.",
    )
    try:
        db.add(enrollment)
        db.flush()

        for prepared_file in prepared_files:
            image = EnrollmentImage(
                enrollment_id=enrollment.id,
                object_key=prepared_file["object_key"],
                original_file_name=prepared_file["original_name"],
                content_type=prepared_file["content_type"],
                sort_order=prepared_file["sort_order"],
                processing_status="pending",
            )
            db.add(image)

        db.commit()
        db.refresh(enrollment)
    except Exception:
        db.rollback()
        delete_objects(settings.minio_bucket_enrollments, uploaded_object_keys)
        raise

    try:
        enqueue_enrollment_job(
            {
                "job_id": enrollment.job_id,
                "employee_id": enrollment.employee_id,
                "bucket_name": settings.minio_bucket_enrollments,
                "object_keys": [item["object_key"] for item in prepared_files],
                "uploaded_count": enrollment.uploaded_count,
            }
        )
    except QueueUnavailableError as exc:
        db.delete(enrollment)
        db.commit()
        delete_objects(settings.minio_bucket_enrollments, uploaded_object_keys)
        raise EnrollmentInfrastructureError(
            "Enrollment queue is unavailable."
        ) from exc

    return enrollment


def get_enrollment_by_job_id(db: Session, job_id: str) -> Enrollment | None:
    stmt = select(Enrollment).where(Enrollment.job_id == job_id)
    return db.scalar(stmt)


def build_prepared_files(
    files: list[UploadFile],
    job_id: str,
) -> list[dict[str, str | bytes | int]]:
    prepared_files: list[dict[str, str | bytes | int]] = []
    for index, file in enumerate(files, start=1):
        original_name = file.filename or f"image_{index}.jpg"
        safe_name = build_safe_filename(original_name, index)
        prepared_files.append(
            {
                "original_name": original_name,
                "object_key": f"enrollments/{job_id}/{index:02d}_{safe_name}",
                "content_type": file.content_type or "application/octet-stream",
                "content": file.file.read(),
                "sort_order": index,
            }
        )

    return prepared_files


def validate_enrollment_files(files: list[UploadFile]) -> None:
    if not files:
        raise InvalidEnrollmentFilesError("At least 1 image is required.")

    if len(files) > 5:
        raise InvalidEnrollmentFilesError("Maximum 5 images are allowed.")

    for file in files:
        if file.filename is None or not file.filename.strip():
            raise InvalidEnrollmentFilesError("Each file must have a filename.")

        if not is_image_file(file):
            raise InvalidEnrollmentFilesError(
                f"File '{file.filename}' is not a supported image."
            )


def _check_enrollment_for_duplicates(
    files: list[UploadFile],
    employee_id: int,
) -> None:
    threshold = get_settings().duplicate_enroll_threshold
    for f in files:
        image_bytes = f.file.read()
        f.file.seek(0)

        result = analyze_image_bytes(image_bytes)
        if result["status"] != "success":
            continue

        try:
            duplicate = find_duplicate_face_owner(
                embedding=result["embedding"],
                exclude_employee_id=employee_id,
                threshold=threshold,
            )
        except VectorStoreError:
            return  # Qdrant unavailable → fail open, worker guard is the real gate

        if duplicate is not None:
            raise DuplicateFaceEnrollmentError(
                employee_id=duplicate.employee_id,
                score=duplicate.score,
            )


def is_image_file(file: UploadFile) -> bool:
    if file.content_type and file.content_type.startswith("image/"):
        return True

    extension = Path(file.filename or "").suffix.lower()
    return extension in ALLOWED_IMAGE_EXTENSIONS


def build_safe_filename(filename: str, index: int) -> str:
    fallback = f"image_{index}.jpg"
    safe_name = Path(filename).name.strip() or fallback
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)
    return safe_name or fallback
