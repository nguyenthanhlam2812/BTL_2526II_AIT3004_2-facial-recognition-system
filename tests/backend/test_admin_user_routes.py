from __future__ import annotations

from backend.app.api.deps import require_owner
from backend.app.main import app
from backend.app.models.user import User


def test_owner_can_create_update_reset_and_delete_admin_user(client):
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
    created = create_response.json()
    assert created["username"] == "ops-admin"
    assert created["role"] == "admin"

    list_response = client.get("/api/admin/users")
    assert list_response.status_code == 200
    assert any(item["username"] == "ops-admin" for item in list_response.json()["items"])

    update_response = client.put(
        f"/api/admin/users/{created['id']}",
        json={"username": "read-only", "role": "viewer", "is_active": True},
    )
    assert update_response.status_code == 200
    assert update_response.json()["username"] == "read-only"
    assert update_response.json()["role"] == "viewer"

    reset_response = client.post(
        f"/api/admin/users/{created['id']}/reset-password",
        json={"password": "viewer-pass-123"},
    )
    assert reset_response.status_code == 200
    assert reset_response.json()["ok"] is True

    login_response = client.post(
        "/api/auth/login",
        json={"username": "read-only", "password": "viewer-pass-123"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["role"] == "viewer"

    delete_response = client.delete(f"/api/admin/users/{created['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"ok": True}


def test_create_admin_user_rejects_duplicate_username(client):
    first_response = client.post(
        "/api/admin/users",
        json={
            "username": "duplicate",
            "password": "duplicate-123",
            "role": "admin",
            "is_active": True,
        },
    )
    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/api/admin/users",
        json={
            "username": "DUPLICATE",
            "password": "duplicate-456",
            "role": "admin",
            "is_active": True,
        },
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == {"detail": "Username already exists."}


def test_create_admin_user_normalizes_username(client):
    response = client.post(
        "/api/admin/users",
        json={
            "username": "  Ops.Admin_01  ",
            "password": "ops-admin-123",
            "role": "admin",
            "is_active": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["username"] == "ops.admin_01"


def test_create_admin_user_rejects_invalid_username_and_weak_password(client):
    invalid_username = client.post(
        "/api/admin/users",
        json={
            "username": "ops admin",
            "password": "ops-admin-123",
            "role": "admin",
            "is_active": True,
        },
    )
    assert invalid_username.status_code == 422

    weak_password = client.post(
        "/api/admin/users",
        json={
            "username": "weak-user",
            "password": "password",
            "role": "admin",
            "is_active": True,
        },
    )
    assert weak_password.status_code == 422


def test_owner_cannot_delete_self(client, admin_user):
    response = client.delete(f"/api/admin/users/{admin_user.id}")

    assert response.status_code == 400
    assert response.json() == {"detail": "You cannot delete your own account."}


def test_owner_cannot_demote_last_active_owner(client, admin_user):
    response = client.put(
        f"/api/admin/users/{admin_user.id}",
        json={"role": "admin", "is_active": True},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "At least one active owner must remain."}


def test_non_owner_cannot_manage_admin_users(client, db_session, admin_user):
    admin_user.role = "admin"
    db_session.add(admin_user)
    db_session.commit()
    app.dependency_overrides.pop(require_owner, None)

    response = client.get("/api/admin/users")

    assert response.status_code == 403
    assert response.json() == {"detail": "Owner role is required."}


def test_inactive_user_cannot_login(client, db_session):
    inactive = User(
        username="inactive-admin",
        password_hash="$pbkdf2-sha256$29000$invalid",
        role="admin",
        is_active=False,
    )
    db_session.add(inactive)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"username": "inactive-admin", "password": "anything"},
    )

    assert response.status_code == 401
