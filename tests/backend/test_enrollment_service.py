from __future__ import annotations

from io import BytesIO

import pytest
from fastapi import UploadFile
from sqlalchemy import func, select
from starlette.datastructures import Headers

from backend.app.models.employee import Employee
from backend.app.models.enrollment import Enrollment
from backend.app.models.enrollment_image import EnrollmentImage
from backend.app.services import enrollment_service
from backend.app.services.qdrant_service import FaceSearchResult, VectorStoreError
from backend.app.services.queue_service import QueueUnavailableError


def make_upload_file(
    filename: str,
    content: bytes = b"fake-image-bytes",
    content_type: str = "image/jpeg",
) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )


def seed_employee(db_session) -> Employee:
    employee = Employee(
        employee_code="E001",
        full_name="Nguyen Van A",
        department="IT",
        position="Engineer",
        status="active",
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)
    return employee


def test_create_enrollment_creates_records_uploads_files_and_enqueues_job(
    db_session,
    monkeypatch,
):
    employee = seed_employee(db_session)
    upload_calls = []
    enqueued = {}

    monkeypatch.setattr(enrollment_service, "ensure_bucket_exists", lambda _: None)

    def fake_upload(bucket_name, object_key, content, content_type):
        upload_calls.append((bucket_name, object_key, content, content_type))

    def fake_enqueue(payload):
        enqueued["payload"] = payload

    monkeypatch.setattr(enrollment_service, "upload_object_bytes", fake_upload)
    monkeypatch.setattr(enrollment_service, "enqueue_enrollment_job", fake_enqueue)

    enrollment = enrollment_service.create_enrollment(
        db_session,
        employee.id,
        [
            make_upload_file("face_1.jpg"),
            make_upload_file("face_2.png"),
        ],
    )

    assert enrollment.employee_id == employee.id
    assert enrollment.status == "pending"
    assert enrollment.uploaded_count == 2
    assert enrollment.processed_count == 0
    assert enrollment.failed_count == 0
    assert db_session.scalar(select(func.count()).select_from(Enrollment)) == 1
    assert db_session.scalar(select(func.count()).select_from(EnrollmentImage)) == 2

    images = db_session.scalars(
        select(EnrollmentImage).order_by(EnrollmentImage.sort_order)
    ).all()
    assert images[0].object_key.endswith("01_face_1.jpg")
    assert images[1].object_key.endswith("02_face_2.png")
    assert len(upload_calls) == 2
    assert enqueued["payload"]["job_id"] == enrollment.job_id
    assert enqueued["payload"]["employee_id"] == employee.id
    assert enqueued["payload"]["uploaded_count"] == 2
    assert len(enqueued["payload"]["object_keys"]) == 2


def test_create_enrollment_rolls_back_db_and_deletes_objects_when_queue_fails(
    db_session,
    monkeypatch,
):
    employee = seed_employee(db_session)
    uploaded_object_keys = []
    deleted = {}

    monkeypatch.setattr(enrollment_service, "ensure_bucket_exists", lambda _: None)

    def fake_upload(bucket_name, object_key, content, content_type):
        uploaded_object_keys.append(object_key)

    def fake_delete(bucket_name, object_keys):
        deleted["bucket_name"] = bucket_name
        deleted["object_keys"] = list(object_keys)

    def fake_enqueue(payload):
        raise QueueUnavailableError("Cannot enqueue enrollment job.")

    monkeypatch.setattr(enrollment_service, "upload_object_bytes", fake_upload)
    monkeypatch.setattr(enrollment_service, "delete_objects", fake_delete)
    monkeypatch.setattr(enrollment_service, "enqueue_enrollment_job", fake_enqueue)

    with pytest.raises(
        enrollment_service.EnrollmentInfrastructureError,
        match="Enrollment queue is unavailable.",
    ):
        enrollment_service.create_enrollment(
            db_session,
            employee.id,
            [
                make_upload_file("face_1.jpg"),
                make_upload_file("face_2.jpg"),
            ],
        )

    assert len(uploaded_object_keys) == 2
    assert db_session.scalar(select(func.count()).select_from(Enrollment)) == 0
    assert db_session.scalar(select(func.count()).select_from(EnrollmentImage)) == 0
    assert len(deleted["object_keys"]) == 2


