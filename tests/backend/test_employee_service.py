from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from backend.app.models.attendance_event import AttendanceEvent
from backend.app.models.employee import Employee
from backend.app.models.enrollment import Enrollment
from backend.app.models.enrollment_image import EnrollmentImage
from backend.app.services import employee_service
from backend.app.services.qdrant_service import VectorStoreError


def seed_employee(
    db_session,
    *,
    employee_code: str,
    department: str = "IT",
) -> Employee:
    employee = Employee(
        employee_code=employee_code,
        full_name=f"Employee {employee_code}",
        department=department,
        position="Engineer",
        status="active",
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)
    return employee


def seed_enrollment(
    db_session,
    employee_id: int,
    *,
    status: str,
    processed_count: int = 0,
    failed_count: int = 0,
    created_at: datetime,
) -> Enrollment:
    enrollment = Enrollment(
        job_id=f"job_{employee_id}_{status}_{created_at.timestamp()}",
        employee_id=employee_id,
        status=status,
        uploaded_count=3,
        processed_count=processed_count,
        failed_count=failed_count,
        message=None,
        created_at=created_at,
    )
    db_session.add(enrollment)
    db_session.commit()
    db_session.refresh(enrollment)
    return enrollment


def test_list_employees_filters_by_department_case_insensitive_exact_match(db_session):
    it_employee = seed_employee(db_session, employee_code="E001", department="IT")
    seed_employee(db_session, employee_code="E002", department="IT Ops")
    seed_employee(db_session, employee_code="E003", department="HR")

    items, total = employee_service.list_employees(
        db_session,
        q=None,
        department="  it  ",
        page=1,
        page_size=20,
    )

    assert total == 1
    assert [employee.id for employee in items] == [it_employee.id]


def test_list_employees_returns_newest_first(db_session):
    seed_employee(db_session, employee_code="E001")
    seed_employee(db_session, employee_code="E002")
    newest = seed_employee(db_session, employee_code="E003")

    items, total = employee_service.list_employees(
        db_session,
        q=None,
        department=None,
        page=1,
        page_size=1,
    )

    assert total == 3
    assert [employee.id for employee in items] == [newest.id]


def test_list_employees_maps_face_data_status_values(db_session):
    now = datetime.utcnow()
    missing = seed_employee(db_session, employee_code="E001")
    pending = seed_employee(db_session, employee_code="E002")
    enrolled = seed_employee(db_session, employee_code="E003")
    failed = seed_employee(db_session, employee_code="E004")

    seed_enrollment(
        db_session,
        pending.id,
        status="pending",
        created_at=now,
    )
    seed_enrollment(
        db_session,
        enrolled.id,
        status="success",
        processed_count=2,
        created_at=now + timedelta(minutes=1),
    )
    seed_enrollment(
        db_session,
        failed.id,
        status="failed",
        failed_count=3,
        created_at=now + timedelta(minutes=2),
    )

    items, total = employee_service.list_employees(
        db_session,
        q=None,
        department=None,
        page=1,
        page_size=20,
    )

    assert total == 4
    face_data_by_code = {
        employee.employee_code: employee.face_data_status for employee in items
    }
    assert face_data_by_code[missing.employee_code] == "missing"
    assert face_data_by_code[pending.employee_code] == "pending"
    assert face_data_by_code[enrolled.employee_code] == "enrolled"
    assert face_data_by_code[failed.employee_code] == "failed"


def test_list_employees_uses_latest_enrollment_for_face_data_status(db_session):
    employee = seed_employee(db_session, employee_code="E001")
    now = datetime.utcnow()

    seed_enrollment(
        db_session,
        employee.id,
        status="success",
        processed_count=2,
        created_at=now,
    )
    seed_enrollment(
        db_session,
        employee.id,
        status="pending",
        created_at=now + timedelta(minutes=1),
    )

    items, total = employee_service.list_employees(
        db_session,
        q=None,
        department=None,
        page=1,
        page_size=20,
    )

    assert total == 1
    assert items[0].face_data_status == "pending"


def test_delete_employee_rejects_employee_with_enrollment(db_session):
    employee = seed_employee(db_session, employee_code="E-ENROLLED")
    seed_enrollment(
        db_session,
        employee.id,
        status="success",
        processed_count=2,
        created_at=datetime.utcnow(),
    )

    with pytest.raises(employee_service.EmployeeHasRelatedDataError):
        employee_service.delete_employee(db_session, employee.id)

    assert db_session.get(Employee, employee.id) is not None


