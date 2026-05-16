from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.models.employee import Employee
from backend.app.models.enrollment import Enrollment
from backend.app.models.enrollment_image import EnrollmentImage
from backend.app.services.minio_service import ObjectStorageError
from backend.app.services.qdrant_service import VectorStoreError
from worker.app import jobs as worker_jobs


def seed_enrollment(db_session) -> Enrollment:
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

    enrollment = Enrollment(
        job_id="job_123",
        employee_id=employee.id,
        status="pending",
        uploaded_count=2,
        processed_count=0,
        failed_count=0,
        message="Enrollment stored. Waiting for worker.",
    )
    db_session.add(enrollment)
    db_session.flush()

    db_session.add_all(
        [
            EnrollmentImage(
                enrollment_id=enrollment.id,
                object_key="enrollments/job_123/01_face_1.jpg",
                original_file_name="face_1.jpg",
                content_type="image/jpeg",
                sort_order=1,
                processing_status="pending",
            ),
            EnrollmentImage(
                enrollment_id=enrollment.id,
                object_key="enrollments/job_123/02_face_2.jpg",
                original_file_name="face_2.jpg",
                content_type="image/jpeg",
                sort_order=2,
                processing_status="pending",
            ),
        ]
    )
    db_session.commit()
    db_session.refresh(enrollment)
    return enrollment


def test_process_enrollment_job_returns_failed_when_job_not_found(db_session, monkeypatch):
    monkeypatch.setattr(worker_jobs, "SessionLocal", lambda: db_session)

    result = worker_jobs.process_enrollment_job({"job_id": "missing-job"})

    assert result["status"] == "failed"
    assert result["message"] == "Enrollment job not found in database."


def test_process_enrollment_job_marks_images_success_when_indexing_succeeds(
    db_session,
    monkeypatch,
):
    enrollment = seed_enrollment(db_session)
    monkeypatch.setattr(worker_jobs, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        worker_jobs,
        "download_object_bytes",
        lambda bucket_name, object_key: b"fake-image-bytes",
    )
    monkeypatch.setattr(
        worker_jobs,
        "analyze_image_bytes",
        lambda image_bytes: {
            "status": "success",
            "embedding": [0.1] * 512,
        },
    )
    monkeypatch.setattr(
        worker_jobs,
        "upsert_face_embedding",
        lambda **kwargs: f"point-{kwargs['enrollment_image_id']}",
    )

    result = worker_jobs.process_enrollment_job(
        {"job_id": enrollment.job_id, "bucket_name": "enrollments"}
    )

    db_session.expire_all()
    updated = db_session.scalar(
        select(Enrollment).where(Enrollment.id == enrollment.id)
    )

    assert result["status"] == "success"
    assert updated is not None
    assert updated.status == "success"
    assert updated.processed_count == 2
    assert updated.failed_count == 0

    images = updated.images
    assert images[0].processing_status == "success"
    assert images[0].qdrant_point_id == f"point-{images[0].id}"
    assert images[1].processing_status == "success"
    assert images[1].qdrant_point_id == f"point-{images[1].id}"


def test_process_enrollment_job_retries_when_qdrant_upsert_fails(
    db_session,
    monkeypatch,
):
    enrollment = seed_enrollment(db_session)

    monkeypatch.setattr(worker_jobs, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        worker_jobs,
        "download_object_bytes",
        lambda bucket_name, object_key: b"fake-image-bytes",
    )
    monkeypatch.setattr(
        worker_jobs,
        "analyze_image_bytes",
        lambda image_bytes: {
            "status": "success",
            "embedding": [0.1] * 512,
        },
    )

    def fake_upsert(**kwargs):
        raise VectorStoreError("Cannot upsert embedding to Qdrant.")

    monkeypatch.setattr(worker_jobs, "upsert_face_embedding", fake_upsert)

    with pytest.raises(worker_jobs.RetryableEnrollmentInfrastructureError):
        worker_jobs.process_enrollment_job(
            {"job_id": enrollment.job_id, "bucket_name": "enrollments"}
        )

    db_session.expire_all()
    updated = db_session.scalar(
        select(Enrollment).where(Enrollment.id == enrollment.id)
    )

    assert updated is not None
    assert updated.status == "pending"
    assert updated.processed_count == 0
    assert updated.failed_count == 0

    for image in updated.images:
        assert image.processing_status == "pending"
        assert image.qdrant_point_id is None
        assert image.error_message is None


