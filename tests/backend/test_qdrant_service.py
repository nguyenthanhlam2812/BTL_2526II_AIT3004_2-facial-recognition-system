from __future__ import annotations

import pytest

from backend.app.services import qdrant_service
from backend.app.services.qdrant_service import FaceSearchResult, VectorStoreError


def test_upsert_face_embedding_uses_qdrant_compatible_integer_point_id(monkeypatch):
    captured = {}

    class FakeClient:
        def upsert(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(qdrant_service, "get_qdrant_client", lambda: FakeClient())
    monkeypatch.setattr(
        qdrant_service,
        "ensure_collection_exists",
        lambda: "employee_faces",
    )

    point_id = qdrant_service.upsert_face_embedding(
        employee_id=7,
        enrollment_id=11,
        enrollment_image_id=42,
        object_key="enrollments/job_123/01_face.jpg",
        embedding=[0.1] * 512,
    )

    assert point_id == "42"
    assert captured["collection_name"] == "employee_faces"
    assert captured["wait"] is True
    assert captured["points"][0].id == 42
    assert captured["points"][0].payload["enrollment_image_id"] == 42


def _stub_search(monkeypatch, results: list[FaceSearchResult]) -> None:
    monkeypatch.setattr(
        qdrant_service,
        "search_face_embeddings",
        lambda **_: list(results),
    )


def test_find_duplicate_face_owner_skips_same_employee(monkeypatch):
    _stub_search(
        monkeypatch,
        [
            FaceSearchResult(employee_id=7, score=0.95, payload={}, point_id=1),
            FaceSearchResult(employee_id=7, score=0.91, payload={}, point_id=2),
        ],
    )

    result = qdrant_service.find_duplicate_face_owner(
        embedding=[0.1] * 512,
        exclude_employee_id=7,
        threshold=0.6,
    )

    assert result is None


def test_find_duplicate_face_owner_returns_different_employee_above_threshold(monkeypatch):
    _stub_search(
        monkeypatch,
        [
            FaceSearchResult(employee_id=9, score=0.82, payload={}, point_id=3),
        ],
    )

    result = qdrant_service.find_duplicate_face_owner(
        embedding=[0.1] * 512,
        exclude_employee_id=7,
        threshold=0.6,
    )

    assert result is not None
    assert result.employee_id == 9
    assert result.score == 0.82


def test_find_duplicate_face_owner_returns_none_when_other_employee_below_threshold(monkeypatch):
    _stub_search(
        monkeypatch,
        [
            FaceSearchResult(employee_id=9, score=0.55, payload={}, point_id=3),
        ],
    )

    result = qdrant_service.find_duplicate_face_owner(
        embedding=[0.1] * 512,
        exclude_employee_id=7,
        threshold=0.6,
    )

    assert result is None


def test_find_duplicate_face_owner_looks_past_same_employee_matches(monkeypatch):
    # Same-employee points dominate the top of the result list; the duplicate
    # match from a different employee is buried deeper but still above threshold.
    _stub_search(
        monkeypatch,
        [
            FaceSearchResult(employee_id=7, score=0.99, payload={}, point_id=1),
            FaceSearchResult(employee_id=7, score=0.97, payload={}, point_id=2),
            FaceSearchResult(employee_id=7, score=0.95, payload={}, point_id=3),
            FaceSearchResult(employee_id=9, score=0.72, payload={}, point_id=4),
        ],
    )

    result = qdrant_service.find_duplicate_face_owner(
        embedding=[0.1] * 512,
        exclude_employee_id=7,
        threshold=0.6,
    )

    assert result is not None
    assert result.employee_id == 9


def test_find_duplicate_face_owner_ignores_points_without_employee_id(monkeypatch):
    _stub_search(
        monkeypatch,
        [
            FaceSearchResult(employee_id=None, score=0.99, payload={}, point_id=1),
            FaceSearchResult(employee_id=9, score=0.71, payload={}, point_id=2),
        ],
    )

    result = qdrant_service.find_duplicate_face_owner(
        embedding=[0.1] * 512,
        exclude_employee_id=7,
        threshold=0.6,
    )

    assert result is not None
    assert result.employee_id == 9


def test_delete_face_embeddings_calls_qdrant_delete(monkeypatch):
    captured = {}

    class FakeClient:
        def delete(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(qdrant_service, "get_qdrant_client", lambda: FakeClient())
    monkeypatch.setattr(
        qdrant_service,
        "ensure_collection_exists",
        lambda: "employee_faces",
    )

    qdrant_service.delete_face_embeddings([1, 2, 3])

    assert captured["collection_name"] == "employee_faces"
    assert captured["wait"] is True
    assert captured["points_selector"] == [1, 2, 3]


def test_delete_face_embeddings_skips_qdrant_call_when_empty(monkeypatch):
    def boom():
        raise AssertionError("get_qdrant_client should not be called when empty.")

    monkeypatch.setattr(qdrant_service, "get_qdrant_client", boom)

    qdrant_service.delete_face_embeddings([])


def test_delete_face_embeddings_wraps_client_errors(monkeypatch):
    class FakeClient:
        def delete(self, **_):
            raise RuntimeError("qdrant down")

    monkeypatch.setattr(qdrant_service, "get_qdrant_client", lambda: FakeClient())
    monkeypatch.setattr(
        qdrant_service,
        "ensure_collection_exists",
        lambda: "employee_faces",
    )

    with pytest.raises(VectorStoreError):
        qdrant_service.delete_face_embeddings([1])
