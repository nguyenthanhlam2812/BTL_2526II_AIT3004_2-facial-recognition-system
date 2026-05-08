from __future__ import annotations

from backend.app.api.routes import attendance as attendance_route
from backend.app.schemas.attendance import AttendanceEventListResponse


def test_post_attendance_frame_returns_400_for_empty_file(client):
    response = client.post(
        "/api/attendance/frame",
        files={"image": ("empty.jpg", b"", "image/jpeg")},
        data={"action_type": "check_in"},
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
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Attendance vector search is unavailable."


def test_get_attendance_events_returns_service_payload(client, monkeypatch):
    monkeypatch.setattr(
        attendance_route,
        "list_attendance_events_service",
        lambda *args, **kwargs: AttendanceEventListResponse(items=[], total=0),
    )

    response = client.get("/api/attendance/events?page=1&page_size=20")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}
