from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from backend.app.models.attendance_event import AttendanceEvent
from backend.app.models.employee import Employee
from backend.app.models.system_setting import SystemSetting
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


def test_recognize_attendance_frame_can_skip_unmatched_event(
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
        camera_id="kiosk-auto",
        record_unmatched=False,
    )

    assert response.matched is False
    assert response.attendance_status == "unknown_face"
    assert response.event_id is None
    assert db_session.scalar(select(func.count()).select_from(AttendanceEvent)) == 0


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
    monkeypatch.setattr(attendance_service, "search_face_embeddings", lambda **_: [])

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
        "search_face_embeddings",
        lambda **_: [
            FaceSearchResult(
                employee_id=123,
                score=0.1,
                payload={},
                point_id="point-1",
            )
        ],
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


def test_recognize_attendance_frame_uses_db_attendance_threshold(
    db_session,
    monkeypatch,
):
    employee = Employee(
        employee_code="E001-THRESHOLD",
        full_name="Threshold User",
        department="IT",
        position="Engineer",
        status="active",
    )
    db_session.add_all(
        [
            employee,
            SystemSetting(
                key="attendance_threshold",
                value="0.99",
                updated_by_user_id=None,
            ),
        ]
    )
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
        "search_face_embeddings",
        lambda **_: [
            FaceSearchResult(
                employee_id=employee.id,
                score=0.95,
                payload={},
                point_id="point-1",
            )
        ],
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
    assert response.message == "Face not recognized."


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
        "search_face_embeddings",
        lambda **_: [
            FaceSearchResult(
                employee_id=employee.id,
                score=0.95,
                payload={},
                point_id="point-1",
            )
        ],
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


def test_recognize_attendance_frame_deduplicates_same_camera_employee_until_clear(
    db_session,
    monkeypatch,
):
    employee = Employee(
        employee_code="E001-CAMERA-GATE",
        full_name="Nguyen Van Camera Gate",
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
        "search_face_embeddings",
        lambda **_: [
            FaceSearchResult(
                employee_id=employee.id,
                score=0.95,
                payload={},
                point_id="point-1",
            )
        ],
    )

    response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=None,
        camera_id="kiosk-auto",
        record_unmatched=False,
    )
    recorded_event = db_session.get(AttendanceEvent, response.event_id)
    assert recorded_event is not None
    recorded_event.created_at = datetime.utcnow() - timedelta(seconds=30)
    db_session.commit()

    second_response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=None,
        camera_id="kiosk-auto",
        record_unmatched=False,
    )

    assert response.matched is True
    assert response.event_id is not None
    assert second_response.event_id == response.event_id
    assert second_response.message == "Check-in already recorded recently."
    assert db_session.scalar(select(func.count()).select_from(AttendanceEvent)) == 1


def test_recognize_attendance_frame_records_new_employee_without_empty_frame(
    db_session,
    monkeypatch,
):
    employee_a = Employee(
        employee_code="E001-A",
        full_name="Nguyen Van A",
        department="IT",
        position="Engineer",
        status="active",
    )
    employee_b = Employee(
        employee_code="E001-B",
        full_name="Tran Thi B",
        department="IT",
        position="Engineer",
        status="active",
    )
    db_session.add_all([employee_a, employee_b])
    db_session.commit()
    db_session.refresh(employee_a)
    db_session.refresh(employee_b)

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
    next_employee_id = {"value": employee_a.id}

    def fake_search(**_kwargs):
        return [
            FaceSearchResult(
                employee_id=next_employee_id["value"],
                score=0.95,
                payload={},
                point_id="point-1",
            )
        ]

    monkeypatch.setattr(attendance_service, "search_face_embeddings", fake_search)

    first_response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=None,
        camera_id="kiosk-auto",
        record_unmatched=False,
    )
    next_employee_id["value"] = employee_b.id
    second_response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=None,
        camera_id="kiosk-auto",
        record_unmatched=False,
    )

    assert first_response.employee is not None
    assert first_response.employee.id == employee_a.id
    assert second_response.employee is not None
    assert second_response.employee.id == employee_b.id
    assert second_response.event_id != first_response.event_id
    assert db_session.scalar(select(func.count()).select_from(AttendanceEvent)) == 2


def test_recognize_attendance_frame_deduplicates_recent_recorded_match(
    db_session,
    monkeypatch,
):
    employee = Employee(
        employee_code="E001-DUPE",
        full_name="Nguyen Van Dupe",
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
        "search_face_embeddings",
        lambda **_: [
            FaceSearchResult(
                employee_id=employee.id,
                score=0.95,
                payload={},
                point_id="point-1",
            )
        ],
    )

    first_captured_at = datetime.now(timezone.utc)
    first_response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=first_captured_at,
        camera_id="kiosk-auto",
    )
    second_response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=first_captured_at + timedelta(seconds=5),
        camera_id="kiosk-auto",
    )

    assert first_response.event_id is not None
    assert second_response.event_id == first_response.event_id
    assert second_response.message == "Check-in already recorded recently."
    assert db_session.scalar(select(func.count()).select_from(AttendanceEvent)) == 1


