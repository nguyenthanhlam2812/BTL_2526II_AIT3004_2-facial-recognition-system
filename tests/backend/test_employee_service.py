from __future__ import annotations

from datetime import datetime, timedelta

from backend.app.models.employee import Employee
from backend.app.models.enrollment import Enrollment
from backend.app.services import employee_service


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