def test_process_enrollment_job_marks_images_failed_when_analysis_fails(
    db_session,
    monkeypatch,
):
    enrollment = seed_enrollment(db_session)

    monkeypatch.setattr(worker_jobs, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        worker_jobs,
        "download_object_bytes",
        lambda bucket_name, object_key: b"fake-image-bytes",
    )
    monkeypatch.setattr(
        worker_jobs,
        "analyze_image_bytes",
        lambda image_bytes: {
            "status": "failed",
            "error_message": "No face detected.",
        },
    )

    result = worker_jobs.process_enrollment_job(
        {"job_id": enrollment.job_id, "bucket_name": "enrollments"}
    )

    db_session.expire_all()
    updated = db_session.scalar(
        select(Enrollment).where(Enrollment.id == enrollment.id)
    )

    assert result["status"] == "failed"
    assert updated is not None
    assert updated.status == "failed"
    assert updated.processed_count == 0
    assert updated.failed_count == 2

    for image in updated.images:
        assert image.processing_status == "failed"
        assert image.qdrant_point_id is None
        assert image.error_message == "No face detected."


def test_process_enrollment_job_retries_when_download_fails(
    db_session,
    monkeypatch,
):
    enrollment = seed_enrollment(db_session)

    monkeypatch.setattr(worker_jobs, "SessionLocal", lambda: db_session)

    def fake_download(bucket_name, object_key):
        raise ObjectStorageError(f"Cannot download object '{object_key}'.")

    monkeypatch.setattr(worker_jobs, "download_object_bytes", fake_download)

    with pytest.raises(worker_jobs.RetryableEnrollmentInfrastructureError):
        worker_jobs.process_enrollment_job(
            {"job_id": enrollment.job_id, "bucket_name": "enrollments"}
        )

    db_session.expire_all()
    updated = db_session.scalar(
        select(Enrollment).where(Enrollment.id == enrollment.id)
    )

    assert updated is not None
    assert updated.status == "pending"
    assert updated.processed_count == 0
    assert updated.failed_count == 0

    for image in updated.images:
        assert image.processing_status == "pending"
        assert image.qdrant_point_id is None
        assert image.error_message is None


def test_mark_enrollment_job_failed_after_retries_marks_pending_images_failed(
    db_session,
    monkeypatch,
):
    enrollment = seed_enrollment(db_session)
    enrollment.images[0].processing_status = "success"
    enrollment.images[0].qdrant_point_id = "point-1"
    db_session.commit()

    monkeypatch.setattr(worker_jobs, "SessionLocal", lambda: db_session)

    class DummyJob:
        args = [{"job_id": enrollment.job_id}]

    worker_jobs.mark_enrollment_job_failed_after_retries(
        DummyJob(),
        None,
        RuntimeError,
        RuntimeError("Cannot download object 'enrollments/job_123/02_face_2.jpg'."),
        None,
    )

    db_session.expire_all()
    updated = db_session.scalar(select(Enrollment).where(Enrollment.id == enrollment.id))

    assert updated is not None
    assert updated.status == "success"
    assert updated.processed_count == 1
    assert updated.failed_count == 1
    assert "retry exhaustion" in (updated.message or "").lower()
    assert updated.images[0].processing_status == "success"
    assert updated.images[1].processing_status == "failed"
    assert "Cannot download object" in (updated.images[1].error_message or "")