def test_validate_enrollment_files_rejects_unsupported_file_type():
    files = [make_upload_file("notes.txt", content_type="text/plain")]

    with pytest.raises(
        enrollment_service.InvalidEnrollmentFilesError,
        match="is not a supported image",
    ):
        enrollment_service.validate_enrollment_files(files)


# --- duplicate pre-check tests ---

def _mock_analyze_success(image_bytes: bytes) -> dict:
    return {"status": "success", "embedding": [0.1] * 512}


def _mock_analyze_failed(image_bytes: bytes) -> dict:
    return {"status": "failed", "error_message": "No face detected."}


def test_check_enrollment_raises_when_duplicate_face_found(monkeypatch):
    monkeypatch.setattr(enrollment_service, "analyze_image_bytes", _mock_analyze_success)
    monkeypatch.setattr(
        enrollment_service,
        "find_duplicate_face_owner",
        lambda **kwargs: FaceSearchResult(
            employee_id=99, score=0.87, payload={}, point_id=42
        ),
    )

    files = [make_upload_file("face.jpg")]

    with pytest.raises(enrollment_service.DuplicateFaceEnrollmentError) as exc_info:
        enrollment_service._check_enrollment_for_duplicates(files, employee_id=7)

    assert exc_info.value.employee_id == 99
    assert "đăng ký cho nhân viên #99" in str(exc_info.value)


def test_check_enrollment_skips_image_when_analysis_fails(monkeypatch):
    monkeypatch.setattr(enrollment_service, "analyze_image_bytes", _mock_analyze_failed)

    called = []
    monkeypatch.setattr(
        enrollment_service,
        "find_duplicate_face_owner",
        lambda **kwargs: called.append(kwargs) or None,
    )

    files = [make_upload_file("face.jpg"), make_upload_file("face2.jpg")]
    enrollment_service._check_enrollment_for_duplicates(files, employee_id=7)

    assert called == []


def test_check_enrollment_fails_open_when_qdrant_unavailable(monkeypatch):
    monkeypatch.setattr(enrollment_service, "analyze_image_bytes", _mock_analyze_success)
    monkeypatch.setattr(
        enrollment_service,
        "find_duplicate_face_owner",
        lambda **kwargs: (_ for _ in ()).throw(VectorStoreError("Qdrant down")),
    )

    files = [make_upload_file("face.jpg")]
    # Should not raise — fail open so the worker guard can catch it later
    enrollment_service._check_enrollment_for_duplicates(files, employee_id=7)


def test_check_enrollment_skips_same_employee(monkeypatch):
    monkeypatch.setattr(enrollment_service, "analyze_image_bytes", _mock_analyze_success)
    # find_duplicate_face_owner returning None means "same employee or below threshold"
    monkeypatch.setattr(
        enrollment_service,
        "find_duplicate_face_owner",
        lambda **kwargs: None,
    )

    files = [make_upload_file("face.jpg")]
    enrollment_service._check_enrollment_for_duplicates(files, employee_id=7)


def test_create_enrollment_returns_409_on_duplicate_face(db_session, monkeypatch):
    employee = seed_employee(db_session)

    monkeypatch.setattr(enrollment_service, "analyze_image_bytes", _mock_analyze_success)
    monkeypatch.setattr(
        enrollment_service,
        "find_duplicate_face_owner",
        lambda **kwargs: FaceSearchResult(
            employee_id=999, score=0.91, payload={}, point_id=1
        ),
    )
    monkeypatch.setattr(enrollment_service, "ensure_bucket_exists", lambda _: None)
    monkeypatch.setattr(enrollment_service, "upload_object_bytes", lambda *a: None)
    monkeypatch.setattr(enrollment_service, "enqueue_enrollment_job", lambda _: None)

    with pytest.raises(enrollment_service.DuplicateFaceEnrollmentError):
        enrollment_service.create_enrollment(
            db_session,
            employee.id,
            [make_upload_file("face.jpg")],
        )