def test_delete_employee_rejects_employee_with_attendance_history(db_session):
    employee = seed_employee(db_session, employee_code="E-HISTORY")
    event = AttendanceEvent(
        employee_id=employee.id,
        action_type="check_in",
        attendance_status="recorded",
    )
    db_session.add(event)
    db_session.commit()

    with pytest.raises(employee_service.EmployeeHasRelatedDataError):
        employee_service.delete_employee(db_session, employee.id)

    assert db_session.get(Employee, employee.id) is not None


def _seed_enrollment_image(
    db_session,
    enrollment_id: int,
    *,
    sort_order: int,
    object_key: str,
    qdrant_point_id: str | None,
) -> EnrollmentImage:
    image = EnrollmentImage(
        enrollment_id=enrollment_id,
        object_key=object_key,
        original_file_name=object_key.rsplit("/", 1)[-1],
        content_type="image/jpeg",
        sort_order=sort_order,
        processing_status="success",
        qdrant_point_id=qdrant_point_id,
    )
    db_session.add(image)
    db_session.commit()
    db_session.refresh(image)
    return image


def test_force_delete_cleans_biometric_and_anonymises_attendance(
    db_session,
    monkeypatch,
):
    employee = seed_employee(db_session, employee_code="E-FORCE")
    enrollment = seed_enrollment(
        db_session,
        employee.id,
        status="success",
        processed_count=2,
        created_at=datetime.utcnow(),
    )
    _seed_enrollment_image(
        db_session,
        enrollment.id,
        sort_order=1,
        object_key="enrollments/job_x/01_a.jpg",
        qdrant_point_id="11",
    )
    _seed_enrollment_image(
        db_session,
        enrollment.id,
        sort_order=2,
        object_key="enrollments/job_x/02_b.jpg",
        qdrant_point_id="12",
    )
    event = AttendanceEvent(
        employee_id=employee.id,
        action_type="check_in",
        attendance_status="recorded",
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    event_id = event.id

    qdrant_calls: list[list[int]] = []
    minio_calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        employee_service,
        "delete_face_embeddings",
        lambda ids: qdrant_calls.append(list(ids)),
    )
    monkeypatch.setattr(
        employee_service,
        "delete_objects",
        lambda bucket, keys: minio_calls.append((bucket, list(keys))),
    )

    stats = employee_service.force_delete_employee(db_session, employee.id)

    assert stats == {
        "qdrant_points_deleted": 2,
        "minio_objects_deleted": 2,
        "attendance_events_anonymized": 1,
    }
    assert db_session.get(Employee, employee.id) is None
    assert qdrant_calls == [[11, 12]]
    assert minio_calls[0][0] == "enrollments"
    assert set(minio_calls[0][1]) == {
        "enrollments/job_x/01_a.jpg",
        "enrollments/job_x/02_b.jpg",
    }

    remaining_event = db_session.get(AttendanceEvent, event_id)
    assert remaining_event is not None
    assert remaining_event.employee_id is None


def test_force_delete_returns_none_when_employee_missing(db_session):
    assert employee_service.force_delete_employee(db_session, 99999) is None


def test_force_delete_completes_even_when_qdrant_fails(db_session, monkeypatch):
    employee = seed_employee(db_session, employee_code="E-RESILIENT")
    enrollment = seed_enrollment(
        db_session,
        employee.id,
        status="success",
        created_at=datetime.utcnow(),
    )
    _seed_enrollment_image(
        db_session,
        enrollment.id,
        sort_order=1,
        object_key="enrollments/job_y/01_a.jpg",
        qdrant_point_id="21",
    )

    def raise_vector_store(_ids):
        raise VectorStoreError("Qdrant down")

    monkeypatch.setattr(
        employee_service, "delete_face_embeddings", raise_vector_store
    )
    monkeypatch.setattr(
        employee_service, "delete_objects", lambda *_args, **_kwargs: None
    )

    stats = employee_service.force_delete_employee(db_session, employee.id)

    assert stats is not None
    assert db_session.get(Employee, employee.id) is None
