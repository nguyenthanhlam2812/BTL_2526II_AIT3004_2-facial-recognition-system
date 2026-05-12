from __future__ import annotations

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
from backend.app.main import app
from backend.app.models.user import User
from backend.app.services import attendance_service


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
    attendance_service._clear_all_camera_match_gates()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        attendance_service._clear_all_camera_match_gates()


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

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
