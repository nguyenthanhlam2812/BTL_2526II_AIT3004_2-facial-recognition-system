from __future__ import annotations

from datetime import datetime
import inspect
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.config import get_settings
from backend.app.db.session import SessionLocal
from backend.app.models.enrollment import Enrollment
from backend.app.services.minio_service import (
    ObjectStorageError,
    download_object_bytes,
)
from backend.app.services.system_settings_service import get_effective_runtime_settings
from worker.app.face_analyzer import analyze_image_bytes

from backend.app.services.qdrant_service import (
    FaceSearchResult,
    VectorStoreError,
    delete_face_embeddings,
    upsert_face_embedding,
)
from backend.app.services.face_duplicate_service import find_duplicate_face_owner


logger = logging.getLogger(__name__)


class RetryableEnrollmentInfrastructureError(RuntimeError):
    pass


def process_enrollment_job(payload: dict[str, Any]) -> dict[str, Any]:
    logger.info("Received enrollment job: %s", payload)

    job_id = str(payload.get("job_id", ""))
    db = SessionLocal()
    try:
        enrollment = db.scalar(
            select(Enrollment)
            .options(selectinload(Enrollment.images))   
            .where(Enrollment.job_id == job_id)
        )

        if enrollment is None:
            logger.warning("Enrollment job not found in DB: %s", job_id)
            return {
                "status": "failed",
                "message": "Enrollment job not found in database.",
            }

        bucket_name = str(payload.get("bucket_name", "enrollments"))
        runtime_settings = get_effective_runtime_settings(db)
        duplicate_threshold = get_settings().duplicate_enroll_threshold

        upserted_point_ids: list[int] = []
        for image in enrollment.images:
            if image.processing_status == "success" and image.qdrant_point_id is not None:
                try:
                    upserted_point_ids.append(int(image.qdrant_point_id))
                except (TypeError, ValueError):
                    pass

        duplicate_match: FaceSearchResult | None = None

        for image in enrollment.images:
            if image.processing_status == "success":
                continue
            if image.processing_status == "failed":
                continue

            try:
                image_bytes = download_object_bytes(bucket_name, image.object_key)
                result = _analyze_image_bytes(image_bytes, runtime_settings)
            except ObjectStorageError as exc:
                _mark_enrollment_pending_for_retry(
                    db,
                    enrollment,
                    f"Temporary object storage error: {exc}",
                )
                raise RetryableEnrollmentInfrastructureError(str(exc)) from exc
            except Exception as exc:
                logger.exception(
                    "Unexpected error while processing enrollment image '%s'.",
                    image.object_key,
                )
                result = {
                    "status": "failed",
                    "error_message": f"Unexpected processing error: {exc}",
                }

            if result["status"] != "success":
                image.processing_status = "failed"
                image.qdrant_point_id = None
                image.error_message = str(
                    result.get("error_message")
                    or "Enrollment image validation failed."
                )
                continue

            embedding = list(result["embedding"])

            try:
                duplicate_match = find_duplicate_face_owner(
                    db=db,
                    embedding=embedding,
                    exclude_employee_id=enrollment.employee_id,
                    threshold=duplicate_threshold,
                )
            except VectorStoreError as exc:
                _mark_enrollment_pending_for_retry(
                    db,
                    enrollment,
                    f"Temporary vector store error: {exc}",
                )
                raise RetryableEnrollmentInfrastructureError(str(exc)) from exc

            if duplicate_match is not None:
                break

            try:
                point_id = upsert_face_embedding(
                    employee_id=enrollment.employee_id,
                    enrollment_id=enrollment.id,
                    enrollment_image_id=image.id,
                    object_key=image.object_key,
                    embedding=embedding,
                )
            except VectorStoreError as exc:
                _mark_enrollment_pending_for_retry(
                    db,
                    enrollment,
                    f"Temporary vector store error: {exc}",
                )
                raise RetryableEnrollmentInfrastructureError(str(exc)) from exc

            upserted_point_ids.append(image.id)
            image.processing_status = "success"
            image.qdrant_point_id = point_id
            image.error_message = None

        if duplicate_match is not None:
            _reject_enrollment_as_duplicate(
                db,
                enrollment,
                upserted_point_ids,
                duplicate_match,
            )
            return {
                "status": enrollment.status,
                "message": enrollment.message,
            }

        _apply_terminal_enrollment_state(enrollment)
        db.commit()

        return {
            "status": enrollment.status,
            "message": enrollment.message,
        }
    finally:
        db.close()


