from __future__ import annotations

from backend.app.api.deps import require_admin, require_operator, require_owner
from backend.app.main import app


def test_viewer_can_read_admin_pages_but_cannot_mutate(client, db_session, admin_user):
    admin_user.role = "viewer"
    db_session.add(admin_user)
    db_session.commit()
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(require_operator, None)

    read_response = client.get("/api/employees")
    assert read_response.status_code == 200

    create_response = client.post(
        "/api/employees",
        json={
            "employee_code": "E-VIEWER",
            "full_name": "Viewer Should Not Create",
            "department": "IT",
            "position": "Viewer",
            "status": "active",
        },
    )
    assert create_response.status_code == 403
    assert create_response.json() == {"detail": "Owner or admin role is required."}

    app.dependency_overrides.pop(require_owner, None)
    system_response = client.get("/api/system/settings")
    assert system_response.status_code == 403
    assert system_response.json() == {"detail": "Owner role is required."}
