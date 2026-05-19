from __future__ import annotations

from datetime import datetime, timedelta, timezone

import fakeredis
import pytest

from backend.app.services import camera_gate_service
from backend.app.services.camera_gate_service import CameraGateRecord


@pytest.fixture()
def fake_redis():
    fake = fakeredis.FakeRedis(decode_responses=True)
    camera_gate_service.reset_client(fake)
    yield fake
    camera_gate_service.reset_client(None)
    fake.flushall()


def _record(employee_id: int = 7, event_id: int = 101) -> CameraGateRecord:
    return CameraGateRecord(
        employee_id=employee_id,
        event_id=event_id,
        updated_at=datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_set_then_get_round_trips_the_record(fake_redis):
    camera_gate_service.set_gate("kiosk-1", "check_in", record=_record())
    loaded = camera_gate_service.get_gate("kiosk-1", "check_in")
    assert loaded is not None
    assert loaded.employee_id == 7
    assert loaded.event_id == 101


def test_get_returns_none_when_key_missing(fake_redis):
    assert camera_gate_service.get_gate("kiosk-2", "check_in") is None


def test_set_writes_with_expected_ttl(fake_redis):
    camera_gate_service.set_gate("kiosk-1", "check_in", record=_record())
    ttl = fake_redis.ttl("camera_gate:kiosk-1:check_in")
    assert 0 < ttl <= camera_gate_service.CAMERA_GATE_TTL_SECONDS


def test_clear_gate_removes_the_key(fake_redis):
    camera_gate_service.set_gate("kiosk-1", "check_in", record=_record())
    camera_gate_service.clear_gate("kiosk-1", "check_in")
    assert camera_gate_service.get_gate("kiosk-1", "check_in") is None


def test_clear_all_gates_wipes_only_camera_gate_keys(fake_redis):
    camera_gate_service.set_gate("kiosk-1", "check_in", record=_record())
    camera_gate_service.set_gate("kiosk-2", "check_out", record=_record(event_id=202))
    fake_redis.set("rate_limit:foo", "x")  # unrelated key must survive
    camera_gate_service.clear_all_gates()
    assert camera_gate_service.get_gate("kiosk-1", "check_in") is None
    assert camera_gate_service.get_gate("kiosk-2", "check_out") is None
    assert fake_redis.get("rate_limit:foo") == "x"


def test_clear_gates_for_event_ids_filters_by_event_id(fake_redis):
    camera_gate_service.set_gate("kiosk-1", "check_in", record=_record(event_id=101))
    camera_gate_service.set_gate("kiosk-2", "check_in", record=_record(event_id=202))
    camera_gate_service.clear_gates_for_event_ids({202})
    assert camera_gate_service.get_gate("kiosk-1", "check_in") is not None
    assert camera_gate_service.get_gate("kiosk-2", "check_in") is None


def test_encode_normalizes_non_utc_input_to_utc(fake_redis):
    # 19:00 UTC+7 == 12:00 UTC. The encoder must persist UTC regardless of
    # the input timezone so two backend instances with different container
    # TZ produce identical Redis payloads. Using a fixed offset instead of
    # ZoneInfo avoids depending on the system tzdata package.
    ict = timezone(timedelta(hours=7))
    ict_time = datetime(2026, 5, 17, 19, 0, 0, tzinfo=ict)
    camera_gate_service.set_gate(
        "cam-01",
        "check_in",
        record=CameraGateRecord(employee_id=1, event_id=1, updated_at=ict_time),
    )
    record = camera_gate_service.get_gate("cam-01", "check_in")
    assert record is not None
    assert record.updated_at == datetime(2026, 5, 17, 12, 0, 0)


def test_operations_fail_open_when_client_is_unavailable(monkeypatch):
    camera_gate_service.reset_client(None)
    monkeypatch.setattr(camera_gate_service, "_make_client", lambda: None)
    # Each call must be a silent no-op / safe default — no exception should leak.
    assert camera_gate_service.get_gate("kiosk-1", "check_in") is None
    camera_gate_service.set_gate("kiosk-1", "check_in", record=_record())
    camera_gate_service.clear_gate("kiosk-1", "check_in")
    camera_gate_service.clear_all_gates()
    camera_gate_service.clear_gates_for_event_ids({1, 2})
