from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from backend.app.db.session import SessionLocal
from backend.app.models.enrollment import Enrollment


logger = logging.getLogger(__name__)


def process_enrollment_job(payload: dict[str, Any]) -> dict[str, Any]:
    logger.info("Received enrollment job: %s", payload)

    job_id = str(payload.get("job_id", ""))
    db = SessionLocal()
    try:
        enrollment = db.scalar(
            select(Enrollment).where(Enrollment.job_id == job_id)
        )
        if enrollment is None:
            logger.warning("Enrollment job not found in DB: %s", job_id)
            return {
                "status": "failed",
                "message": "Enrollment job not found in database.",
            }

        enrollment.message = (
            "Worker received job successfully. Embedding logic will be added next."
        )
        db.commit()

        return {
            "status": enrollment.status,
            "message": enrollment.message,
        }
    finally:
        db.close()
