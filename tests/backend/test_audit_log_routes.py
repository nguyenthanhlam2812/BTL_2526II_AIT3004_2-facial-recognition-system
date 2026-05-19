from __future__ import annotations

import json

from backend.app.api.deps import require_owner
from backend.app.api.routes import enrollments as enrollments_route
from backend.app.main import app
from backend.app.models.attendance_event import AttendanceEvent
from backend.app.models.employee import Employee
from backend.app.models.enrollment import Enrollment
from backend.app.security import get_password_hash


def test_owner_can_list_audit_logs_and_non_owner_is_forbidden(client, db_session, admin_user):
    create_response = client.post(
        "/api/admin/users",
        json={
            "username": "ops-admin",
            "password": "ops-admin-123",
            "role": "admin",
            "is_active": True,
        },
    )
    assert create_response.status_code == 201

    owner_response = client.get("/api/audit/logs", params={"action": "admin_user.create"})
    assert owner_response.status_code == 200
    owner_payload = owner_response.json()
    assert owner_payload["total"] == 1
    assert owner_payload["items"][0]["actor_username"] == "admin"
    assert owner_payload["items"][0]["resource_label"] == "ops-admin"

    admin_user.role = "admin"
    db_session.add(admin_user)
    db_session.commit()
    app.dependency_overrides.pop(require_owner, None)

    forbidden_response = client.get("/api/audit/logs")
    assert forbidden_response.status_code == 403
    assert forbidden_response.json() == {"detail": "Owner role is required."}


def test_admin_user_and_change_password_audit_logs_do_not_store_passwords(
    client,
    db_session,
    admin_user,
):
    create_response = client.post(
        "/api/admin/users",
        json={
            "username": "viewer-demo",
            "password": "viewer-demo-123",
            "role": "viewer",
            "is_active": True,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()

    reset_response = client.post(
        f"/api/admin/users/{created['id']}/reset-password",
        json={"password": "reset-secret-123"},
    )
    assert reset_response.status_code == 200

    admin_user.password_hash = get_password_hash("old-admin-123")
    db_session.add(admin_user)
    db_session.commit()
    change_response = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "old-admin-123",
            "new_password": "new-admin-456",
        },
    )
    assert change_response.status_code == 200

    logs_response = client.get("/api/audit/logs", params={"page_size": 20})
    assert logs_response.status_code == 200
    payload = logs_response.json()
    actions = {item["action"] for item in payload["items"]}
    assert {"admin_user.create", "admin_user.reset_password", "auth.change_password"} <= actions

    serialized = json.dumps(payload).lower()
    assert "viewer-demo-123" not in serialized
    assert "reset-secret-123" not in serialized
    assert "old-admin-123" not in serialized
    assert "new-admin-456" not in serialized


def test_employee_and_system_setting_actions_create_audit_logs(client):
    create_response = client.post(
        "/api/employees",
        json={
            "employee_code": "EMP0001",
            "full_name": "Nguyen Van A",
            "department": "IT",
            "position": "Engineer",
            "status": "active",
        },
    )
    assert create_response.status_code == 201
    employee = create_response.json()

    update_response = client.put(
        f"/api/employees/{employee['id']}",
        json={
            "employee_code": "EMP0001",
            "full_name": "Nguyen Van A",
            "department": "HR",
            "position": "Engineer",
            "status": "inactive",
        },
    )
    assert update_response.status_code == 200

    settings_response = client.patch(
        "/api/system/settings",
        json={"attendance_threshold": 0.77, "business_timezone": "UTC"},
    )
    assert settings_response.status_code == 200

    reset_response = client.post(
        "/api/system/settings/reset",
        json={"keys": ["attendance_threshold", "business_timezone"]},
    )
    assert reset_response.status_code == 200

    logs_response = client.get("/api/audit/logs", params={"page_size": 20})
    assert logs_response.status_code == 200
    logs = logs_response.json()["items"]
    actions = {item["action"] for item in logs}
    assert {
        "employee.create",
        "employee.update",
        "system_setting.update",
        "system_setting.reset",
    } <= actions

    employee_log = next(item for item in logs if item["action"] == "employee.update")
    assert employee_log["resource_id"] == str(employee["id"])
    assert employee_log["metadata"]["department"] == "HR"

    settings_log = next(item for item in logs if item["action"] == "system_setting.update")
    assert settings_log["metadata"]["keys"] == ["attendance_threshold", "business_timezone"]


def test_enrollment_submit_and_attendance_delete_create_audit_logs(
    client,
    db_session,
    monkeypatch,
):
    employee = Employee(
        employee_code="EMP0002",
        full_name="Nguyen Van B",
        department="IT",
        position="Engineer",
        status="active",
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)

    def fake_create_enrollment(db, employee_id, files):
        enrollment = Enrollment(
            job_id="job_audit_123",
            employee_id=employee_id,
            status="pending",
            uploaded_count=len(files),
            processed_count=0,
            failed_count=0,
            message="queued",
        )
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
        return enrollment

    monkeypatch.setattr(
        enrollments_route,
        "create_enrollment_service",
        fake_create_enrollment,
    )

    enrollment_response = client.post(
        f"/api/employees/{employee.id}/enrollments",
        files=[("files", ("face.jpg", b"fake-image-bytes", "image/jpeg"))],
    )
    assert enrollment_response.status_code == 201

    event_one = AttendanceEvent(action_type="check_in", attendance_status="unknown_face")
    event_two = AttendanceEvent(action_type="check_out", attendance_status="recorded")
    db_session.add_all([event_one, event_two])
    db_session.commit()
    db_session.refresh(event_one)
    db_session.refresh(event_two)

    selected_response = client.request(
        "DELETE",
        "/api/attendance/events/selected",
        json={"ids": [event_one.id]},
    )
    assert selected_response.status_code == 200
    assert selected_response.json()["deleted_count"] == 1

    all_response = client.delete("/api/attendance/events")
    assert all_response.status_code == 200
    assert all_response.json()["deleted_count"] == 1

    logs_response = client.get("/api/audit/logs", params={"page_size": 20})
    assert logs_response.status_code == 200
    logs = logs_response.json()["items"]
    actions = {item["action"] for item in logs}
    assert {
        "enrollment.submit",
        "attendance_event.delete_selected",
        "attendance_event.delete_all",
    } <= actions

    enrollment_log = next(item for item in logs if item["action"] == "enrollment.submit")
    assert enrollment_log["metadata"]["job_id"] == "job_audit_123"
    assert enrollment_log["metadata"]["employee_id"] == employee.id

    selected_log = next(
        item for item in logs if item["action"] == "attendance_event.delete_selected"
    )
    assert selected_log["metadata"]["deleted_count"] == 1
    assert selected_log["metadata"]["event_ids"] == [event_one.id]
