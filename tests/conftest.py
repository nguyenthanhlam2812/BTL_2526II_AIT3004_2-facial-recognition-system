from __future__ import annotations

import os

# Keep rate limiter in-memory for tests so they don't depend on a live Redis.
os.environ.setdefault("RATE_LIMIT_STORAGE_URI", "memory://")

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.models  # noqa: F401
from backend.app.api.deps import (
    get_current_user,
    require_admin,
    require_operator,
    require_owner,
)
from backend.app.config import get_settings
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.default_lookups import DEFAULT_DEPARTMENTS, DEFAULT_POSITIONS
from backend.app.models.department import Department
from backend.app.models.position import Position
from backend.app.main import app
from backend.app.models.user import User
from backend.app.services import attendance_service, camera_gate_service


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    try:
        yield
    finally:
        get_settings.cache_clear()


@pytest.fixture()
def db_session():
    # Wire a fresh in-memory Redis stub into the camera-gate service for each
    # test so the dedupe window is deterministic and tests stay isolated.
    fake = fakeredis.FakeRedis(decode_responses=True)
    camera_gate_service.reset_client(fake)
    attendance_service._clear_all_camera_match_gates()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    _seed_default_lookups(db)
    try:
        yield db
    finally:
        db.close()
        attendance_service._clear_all_camera_match_gates()
        camera_gate_service.reset_client(None)
        try:
            fake.flushall()
        except Exception:
            pass


@pytest.fixture()
def admin_user(db_session):
    user = User(
        username="admin",
        password_hash="not-used-in-tests",
        role="owner",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def client(db_session, admin_user):
    def override_get_db():
        yield db_session

    def override_require_admin():
        return admin_user

    def override_require_operator():
        return admin_user

    def override_require_owner():
        return admin_user

    def override_get_current_user():
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_admin] = override_require_admin
    app.dependency_overrides[require_operator] = override_require_operator
    app.dependency_overrides[require_owner] = override_require_owner

    _reset_rate_limits()
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    _reset_rate_limits()


def _reset_rate_limits():
    limiter = getattr(app.state, "limiter", None)
    storage = getattr(limiter, "_storage", None)
    if storage is None:
        return

    reset = getattr(storage, "reset", None)
    if callable(reset):
        reset()


def _seed_default_lookups(db: Session) -> None:
    db.add_all(
        [Department(name=name) for name in DEFAULT_DEPARTMENTS]
        + [Position(name=name) for name in DEFAULT_POSITIONS]
    )
    db.commit()
