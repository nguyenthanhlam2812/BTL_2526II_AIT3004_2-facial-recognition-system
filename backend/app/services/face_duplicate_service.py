from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from backend.app.models.employee import Employee
from backend.app.services.qdrant_service import (
    FaceSearchResult,
    VectorStoreError,
    delete_face_embeddings,
    search_face_embeddings,
)


logger = logging.getLogger(__name__)


def find_duplicate_face_owner(
    *,
    db: Session,
    embedding: list[float],
    exclude_employee_id: int,
    threshold: float,
    limit: int = 10,
    max_cleanup_rounds: int = 3,
) -> FaceSearchResult | None:
    """Find a duplicate face owned by an existing employee.

    Qdrant can outlive MySQL rows when a demo DB is reset or data is cleaned
    manually. Those stale vectors must not block a new enrollment, so this
    helper verifies the employee in MySQL and best-effort deletes orphaned
    Qdrant points before continuing the duplicate scan.
    """

    for _ in range(max_cleanup_rounds):
        stale_point_ids: list[str | int] = []
        candidates = search_face_embeddings(embedding=embedding, limit=limit)

        for candidate in candidates:
            if candidate.employee_id is None:
                continue
            if candidate.employee_id == exclude_employee_id:
                continue
            if candidate.score < threshold:
                _delete_stale_points(stale_point_ids)
                return None

            employee = db.get(Employee, candidate.employee_id)
            if employee is None:
                if candidate.point_id is not None:
                    stale_point_ids.append(candidate.point_id)
                continue

            _delete_stale_points(stale_point_ids)
            return candidate

        if not stale_point_ids:
            return None

        _delete_stale_points(stale_point_ids)

    return None


def _delete_stale_points(point_ids: list[str | int]) -> None:
    if not point_ids:
        return

    try:
        delete_face_embeddings(point_ids)
    except VectorStoreError:
        logger.warning("face_duplicate.stale_qdrant_cleanup_failed", exc_info=True)
