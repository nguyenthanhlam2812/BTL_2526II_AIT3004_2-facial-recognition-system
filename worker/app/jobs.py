from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.db.session import SessionLocal
from backend.app.models.enrollment import Enrollment
from backend.app.services.minio_service import (
    ObjectStorageError,
    download_object_bytes,
)
from worker.app.face_analyzer import analyze_image_bytes

from backend.app.services.qdrant_service import (
    VectorStoreError,
    upsert_face_embedding,
)


logger = logging.getLogger(__name__)


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
        processed_count = 0
        failed_count = 0

        for image in enrollment.images:
            try:
                image_bytes = download_object_bytes(bucket_name, image.object_key)
                result = analyze_image_bytes(image_bytes)
            except ObjectStorageError as exc:
                result = {
                    "status": "failed",
                    "error_message": str(exc),
                }
            except Exception as exc:
                logger.exception(
                    "Unexpected error while processing enrollment image '%s'.",
                    image.object_key,
                )
                result = {
                    "status": "failed",
                    "error_message": f"Unexpected processing error: {exc}",
                }

            if result["status"] == "success":
                try:
                    point_id = upsert_face_embedding(
                        employee_id=enrollment.employee_id,
                        enrollment_id=enrollment.id,
                        enrollment_image_id=image.id,
                        object_key=image.object_key,
                        embedding=list(result["embedding"]),
                    )
                except VectorStoreError as exc:
                    image.processing_status = "failed"
                    image.qdrant_point_id = None
                    image.error_message = str(exc)
                    failed_count += 1
                    continue

                image.processing_status = "success"
                image.qdrant_point_id = point_id
                image.error_message = None
                processed_count += 1


        enrollment.processed_count = processed_count
        enrollment.failed_count = failed_count
        enrollment.completed_at = datetime.utcnow()

        if processed_count > 0:
            enrollment.status = "success"
            if failed_count == 0:
                enrollment.message = (
                    f"Indexed {processed_count} image(s) into Qdrant successfully."
                )
            else:
                enrollment.message = (
                    f"Indexed {processed_count} image(s) into Qdrant, "
                    f"{failed_count} image(s) failed validation."
                )
        else:
            enrollment.status = "failed"
            enrollment.message = "All enrollment images failed before Qdrant indexing."


        db.commit()

        return {
            "status": enrollment.status,
            "message": enrollment.message,
        }
    finally:
        db.close()
