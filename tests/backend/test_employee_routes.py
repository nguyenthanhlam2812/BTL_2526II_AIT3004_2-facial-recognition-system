from __future__ import annotations

from datetime import datetime, timedelta

from backend.app.models.attendance_event import AttendanceEvent
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


def test_get_employees_keeps_legacy_employee_codes_readable(client, db_session):
    seed_employee(
        db_session,
        employee_code="LIVE_ENR_20260504134435",
        department="IT",
    )

    response = client.get("/api/employees?page=1&page_size=20")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["employee_code"] == "LIVE_ENR_20260504134435"


def test_create_employee_normalizes_business_fields(client):
    response = client.post(
        "/api/employees",
        json={
            "employee_code": " emp0001 ",
            "full_name": "  Nguyen   Van   A  ",
            "department": "  Software   Engineering  ",
            "position": "  Software   Engineer  ",
            "status": "active",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["employee_code"] == "EMP0001"
    assert payload["full_name"] == "Nguyen Van A"
    assert payload["department"] == "Software Engineering"
    assert payload["position"] == "Software Engineer"


def test_create_employee_rejects_invalid_business_fields(client):
    invalid_code = client.post(
        "/api/employees",
        json={
            "employee_code": "EMP 001",
            "full_name": "Nguyen Van A",
            "department": "Software Engineering",
            "position": "Software Engineer",
            "status": "active",
        },
    )
    assert invalid_code.status_code == 422

    invalid_name = client.post(
        "/api/employees",
        json={
            "employee_code": "EMP0002",
            "full_name": "<script>",
            "department": "Software Engineering",
            "position": "Software Engineer",
            "status": "active",
        },
    )
    assert invalid_name.status_code == 422


def test_create_employee_rejects_duplicate_code_case_insensitively(client):
    first_response = client.post(
        "/api/employees",
        json={
            "employee_code": "EMP0003",
            "full_name": "Nguyen Van A",
            "department": "Software Engineering",
            "position": "Software Engineer",
            "status": "active",
        },
    )
    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/api/employees",
        json={
            "employee_code": "emp0003",
            "full_name": "Nguyen Van B",
            "department": "Data & Analytics",
            "position": "Data Analyst",
            "status": "active",
        },
    )
    assert duplicate_response.status_code == 409


def test_delete_employee_allows_employee_without_history(client):
    create_response = client.post(
        "/api/employees",
        json={
            "employee_code": "EMP-DELETE",
            "full_name": "Delete Me",
            "department": "Software Engineering",
            "position": "Software Engineer",
            "status": "active",
        },
    )
    assert create_response.status_code == 201

    delete_response = client.delete(f"/api/employees/{create_response.json()['id']}")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"ok": True}


def test_delete_employee_rejects_employee_with_attendance_history(client, db_session):
    employee = seed_employee(db_session, employee_code="E-HISTORY", department="IT")
    db_session.add(
        AttendanceEvent(
            employee_id=employee.id,
            action_type="check_in",
            attendance_status="recorded",
        )
    )
    db_session.commit()

    delete_response = client.delete(f"/api/employees/{employee.id}")

    assert delete_response.status_code == 409
    assert "Tạm ngưng" in delete_response.json()["detail"]
