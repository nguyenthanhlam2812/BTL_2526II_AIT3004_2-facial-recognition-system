from __future__ import annotations

from types import SimpleNamespace

from backend.app.models.user import User
from backend.app.security import get_password_hash, verify_password
from scripts.seed import seed_admin


def test_seed_admin_does_not_overwrite_existing_user(monkeypatch, db_session):
    existing_user = User(
        username="admin",
        password_hash=get_password_hash("current-pass-123"),
        role="viewer",
        is_active=False,
    )
    db_session.add(existing_user)
    db_session.commit()
    db_session.refresh(existing_user)

    monkeypatch.setattr(seed_admin, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        seed_admin,
        "get_settings",
        lambda: SimpleNamespace(
            seed_admin_username="admin",
            seed_admin_password="replace-with-demo-password",
        ),
    )

    seed_admin.main()

    persisted_user = db_session.query(User).filter_by(username="admin").one()
    assert verify_password("current-pass-123", persisted_user.password_hash)
    assert persisted_user.role == "viewer"
    assert persisted_user.is_active is False


def test_seed_admin_creates_missing_owner(monkeypatch, db_session):
    monkeypatch.setattr(seed_admin, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        seed_admin,
        "get_settings",
        lambda: SimpleNamespace(
            seed_admin_username="bootstrap-owner",
            seed_admin_password="bootstrap-owner-123",
        ),
    )

    seed_admin.main()

    created_user = db_session.query(User).filter_by(username="bootstrap-owner").one()
    assert verify_password("bootstrap-owner-123", created_user.password_hash)
    assert created_user.role == "owner"
    assert created_user.is_active is True