def test_recognize_attendance_frame_records_again_after_dedupe_window(
    db_session,
    monkeypatch,
):
    employee = Employee(
        employee_code="E001-WINDOW",
        full_name="Nguyen Van Window",
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
        "search_face_embeddings",
        lambda **_: [
            FaceSearchResult(
                employee_id=employee.id,
                score=0.95,
                payload={},
                point_id="point-1",
            )
        ],
    )

    old_event = AttendanceEvent(
        employee_id=employee.id,
        action_type="check_in",
        attendance_status="recorded",
        captured_at=datetime.utcnow() - timedelta(seconds=11),
        created_at=datetime.utcnow() - timedelta(seconds=11),
    )
    db_session.add(old_event)
    db_session.commit()

    response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=datetime.utcnow(),
        camera_id="kiosk-auto",
    )

    assert response.event_id is not None
    assert response.event_id != old_event.id
    assert db_session.scalar(select(func.count()).select_from(AttendanceEvent)) == 2


def test_recognize_attendance_frame_uses_server_recorded_time_for_dedupe(
    db_session,
    monkeypatch,
):
    employee = Employee(
        employee_code="E001-SLOW",
        full_name="Nguyen Van Slow",
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
        "search_face_embeddings",
        lambda **_: [
            FaceSearchResult(
                employee_id=employee.id,
                score=0.95,
                payload={},
                point_id="point-1",
            )
        ],
    )

    now = datetime.now(timezone.utc)
    recorded_event = AttendanceEvent(
        employee_id=employee.id,
        action_type="check_in",
        attendance_status="recorded",
        captured_at=now - timedelta(seconds=13),
        created_at=now - timedelta(seconds=8),
    )
    db_session.add(recorded_event)
    db_session.commit()

    response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=now - timedelta(seconds=2),
        camera_id="kiosk-auto",
    )

    assert response.event_id == recorded_event.id
    assert response.message == "Check-in already recorded recently."
    assert db_session.scalar(select(func.count()).select_from(AttendanceEvent)) == 1


def test_recognize_attendance_frame_keeps_camera_gate_after_no_face_jitter(
    db_session,
    monkeypatch,
):
    employee = Employee(
        employee_code="E001-CLEAR",
        full_name="Nguyen Van Clear",
        department="IT",
        position="Engineer",
        status="active",
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)

    match_analysis = {
        "status": "success",
        "faces_detected": 1,
        "error_message": None,
        "embedding": [0.1] * 512,
    }
    no_face_analysis = {
        "status": "failed",
        "faces_detected": 0,
        "error_message": "No face detected.",
    }
    current_analysis = {"value": match_analysis}

    monkeypatch.setattr(
        attendance_service,
        "analyze_image_bytes",
        lambda _: current_analysis["value"],
    )
    monkeypatch.setattr(
        attendance_service,
        "search_face_embeddings",
        lambda **_: [
            FaceSearchResult(
                employee_id=employee.id,
                score=0.95,
                payload={},
                point_id="point-1",
            )
        ],
    )

    first_response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=None,
        camera_id="kiosk-auto",
        record_unmatched=False,
    )
    recorded_event = db_session.get(AttendanceEvent, first_response.event_id)
    assert recorded_event is not None
    recorded_event.created_at = datetime.utcnow() - timedelta(seconds=30)
    db_session.commit()

    current_analysis["value"] = no_face_analysis
    no_face_response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=None,
        camera_id="kiosk-auto",
        record_unmatched=False,
    )
    current_analysis["value"] = match_analysis
    second_response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=None,
        camera_id="kiosk-auto",
        record_unmatched=False,
    )

    assert no_face_response.matched is False
    assert no_face_response.event_id is None
    assert second_response.event_id == first_response.event_id
    assert second_response.message == "Check-in already recorded recently."
    assert db_session.scalar(select(func.count()).select_from(AttendanceEvent)) == 1


