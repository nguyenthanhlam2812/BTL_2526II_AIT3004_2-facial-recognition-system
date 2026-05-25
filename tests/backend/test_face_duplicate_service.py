from __future__ import annotations

from backend.app.models.employee import Employee
from backend.app.services import face_duplicate_service
from backend.app.services.qdrant_service import FaceSearchResult


def _seed_employee(db_session, employee_code: str = "E-DUP") -> Employee:
    employee = Employee(
        employee_code=employee_code,
        full_name="Duplicate Owner",
        department="IT",
        position="Engineer",
        status="active",
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)
    return employee


def test_find_duplicate_face_owner_ignores_and_deletes_stale_qdrant_points(
    db_session,
    monkeypatch,
):
    owner = _seed_employee(db_session)
    deleted: list[list[str | int]] = []

    monkeypatch.setattr(
        face_duplicate_service,
        "search_face_embeddings",
        lambda **_: [
            FaceSearchResult(employee_id=999, score=0.99, payload={}, point_id=44),
            FaceSearchResult(
                employee_id=owner.id,
                score=0.91,
                payload={},
                point_id=45,
            ),
        ],
    )
    monkeypatch.setattr(
        face_duplicate_service,
        "delete_face_embeddings",
        lambda point_ids: deleted.append(list(point_ids)),
    )

    result = face_duplicate_service.find_duplicate_face_owner(
        db=db_session,
        embedding=[0.1] * 512,
        exclude_employee_id=7,
        threshold=0.6,
    )

    assert result is not None
    assert result.employee_id == owner.id
    assert deleted == [[44]]


def test_find_duplicate_face_owner_allows_enrollment_when_only_match_is_stale(
    db_session,
    monkeypatch,
):
    deleted: list[list[str | int]] = []
    calls = {"count": 0}

    def fake_search(**_):
        calls["count"] += 1
        if calls["count"] == 1:
            return [FaceSearchResult(employee_id=999, score=0.99, payload={}, point_id=44)]
        return []

    monkeypatch.setattr(face_duplicate_service, "search_face_embeddings", fake_search)
    monkeypatch.setattr(
        face_duplicate_service,
        "delete_face_embeddings",
        lambda point_ids: deleted.append(list(point_ids)),
    )

    result = face_duplicate_service.find_duplicate_face_owner(
        db=db_session,
        embedding=[0.1] * 512,
        exclude_employee_id=7,
        threshold=0.6,
    )

    assert result is None
    assert deleted == [[44]]
