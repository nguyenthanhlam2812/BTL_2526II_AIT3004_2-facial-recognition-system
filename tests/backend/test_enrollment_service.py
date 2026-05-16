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