def test_recognize_attendance_frame_skips_missing_employee_match(
    db_session,
    monkeypatch,
):
    employee = Employee(
        employee_code="E002",
        full_name="Tran Thi B",
        department="HR",
        position="Manager",
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
            "embedding": [0.2] * 512,
        },
    )
    monkeypatch.setattr(
        attendance_service,
        "search_face_embeddings",
        lambda **_: [
            FaceSearchResult(
                employee_id=999,
                score=0.99,
                payload={},
                point_id="orphan-point",
            ),
            FaceSearchResult(
                employee_id=employee.id,
                score=0.92,
                payload={},
                point_id="valid-point",
            ),
        ],
    )

    response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_out",
        captured_at=None,
        camera_id="cam-01",
    )

    assert response.matched is True
    assert response.attendance_status == "recorded"
    assert response.employee is not None
    assert response.employee.id == employee.id
    assert response.score == 0.92


def test_delete_attendance_events_returns_deleted_count(db_session):
    db_session.add_all(
        [
            AttendanceEvent(action_type="check_in", attendance_status="unknown_face"),
            AttendanceEvent(action_type="check_out", attendance_status="recorded"),
        ]
    )
    db_session.commit()

    deleted_count = attendance_service.delete_attendance_events(db_session)

    assert deleted_count == 2
    assert db_session.scalar(select(func.count()).select_from(AttendanceEvent)) == 0


def test_delete_attendance_events_by_ids_keeps_unselected_events(db_session):
    events = [
        AttendanceEvent(action_type="check_in", attendance_status="unknown_face"),
        AttendanceEvent(action_type="check_out", attendance_status="recorded"),
        AttendanceEvent(action_type="check_in", attendance_status="multiple_faces"),
    ]
    db_session.add_all(events)
    db_session.commit()

    deleted_count = attendance_service.delete_attendance_events_by_ids(
        db_session,
        [events[0].id, events[2].id, events[2].id],
    )

    remaining_ids = db_session.scalars(select(AttendanceEvent.id)).all()
    assert deleted_count == 2
    assert remaining_ids == [events[1].id]


def test_list_attendance_events_filters_by_attendance_status(db_session):
    db_session.add_all(
        [
            AttendanceEvent(action_type="check_in", attendance_status="unknown_face"),
            AttendanceEvent(action_type="check_out", attendance_status="recorded"),
            AttendanceEvent(action_type="check_in", attendance_status="multiple_faces"),
        ]
    )
    db_session.commit()

    response = attendance_service.list_attendance_events(
        db_session,
        employee_id=None,
        action_type=None,
        attendance_status="unknown_face",
        from_=None,
        to=None,
        page=1,
        page_size=20,
    )

    assert response.total == 1
    assert response.items[0].attendance_status == "unknown_face"


def test_export_attendance_events_csv_uses_filters_and_includes_employee_fields(db_session):
    employee = Employee(
        employee_code="E900",
        full_name="Csv Export",
        department="IT",
        position="Engineer",
        status="active",
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)

    db_session.add_all(
        [
            AttendanceEvent(
                employee_id=employee.id,
                action_type="check_in",
                attendance_status="recorded",
                camera_id="cam-01",
                score=Decimal("0.9500"),
                captured_at=datetime(2026, 5, 11, 8, 30, 0),
            ),
            AttendanceEvent(
                employee_id=employee.id,
                action_type="check_out",
                attendance_status="recorded",
                camera_id="cam-02",
                score=Decimal("0.9100"),
                captured_at=datetime(2026, 5, 11, 17, 45, 0),
            ),
            AttendanceEvent(
                employee_id=employee.id,
                action_type="check_in",
                attendance_status="unknown_face",
                camera_id="cam-03",
                score=None,
                captured_at=datetime(2026, 5, 11, 9, 15, 0),
            ),
        ]
    )
    db_session.commit()

    csv_content = attendance_service.export_attendance_events_csv(
        db_session,
        employee_id=employee.id,
        action_type="check_in",
        attendance_status="recorded",
        from_=None,
        to=None,
    )

    lines = csv_content.strip().splitlines()
    assert lines[0] == "event_id,event_time,employee_code,full_name,action_type,attendance_status,score,camera_id"
    assert len(lines) == 2
    assert "2026-05-11T15:30:00" in lines[1]
    assert "E900" in lines[1]
    assert "Csv Export" in lines[1]
    assert ",check_in,recorded,0.95,cam-01" in lines[1]


def test_export_attendance_events_csv_rejects_results_over_cap(db_session, monkeypatch):
    employee = Employee(
        employee_code="E902",
        full_name="Too Many Events",
        department="IT",
        position="Engineer",
        status="active",
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)

    db_session.add_all(
        [
            AttendanceEvent(
                employee_id=employee.id,
                action_type="check_in",
                attendance_status="recorded",
                captured_at=datetime(2026, 5, 11, 8, 30, 0),
            ),
            AttendanceEvent(
                employee_id=employee.id,
                action_type="check_in",
                attendance_status="recorded",
                captured_at=datetime(2026, 5, 11, 8, 31, 0),
            ),
        ]
    )
    db_session.commit()
    monkeypatch.setattr(attendance_service, "MAX_EXPORT_EVENTS", 1)

    with pytest.raises(
        attendance_service.AttendanceValidationError,
        match="Attendance event export exceeds 1 rows",
    ):
        attendance_service.export_attendance_events_csv(
            db_session,
            employee_id=employee.id,
            action_type="check_in",
            attendance_status=None,
            from_=None,
            to=None,
        )


