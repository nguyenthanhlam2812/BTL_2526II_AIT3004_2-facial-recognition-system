from __future__ import annotations

import json

from backend.app.api.deps import require_owner
from backend.app.main import app


def test_get_system_settings_returns_safe_admin_config(client):
    response = client.get("/api/system/settings")

    assert response.status_code == 200
    data = response.json()

    assert data["attendance_threshold"] > 0
    assert data["fields"]
    assert any(field["key"] == "attendance_threshold" for field in data["fields"])
    assert data["business_timezone"] == "Asia/Ho_Chi_Minh"
    assert data["insightface_model_name"]
    assert data["face_min_det_score"] > 0
    assert data["face_min_area_ratio"] > 0
    assert data["face_secondary_area_ratio"] > 0
    assert "host" in data["redis"]
    assert "database" in data["redis"]

    serialized = json.dumps(data).lower()
    for forbidden in (
        "jwt_secret_key",
        "mysql_password",
        "mysql_root_password",
        "minio_access_key",
        "minio_secret_key",
        "change-me",
        "app_password",
        "root_password",
        "minioadmin",
    ):
        assert forbidden not in serialized


def test_owner_can_update_and_reset_system_settings(client):
    original_response = client.get("/api/system/settings")
    assert original_response.status_code == 200
    original = original_response.json()

    update_response = client.patch(
        "/api/system/settings",
        json={
            "attendance_threshold": 0.77,
            "business_timezone": "UTC",
            "warmup_face_model": True,
        },
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["attendance_threshold"] == 0.77
    assert data["business_timezone"] == "UTC"
    assert data["warmup_face_model"] is True
    assert _field_source(data, "attendance_threshold") == "db"
    assert _field_source(data, "business_timezone") == "db"

    reset_response = client.post(
        "/api/system/settings/reset",
        json={"keys": ["attendance_threshold", "business_timezone", "warmup_face_model"]},
    )

    assert reset_response.status_code == 200
    reset_data = reset_response.json()
    assert reset_data["attendance_threshold"] == original["attendance_threshold"]
    assert reset_data["business_timezone"] == original["business_timezone"]
    assert reset_data["warmup_face_model"] == original["warmup_face_model"]
    assert _field_source(reset_data, "attendance_threshold") == "env"


def test_partial_settings_update_keeps_untouched_fields_on_env_source(client):
    response = client.patch(
        "/api/system/settings",
        json={"attendance_threshold": 0.77},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["attendance_threshold"] == 0.77
    assert _field_source(data, "attendance_threshold") == "db"
    assert _field_source(data, "business_timezone") == "env"
    assert _field_source(data, "face_min_det_score") == "env"


def test_system_settings_reject_invalid_values(client):
    response = client.patch(
        "/api/system/settings",
        json={"attendance_threshold": 0},
    )

    assert response.status_code == 422


def test_non_owner_cannot_update_system_settings(client, db_session, admin_user):
    admin_user.role = "admin"
    db_session.add(admin_user)
    db_session.commit()
    app.dependency_overrides.pop(require_owner, None)

    response = client.patch(
        "/api/system/settings",
        json={"attendance_threshold": 0.8},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Owner role is required."}


def _field_source(data: dict, key: str) -> str:
    field = next(item for item in data["fields"] if item["key"] == key)
    return field["source"]
