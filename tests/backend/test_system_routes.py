from __future__ import annotations

import json


def test_get_system_settings_returns_safe_admin_config(client):
    response = client.get("/api/system/settings")

    assert response.status_code == 200
    data = response.json()

    assert data["attendance_threshold"] > 0
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
