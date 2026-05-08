from __future__ import annotations

from sqlalchemy import func, select

from backend.app.models.attendance_event import AttendanceEvent
from backend.app.models.employee import Employee
from backend.app.services import attendance_service
from backend.app.services.qdrant_service import FaceSearchResult


def test_recognize_attendance_frame_returns_unknown_face_when_no_face(
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        attendance_service,
        "analyze_image_bytes",
        lambda _: {
            "status": "failed",
            "faces_detected": 0,
            "error_message": "No face detected.",
        },
    )

    response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=None,
        camera_id="cam-01",
    )

    assert response.matched is False
    assert response.attendance_status == "unknown_face"
    assert response.message == "No face detected."
    assert db_session.scalar(select(func.count()).select_from(AttendanceEvent)) == 1


def test_recognize_attendance_frame_returns_multiple_faces(
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        attendance_service,
        "analyze_image_bytes",
        lambda _: {
            "status": "failed",
            "faces_detected": 2,
            "error_message": "Multiple faces detected.",
        },
    )

    response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=None,
        camera_id="cam-01",
    )

    assert response.matched is False
    assert response.attendance_status == "multiple_faces"
    assert response.message == "Multiple faces detected."
    assert db_session.scalar(select(func.count()).select_from(AttendanceEvent)) == 1


def test_recognize_attendance_frame_returns_unknown_face_when_qdrant_has_no_match(
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        attendance_service,
        "analyze_image_bytes",
        lambda _: {
            "status": "success",
            "faces_detected": 1,
            "error_message": None,
            "embedding": [0.1] * 512,
        },
    )
    monkeypatch.setattr(attendance_service, "search_face_embedding", lambda **_: None)

    response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=None,
        camera_id="cam-01",
    )

    assert response.matched is False
    assert response.attendance_status == "unknown_face"
    assert response.message == "Face not recognized."
    assert db_session.scalar(select(func.count()).select_from(AttendanceEvent)) == 1


def test_recognize_attendance_frame_returns_unknown_face_when_score_below_threshold(
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        attendance_service,
        "analyze_image_bytes",
        lambda _: {
            "status": "success",
            "faces_detected": 1,
            "error_message": None,
            "embedding": [0.1] * 512,
        },
    )
    monkeypatch.setattr(
        attendance_service,
        "search_face_embedding",
        lambda **_: FaceSearchResult(
            employee_id=123,
            score=0.1,
            payload={},
            point_id="point-1",
        ),
    )

    response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=None,
        camera_id="cam-01",
    )

    assert response.matched is False
    assert response.attendance_status == "unknown_face"
    assert response.score == 0.1
    assert db_session.scalar(select(func.count()).select_from(AttendanceEvent)) == 1


def test_recognize_attendance_frame_returns_recorded_when_match_succeeds(
    db_session,
    monkeypatch,
):
    employee = Employee(
        employee_code="E001",
        full_name="Nguyen Van A",
        department="IT",
        position="Engineer",
        status="active",
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)

    monkeypatch.setattr(
        attendance_service,
        "analyze_image_bytes",
        lambda _: {
            "status": "success",
            "faces_detected": 1,
            "error_message": None,
            "embedding": [0.1] * 512,
        },
    )
    monkeypatch.setattr(
        attendance_service,
        "search_face_embedding",
        lambda **_: FaceSearchResult(
            employee_id=employee.id,
            score=0.95,
            payload={},
            point_id="point-1",
        ),
    )

    response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=None,
        camera_id="cam-01",
    )

    assert response.matched is True
    assert response.attendance_status == "recorded"
    assert response.employee is not None
    assert response.employee.id == employee.id
    assert response.message == "Check-in recorded."
    assert db_session.scalar(select(func.count()).select_from(AttendanceEvent)) == 1
