from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import redis
import structlog

from backend.app.config import get_settings


CAMERA_GATE_TTL_SECONDS = 300  # 5 minutes, matches CAMERA_MATCH_GATE_TTL.
KEY_PREFIX = "camera_gate"

logger = structlog.get_logger(__name__)


@dataclass
class CameraGateRecord:
    employee_id: int
    event_id: int
    updated_at: datetime


_client: redis.Redis | None = None
_client_lock = threading.Lock()


def _make_client() -> redis.Redis | None:
    settings = get_settings()
    try:
        # from_url only parses the URL; actual connection happens lazily on
        # the first command. We catch ValueError for malformed REDIS_URL so a
        # bad config does not crash the whole backend — connection errors are
        # caught later inside each operation.
        return redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
        )
    except ValueError:
        logger.exception("camera_gate.redis_init_failed")
        return None


def _get_client() -> redis.Redis | None:
    # Double-checked locking: the fast path stays lock-free, and only the
    # very first concurrent callers contend on the lock during init.
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = _make_client()
    return _client


def reset_client(client: redis.Redis | None) -> None:
    """Override the cached client. Tests inject a fakeredis instance via this."""
    global _client
    with _client_lock:
        _client = client


def _key(camera_id: str, action_type: str) -> str:
    return f"{KEY_PREFIX}:{camera_id}:{action_type}"


def _encode(record: CameraGateRecord) -> str:
    # Persist updated_at as a UTC-naive ISO string. astimezone(timezone.utc)
    # converts an aware datetime regardless of input TZ; astimezone(tz=None)
    # would have used the container's local TZ which is non-deterministic
    # across instances.
    updated = record.updated_at
    if updated.tzinfo is not None:
        updated = updated.astimezone(timezone.utc).replace(tzinfo=None)
    return json.dumps(
        {
            "employee_id": record.employee_id,
            "event_id": record.event_id,
            "updated_at": updated.isoformat(),
        }
    )


def _decode(payload: str) -> CameraGateRecord | None:
    try:
        data = json.loads(payload)
        return CameraGateRecord(
            employee_id=int(data["employee_id"]),
            event_id=int(data["event_id"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        logger.warning("camera_gate.decode_failed")
        return None


def get_gate(camera_id: str, action_type: str) -> CameraGateRecord | None:
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(_key(camera_id, action_type))
    except redis.RedisError:
        logger.warning("camera_gate.redis_get_failed", camera_id=camera_id)
        return None
    if raw is None:
        return None
    return _decode(raw)


def set_gate(camera_id: str, action_type: str, *, record: CameraGateRecord) -> None:
    client = _get_client()
    if client is None:
        logger.warning("camera_gate.redis_unavailable_on_set", camera_id=camera_id)
        return
    try:
        client.set(
            _key(camera_id, action_type),
            _encode(record),
            ex=CAMERA_GATE_TTL_SECONDS,
        )
    except redis.RedisError:
        logger.warning("camera_gate.redis_set_failed", camera_id=camera_id)


def clear_gate(camera_id: str, action_type: str) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.delete(_key(camera_id, action_type))
    except redis.RedisError:
        logger.warning("camera_gate.redis_del_failed", camera_id=camera_id)


def clear_all_gates() -> None:
    client = _get_client()
    if client is None:
        return
    try:
        for key in client.scan_iter(match=f"{KEY_PREFIX}:*"):
            client.delete(key)
    except redis.RedisError:
        logger.warning("camera_gate.redis_clear_all_failed")


def clear_gates_for_event_ids(event_ids: Iterable[int]) -> None:
    event_id_set = {int(eid) for eid in event_ids}
    if not event_id_set:
        return
    client = _get_client()
    if client is None:
        return
    try:
        for key in client.scan_iter(match=f"{KEY_PREFIX}:*"):
            raw = client.get(key)
            if raw is None:
                continue
            record = _decode(raw)
            if record is not None and record.event_id in event_id_set:
                client.delete(key)
    except redis.RedisError:
        logger.warning("camera_gate.redis_clear_for_events_failed")
