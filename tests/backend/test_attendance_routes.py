from __future__ import annotations

from backend.app.api.routes import attendance as attendance_route
from backend.app.schemas.attendance import AttendanceEventListResponse, AttendanceFrameResponse
from backend.app.services.attendance_service import AttendanceValidationError

KIOSK_HEADERS = {"X-Kiosk-Token": "local-kiosk-token"}


def test_post_attendance_frame_requires_kiosk_token(client):
    response = client.post(
        "/api/attendance/frame",
        files={"image": ("frame.jpg", b"fake-image-bytes", "image/jpeg")},
        data={"action_type": "check_in"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid kiosk token."}


def test_post_attendance_frame_rejects_wrong_kiosk_token(client):
    response = client.post(
        "/api/attendance/frame",
        files={"image": ("frame.jpg", b"fake-image-bytes", "image/jpeg")},
        data={"action_type": "check_in"},
        headers={"X-Kiosk-Token": "wrong-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid kiosk token."}


def test_post_attendance_frame_returns_400_for_empty_file(client):
    response = client.post(
        "/api/attendance/frame",
        files={"image": ("empty.jpg", b"", "image/jpeg")},
        data={"action_type": "check_in"},
        headers=KIOSK_HEADERS,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Image file is empty."


def test_post_attendance_frame_maps_infrastructure_error_to_503(
    client,
    monkeypatch,
):
    def fake_service(*args, **kwargs):
        raise attendance_route.AttendanceInfrastructureError(
            "Attendance vector search is unavailable."
        )

    monkeypatch.setattr(
        attendance_route,
        "recognize_attendance_frame_service",
        fake_service,
    )

    response = client.post(
        "/api/attendance/frame",
        files={"image": ("frame.jpg", b"fake-image-bytes", "image/jpeg")},
        data={"action_type": "check_in"},
        headers=KIOSK_HEADERS,
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Attendance vector search is unavailable."


def test_post_attendance_frame_ignores_public_record_matched_flag(client, monkeypatch):
    captured = {}

    def fake_service(_db, **kwargs):
        captured.update(kwargs)
        return AttendanceFrameResponse(
            matched=True,
            employee=None,
            score=0.95,
            action_type="check_in",
            attendance_status="recorded",
            message="Check-in recorded.",
            event_id=101,
        )

    monkeypatch.setattr(
        attendance_route,
        "recognize_attendance_frame_service",
        fake_service,
    )

    response = client.post(
        "/api/attendance/frame",
        files={"image": ("frame.jpg", b"fake-image-bytes", "image/jpeg")},
        data={
            "action_type": "check_in",
            "record_unmatched": "false",
            "record_matched": "false",
            "camera_id": "kiosk-web",
        },
        headers=KIOSK_HEADERS,
    )

    assert response.status_code == 200
    assert captured["record_unmatched"] is False
    assert captured["camera_id"] == "kiosk-web"
    assert "record_matched" not in captured


def test_post_attendance_frame_rate_limits_after_ten_requests(client, monkeypatch):
    monkeypatch.setattr(
        attendance_route,
        "recognize_attendance_frame_service",
        lambda *_args, **_kwargs: AttendanceFrameResponse(
            matched=False,
            employee=None,
            score=None,
            action_type="check_in",
            attendance_status="unknown_face",
            message="No face detected.",
            event_id=None,
        ),
    )

    for _ in range(10):
        response = client.post(
            "/api/attendance/frame",
            files={"image": ("frame.jpg", b"fake-image-bytes", "image/jpeg")},
            data={"action_type": "check_in"},
            headers=KIOSK_HEADERS,
        )
        assert response.status_code == 200

    limited_response = client.post(
        "/api/attendance/frame",
        files={"image": ("frame.jpg", b"fake-image-bytes", "image/jpeg")},
        data={"action_type": "check_in"},
        headers=KIOSK_HEADERS,
    )

    assert limited_response.status_code == 429


def test_get_attendance_events_returns_service_payload(client, monkeypatch):
    monkeypatch.setattr(
        attendance_route,
        "list_attendance_events_service",
        lambda *args, **kwargs: AttendanceEventListResponse(items=[], total=0),
    )

    response = client.get("/api/attendance/events?page=1&page_size=20")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_export_attendance_events_csv_returns_attachment(client, monkeypatch):
    captured = {}

    def fake_service(_db, **kwargs):
        captured.update(kwargs)
        return "event_id,event_time\n1,2026-05-11T08:30:00"

    monkeypatch.setattr(
        attendance_route,
        "export_attendance_events_csv_service",
        fake_service,
    )

    response = client.get(
        "/api/attendance/events/export.csv",
        params={"employee_id": 3, "action_type": "check_in"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == 'attachment; filename="attendance-events.csv"'
    assert response.text.startswith("\ufeffevent_id,event_time")
    assert captured["employee_id"] == 3
    assert captured["action_type"] == "check_in"


def test_export_attendance_events_csv_returns_400_for_large_exports(client, monkeypatch):
    def fake_service(_db, **_kwargs):
        raise AttendanceValidationError(
            "Attendance event export exceeds 50000 rows. Narrow the filters and try again."
        )

    monkeypatch.setattr(
        attendance_route,
        "export_attendance_events_csv_service",
        fake_service,
    )

    response = client.get("/api/attendance/events/export.csv")

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Attendance event export exceeds 50000 rows. Narrow the filters and try again."
    )


def test_delete_attendance_events_returns_deleted_count(client, monkeypatch):
    monkeypatch.setattr(
        attendance_route,
        "delete_attendance_events_service",
        lambda *args, **kwargs: 7,
    )

    response = client.delete("/api/attendance/events")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "deleted_count": 7}


def test_delete_selected_attendance_events_returns_deleted_count(client, monkeypatch):
    captured = {}

    def fake_service(_db, ids):
        captured["ids"] = ids
        return 2

    monkeypatch.setattr(
        attendance_route,
        "delete_attendance_events_by_ids_service",
        fake_service,
    )

    response = client.request(
        "DELETE",
        "/api/attendance/events/selected",
        json={"ids": [3, 5]},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "deleted_count": 2}
    assert captured["ids"] == [3, 5]
