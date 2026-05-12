from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.app.config import get_settings


def get_rate_limit_key(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip

    real_ip = request.headers.get("X-Real-IP", "").strip()
    if real_ip:
        return real_ip

    return get_remote_address(request)


limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri=get_settings().rate_limit_storage_uri,
    default_limits=[],
    headers_enabled=True,
)
