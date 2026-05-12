from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.config import (
    DEFAULT_KIOSK_API_TOKEN,
    DEFAULT_JWT_SECRET_KEY,
    DEFAULT_SEED_ADMIN_PASSWORD,
    DEFAULT_SEED_ADMIN_USERNAME,
    RuntimeConfigurationError,
)
from backend.app.main import create_app
from backend.app.security import get_password_hash


def _set_admin_password(db_session, admin_user, password: str) -> None:
    admin_user.password_hash = get_password_hash(password)
    db_session.add(admin_user)
    db_session.commit()


def test_login_allows_default_admin_in_local_mode(client, db_session, admin_user):
    _set_admin_password(db_session, admin_user, DEFAULT_SEED_ADMIN_PASSWORD)

    response = client.post(
        "/api/auth/login",
        json={
            "username": DEFAULT_SEED_ADMIN_USERNAME,
            "password": DEFAULT_SEED_ADMIN_PASSWORD,
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["username"] == DEFAULT_SEED_ADMIN_USERNAME
    assert response.json()["access_token"]


def test_public_demo_mode_requires_non_default_admin_password(monkeypatch):
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("JWT_SECRET_KEY", "replace-with-a-strong-secret")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", DEFAULT_SEED_ADMIN_PASSWORD)
    monkeypatch.setenv("WARMUP_FACE_MODEL", "false")

    with pytest.raises(RuntimeConfigurationError, match="SEED_ADMIN_PASSWORD"):
        with TestClient(create_app()):
            pass


def test_public_demo_mode_requires_non_default_jwt_secret(monkeypatch):
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("JWT_SECRET_KEY", DEFAULT_JWT_SECRET_KEY)
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "replace-with-a-demo-password")
    monkeypatch.setenv("WARMUP_FACE_MODEL", "false")

    with pytest.raises(RuntimeConfigurationError, match="JWT_SECRET_KEY"):
        with TestClient(create_app()):
            pass


def test_public_demo_mode_requires_non_default_kiosk_token(monkeypatch):
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("JWT_SECRET_KEY", "replace-with-a-strong-secret")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "replace-with-a-demo-password")
    monkeypatch.setenv("KIOSK_API_TOKEN", DEFAULT_KIOSK_API_TOKEN)
    monkeypatch.setenv("WARMUP_FACE_MODEL", "false")

    with pytest.raises(RuntimeConfigurationError, match="KIOSK_API_TOKEN"):
        with TestClient(create_app()):
            pass


def test_public_demo_mode_starts_with_strong_secrets(monkeypatch):
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("JWT_SECRET_KEY", "replace-with-a-strong-secret")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "replace-with-a-demo-password")
    monkeypatch.setenv("KIOSK_API_TOKEN", "replace-with-a-kiosk-token")
    monkeypatch.setenv("WARMUP_FACE_MODEL", "false")

    with TestClient(create_app()) as test_client:
        response = test_client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_change_password_updates_admin_credentials(client, db_session, admin_user):
    _set_admin_password(db_session, admin_user, "admin123")

    response = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "admin123",
            "new_password": "new-admin-123",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "message": "Password updated successfully.",
    }

    old_login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "new-admin-123"},
    )
    assert new_login.status_code == 200


def test_change_password_rejects_wrong_current_password(client, db_session, admin_user):
    _set_admin_password(db_session, admin_user, "admin123")

    response = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "wrong-password",
            "new_password": "new-admin-123",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Current password is incorrect."}


def test_change_password_rejects_same_password(client, db_session, admin_user):
    _set_admin_password(db_session, admin_user, "admin123")

    response = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "admin123",
            "new_password": "admin123",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "New password must be different from the current password."
    }
