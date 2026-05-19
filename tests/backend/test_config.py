from __future__ import annotations

from backend.app.config import Settings, get_settings


def test_rate_limit_storage_uri_falls_back_to_redis_url_when_not_set(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_STORAGE_URI", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://fallback-host:6379/9")
    get_settings.cache_clear()
    settings = Settings()
    assert settings.rate_limit_storage_uri == "redis://fallback-host:6379/9"


def test_rate_limit_storage_uri_uses_explicit_value_when_provided(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_STORAGE_URI", "memory://")
    monkeypatch.setenv("REDIS_URL", "redis://should-not-be-used:6379/9")
    get_settings.cache_clear()
    settings = Settings()
    assert settings.rate_limit_storage_uri == "memory://"