def _analyze_image_bytes(image_bytes: bytes, runtime_settings: object) -> dict[str, Any]:
    parameters = inspect.signature(analyze_image_bytes).parameters
    if len(parameters) == 1:
        return analyze_image_bytes(image_bytes)
    return analyze_image_bytes(image_bytes, runtime_settings)


def mark_enrollment_job_failed_after_retries(job, connection, *exc_info) -> None:
    del connection

    payload = job.args[0] if job.args else {}
    job_id = str(payload.get("job_id", ""))
    error_value = exc_info[1] if len(exc_info) >= 2 else None
    failure_reason = str(error_value) if error_value else "Enrollment job failed after retries."

    db = SessionLocal()
    try:
        enrollment = db.scalar(
            select(Enrollment)
            .options(selectinload(Enrollment.images))
            .where(Enrollment.job_id == job_id)
        )
        if enrollment is None:
            logger.warning("Enrollment job not found while handling retries exhaustion: %s", job_id)
            return

        for image in enrollment.images:
            if image.processing_status == "pending":
                image.processing_status = "failed"
                image.qdrant_point_id = None
                image.error_message = failure_reason

        _apply_terminal_enrollment_state(enrollment, failure_reason=failure_reason)
        db.commit()
    finally:
        db.close()


def _mark_enrollment_pending_for_retry(
    db,
    enrollment: Enrollment,
    message: str,
) -> None:
    processed_count, failed_count = _count_image_states(enrollment)
    enrollment.status = "pending"
    enrollment.processed_count = processed_count
    enrollment.failed_count = failed_count
    enrollment.completed_at = None
    enrollment.message = message
    db.commit()


def _reject_enrollment_as_duplicate(
    db,
    enrollment: Enrollment,
    upserted_point_ids: list[int],
    duplicate_match: FaceSearchResult,
) -> None:
    if upserted_point_ids:
        try:
            delete_face_embeddings(list(upserted_point_ids))
        except VectorStoreError:
            logger.exception(
                "Failed to roll back embeddings for enrollment '%s' after duplicate detection.",
                enrollment.job_id,
            )

    error_message = (
        f"Khuôn mặt đã được đăng ký cho nhân viên #{duplicate_match.employee_id} "
        f"(độ trùng khớp {duplicate_match.score:.2f}). Hệ thống từ chối đăng ký mới."
    )

    for image in enrollment.images:
        image.processing_status = "failed"
        image.qdrant_point_id = None
        image.error_message = error_message

    enrollment.status = "failed"
    enrollment.message = error_message
    enrollment.completed_at = datetime.utcnow()
    enrollment.processed_count = 0
    enrollment.failed_count = len(enrollment.images)
    db.commit()


def _apply_terminal_enrollment_state(
    enrollment: Enrollment,
    *,
    failure_reason: str | None = None,
) -> None:
    processed_count, failed_count = _count_image_states(enrollment)
    enrollment.processed_count = processed_count
    enrollment.failed_count = failed_count
    enrollment.completed_at = datetime.utcnow()

    if processed_count > 0:
        enrollment.status = "success"
        if failed_count == 0:
            enrollment.message = f"Indexed {processed_count} image(s) into Qdrant successfully."
            return
        if failure_reason:
            enrollment.message = (
                f"Indexed {processed_count} image(s) into Qdrant, "
                f"{failed_count} image(s) failed after retry exhaustion."
            )
            return
        enrollment.message = (
            f"Indexed {processed_count} image(s) into Qdrant, "
            f"{failed_count} image(s) failed validation."
        )
        return

    enrollment.status = "failed"
    if failure_reason:
        enrollment.message = f"Enrollment failed after retry exhaustion: {failure_reason}"
        return
    enrollment.message = "All enrollment images failed before Qdrant indexing."


def _count_image_states(enrollment: Enrollment) -> tuple[int, int]:
    processed_count = sum(1 for image in enrollment.images if image.processing_status == "success")
    failed_count = sum(1 for image in enrollment.images if image.processing_status == "failed")
    return processed_count, failed_count