def test_recognize_attendance_frame_skips_inactive_employee(db_session, monkeypatch):
    inactive_employee = Employee(
        employee_code="E-INACTIVE",
        full_name="Inactive Person",
        department="IT",
        position="Engineer",
        status="inactive",
    )
    db_session.add(inactive_employee)
    db_session.commit()
    db_session.refresh(inactive_employee)

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
        "search_face_embeddings",
        lambda **_: [
            FaceSearchResult(
                employee_id=inactive_employee.id,
                score=0.95,
                payload={},
                point_id="point-1",
            )
        ],
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
    assert response.message == "Face not recognized."
    assert response.employee is None
    assert response.event_id is None
    # Policy: inactive-only match must not create any event (recorded or unknown).
    total_count = db_session.scalar(select(func.count()).select_from(AttendanceEvent))
    assert total_count == 0


def test_recognize_attendance_frame_matches_active_after_inactive_in_results(
    db_session,
    monkeypatch,
):
    inactive_employee = Employee(
        employee_code="E-INACTIVE-FIRST",
        full_name="Inactive Top Hit",
        department="IT",
        position="Engineer",
        status="inactive",
    )
    active_employee = Employee(
        employee_code="E-ACTIVE-SECOND",
        full_name="Active Second Hit",
        department="IT",
        position="Engineer",
        status="active",
    )
    db_session.add_all([inactive_employee, active_employee])
    db_session.commit()
    db_session.refresh(inactive_employee)
    db_session.refresh(active_employee)

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
        "search_face_embeddings",
        lambda **_: [
            FaceSearchResult(
                employee_id=inactive_employee.id,
                score=0.97,
                payload={},
                point_id="point-1",
            ),
            FaceSearchResult(
                employee_id=active_employee.id,
                score=0.90,
                payload={},
                point_id="point-2",
            ),
        ],
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
    assert response.employee.id == active_employee.id
    assert response.score == 0.90
    recorded_count = db_session.scalar(
        select(func.count())
        .select_from(AttendanceEvent)
        .where(AttendanceEvent.attendance_status == "recorded")
    )
    assert recorded_count == 1


def test_recognize_attendance_frame_inactive_only_creates_no_event(
    db_session,
    monkeypatch,
):
    inactive_employee = Employee(
        employee_code="E-INACTIVE-ONLY",
        full_name="Inactive Only",
        department="IT",
        position="Engineer",
        status="inactive",
    )
    db_session.add(inactive_employee)
    db_session.commit()
    db_session.refresh(inactive_employee)

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
        "search_face_embeddings",
        lambda **_: [
            FaceSearchResult(
                employee_id=inactive_employee.id,
                score=0.95,
                payload={},
                point_id="point-1",
            ),
            FaceSearchResult(
                employee_id=inactive_employee.id,
                score=0.92,
                payload={},
                point_id="point-2",
            ),
        ],
    )

    response = attendance_service.recognize_attendance_frame(
        db_session,
        image_bytes=b"fake-image-bytes",
        action_type="check_in",
        captured_at=None,
        camera_id="cam-01",
        record_unmatched=True,
    )

    assert response.matched is False
    assert response.event_id is None
    total_count = db_session.scalar(select(func.count()).select_from(AttendanceEvent))
    assert total_count == 0


def test_list_attendance_events_serializes_business_local_wall_time(db_session):
    employee = Employee(
        employee_code="E901",
        full_name="Local Wall Time",
        department="IT",
        position="Engineer",
        status="active",
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)

    event = AttendanceEvent(
        employee_id=employee.id,
        action_type="check_in",
        attendance_status="recorded",
        camera_id="cam-01",
        score=Decimal("0.9500"),
        captured_at=datetime(2026, 5, 11, 4, 52, 0),
    )
    db_session.add(event)
    db_session.commit()

    response = attendance_service.list_attendance_events(
        db_session,
        employee_id=employee.id,
        action_type="check_in",
        attendance_status=None,
        from_=None,
        to=None,
        page=1,
        page_size=20,
    )

    assert response.total == 1
    assert response.items[0].captured_at == datetime(2026, 5, 11, 11, 52, 0)
