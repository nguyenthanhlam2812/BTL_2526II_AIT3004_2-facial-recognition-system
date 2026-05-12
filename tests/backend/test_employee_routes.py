from __future__ import annotations

from datetime import datetime, timedelta

from backend.app.models.employee import Employee
from backend.app.models.enrollment import Enrollment


def seed_employee(
    db_session,
    *,
    employee_code: str,
    department: str,
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
    created_at: datetime,
) -> Enrollment:
    enrollment = Enrollment(
        job_id=f"job_{employee_id}_{status}_{created_at.timestamp()}",
        employee_id=employee_id,
        status=status,
        uploaded_count=3,
        processed_count=processed_count,
        failed_count=0,
        message=None,
        created_at=created_at,
    )
    db_session.add(enrollment)
    db_session.commit()
    db_session.refresh(enrollment)
    return enrollment


def test_get_employees_returns_face_data_status(client, db_session):
    employee = seed_employee(db_session, employee_code="E001", department="IT")
    seed_enrollment(
        db_session,
        employee.id,
        status="success",
        processed_count=2,
        created_at=datetime.utcnow(),
    )

    response = client.get("/api/employees?page=1&page_size=20")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["employee_code"] == "E001"
    assert payload["items"][0]["face_data_status"] == "enrolled"


def test_get_employees_honors_department_filter(client, db_session):
    now = datetime.utcnow()
    it_employee = seed_employee(db_session, employee_code="E001", department="IT")
    hr_employee = seed_employee(db_session, employee_code="E002", department="HR")
    seed_enrollment(
        db_session,
        it_employee.id,
        status="pending",
        created_at=now,
    )
    seed_enrollment(
        db_session,
        hr_employee.id,
        status="failed",
        created_at=now + timedelta(minutes=1),
    )

    response = client.get(
        "/api/employees",
        params={"department": "  it  ", "page": 1, "page_size": 20},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["employee_code"] for item in payload["items"]] == ["E001"]
    assert payload["items"][0]["face_data_status"] == "pending"
