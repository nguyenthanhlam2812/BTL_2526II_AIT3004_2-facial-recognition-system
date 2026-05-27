"""Tests for work-session pair matching on top of attendance events.

Business rules covered:
- Greedy pair matching: each check-out pairs with the earliest unpaired check-in.
- Multiple sessions per day (vd: sáng-chiều có nghỉ trưa).
- Orphan check-in → incomplete session (NULL duration, is_complete=False).
- Orphan check-out → ignored (data anomaly, log only).
- Duplicate check-in → bỏ qua cái sau, giữ check-in sớm nhất.
- Cross-midnight (làm đêm) → session thuộc business day của check-in.
- Inactive employee → không xuất hiện trong report.
- Báo cáo trong khoảng từ-đến, mỗi (date, employee) là 1 row.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from backend.app.models.attendance_event import AttendanceEvent
from backend.app.models.employee import Employee
from backend.app.services import attendance_service
from backend.app.services.attendance_service import AttendanceValidationError


def seed_employee(
    db_session,
    *,
    employee_code: str,
    department: str = "IT",
    status: str = "active",
) -> Employee:
    employee = Employee(
        employee_code=employee_code,
        full_name=f"Employee {employee_code}",
        department=department,
        position="Engineer",
        status=status,
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)
    return employee


def seed_recorded_event(
    db_session,
    *,
    employee_id: int,
    action_type: str,
    captured_at: datetime,
) -> AttendanceEvent:
    event = AttendanceEvent(
        employee_id=employee_id,
        action_type=action_type,
        attendance_status="recorded",
        score=Decimal("0.9500"),
        camera_id="cam-01",
        captured_at=captured_at,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


def test_sessions_simple_pair_returns_one_complete_session(db_session):
    """IN 08:00 → OUT 17:00 → 1 session, 9h."""
    employee = seed_employee(db_session, employee_code="E001")
    # captured_at in UTC; business TZ +7 → local times 08:00 and 17:00 on 2026-05-27
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 27, 1, 0, 0),  # 08:00 local
    )
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_out",
        captured_at=datetime(2026, 5, 27, 10, 0, 0),  # 17:00 local
    )

    response = attendance_service.list_daily_work_sessions(
        db_session,
        date_=date(2026, 5, 27),
        from_=None,
        to=None,
        employee_id=None,
        department=None,
        status=None,
        page=1,
        page_size=20,
    )

    assert response.total == 1
    row = response.items[0]
    assert row.date == date(2026, 5, 27)
    assert row.employee_id == employee.id
    assert len(row.sessions) == 1
    assert row.sessions[0].is_complete is True
    assert row.sessions[0].duration_minutes == 9 * 60
    assert row.total_work_minutes == 9 * 60
    assert row.summary_status == "present"


def test_sessions_multiple_sessions_per_day(db_session):
    """IN 08:00, OUT 11:30, IN 12:30, OUT 17:30 → 2 sessions, total 8.5h."""
    employee = seed_employee(db_session, employee_code="E002")
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 27, 1, 0, 0),  # 08:00 local
    )
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_out",
        captured_at=datetime(2026, 5, 27, 4, 30, 0),  # 11:30 local
    )
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 27, 5, 30, 0),  # 12:30 local
    )
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_out",
        captured_at=datetime(2026, 5, 27, 10, 30, 0),  # 17:30 local
    )

    response = attendance_service.list_daily_work_sessions(
        db_session,
        date_=date(2026, 5, 27),
        from_=None, to=None, employee_id=None, department=None, status=None,
        page=1, page_size=20,
    )

    row = response.items[0]
    assert len(row.sessions) == 2
    assert row.sessions[0].duration_minutes == 3 * 60 + 30  # 3h30
    assert row.sessions[1].duration_minutes == 5 * 60  # 5h
    assert row.total_work_minutes == 8 * 60 + 30
    assert all(s.is_complete for s in row.sessions)


def test_sessions_orphan_check_in_returns_incomplete_session(db_session):
    """IN 08:00 (no check-out) → 1 incomplete session, NULL duration."""
    employee = seed_employee(db_session, employee_code="E003")
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 27, 1, 0, 0),
    )

    response = attendance_service.list_daily_work_sessions(
        db_session,
        date_=date(2026, 5, 27),
        from_=None, to=None, employee_id=None, department=None, status=None,
        page=1, page_size=20,
    )

    row = response.items[0]
    assert len(row.sessions) == 1
    session = row.sessions[0]
    assert session.is_complete is False
    assert session.check_in_at is not None
    assert session.check_out_at is None
    assert session.duration_minutes is None
    # Total work minutes only counts complete sessions.
    assert row.total_work_minutes == 0
    assert row.summary_status == "present"  # Still "present" because had a check-in


def test_sessions_orphan_check_out_is_ignored(db_session):
    """OUT 17:00 không có IN trước → bỏ qua, không tạo session."""
    employee = seed_employee(db_session, employee_code="E004")
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_out",
        captured_at=datetime(2026, 5, 27, 10, 0, 0),
    )

    response = attendance_service.list_daily_work_sessions(
        db_session,
        date_=date(2026, 5, 27),
        from_=None, to=None, employee_id=None, department=None, status=None,
        page=1, page_size=20,
    )

    row = response.items[0]
    assert row.sessions == []
    assert row.total_work_minutes == 0
    assert row.summary_status == "missing"  # No check-in at all


def test_sessions_duplicate_check_in_keeps_earliest(db_session):
    """IN 08:00, IN 09:00, OUT 17:00 → 1 session (08:00 → 17:00)."""
    employee = seed_employee(db_session, employee_code="E005")
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 27, 1, 0, 0),  # 08:00
    )
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 27, 2, 0, 0),  # 09:00 dup
    )
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_out",
        captured_at=datetime(2026, 5, 27, 10, 0, 0),  # 17:00
    )

    response = attendance_service.list_daily_work_sessions(
        db_session,
        date_=date(2026, 5, 27),
        from_=None, to=None, employee_id=None, department=None, status=None,
        page=1, page_size=20,
    )

    row = response.items[0]
    assert len(row.sessions) == 1
    assert row.sessions[0].is_complete is True
    assert row.sessions[0].check_in_at.hour == 8  # business local
    assert row.sessions[0].duration_minutes == 9 * 60


def test_sessions_cross_midnight_bucketed_under_check_in_date(db_session):
    """Night shift IN 22:00 ngày 27 → OUT 06:00 ngày 28 → session belongs to 27."""
    employee = seed_employee(db_session, employee_code="E006")
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 27, 15, 0, 0),  # 22:00 local on 27
    )
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_out",
        captured_at=datetime(2026, 5, 27, 23, 0, 0),  # 06:00 local on 28
    )

    response = attendance_service.list_daily_work_sessions(
        db_session,
        date_=None,
        from_=date(2026, 5, 27),
        to=date(2026, 5, 28),
        employee_id=None, department=None, status=None,
        page=1, page_size=20,
    )

    # Should appear exactly once, on day 27 (check-in's day).
    sessions_on_27 = [r for r in response.items if r.date == date(2026, 5, 27)]
    sessions_on_28 = [
        r for r in response.items
        if r.date == date(2026, 5, 28) and r.sessions
    ]
    assert len(sessions_on_27) == 1
    assert sessions_on_28 == []
    row = sessions_on_27[0]
    assert len(row.sessions) == 1
    assert row.sessions[0].is_complete is True
    assert row.sessions[0].duration_minutes == 8 * 60


def test_sessions_inactive_employee_excluded(db_session):
    """Inactive employee không xuất hiện trong report."""
    inactive = seed_employee(db_session, employee_code="E007", status="inactive")
    seed_recorded_event(
        db_session,
        employee_id=inactive.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 27, 1, 0, 0),
    )

    response = attendance_service.list_daily_work_sessions(
        db_session,
        date_=date(2026, 5, 27),
        from_=None, to=None, employee_id=None, department=None, status=None,
        page=1, page_size=20,
    )

    # No active employee → empty list.
    assert response.items == []
    assert response.total == 0


def test_sessions_late_status_uses_first_check_in(db_session):
    """First check-in 10:00 (after 09:00 threshold) → late."""
    employee = seed_employee(db_session, employee_code="E008")
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 27, 3, 0, 0),  # 10:00 local
    )
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_out",
        captured_at=datetime(2026, 5, 27, 10, 0, 0),  # 17:00 local
    )

    response = attendance_service.list_daily_work_sessions(
        db_session,
        date_=date(2026, 5, 27),
        from_=None, to=None, employee_id=None, department=None, status=None,
        page=1, page_size=20,
    )

    row = response.items[0]
    assert row.summary_status == "late"
    assert row.sessions[0].duration_minutes == 7 * 60


def test_sessions_employee_filter(db_session):
    """employee_id filter chỉ trả 1 nhân viên."""
    e1 = seed_employee(db_session, employee_code="E009")
    e2 = seed_employee(db_session, employee_code="E010")
    for emp_id in (e1.id, e2.id):
        seed_recorded_event(
            db_session, employee_id=emp_id, action_type="check_in",
            captured_at=datetime(2026, 5, 27, 1, 0, 0),
        )

    response = attendance_service.list_daily_work_sessions(
        db_session,
        date_=date(2026, 5, 27),
        from_=None, to=None,
        employee_id=e1.id,
        department=None, status=None,
        page=1, page_size=20,
    )

    assert response.total == 1
    assert response.items[0].employee_id == e1.id


def test_sessions_date_range_too_long_raises(db_session):
    """Quá MAX_REPORT_DAYS → raise validation error."""
    with pytest.raises(AttendanceValidationError):
        attendance_service.list_daily_work_sessions(
            db_session,
            date_=None,
            from_=date(2026, 1, 1),
            to=date(2026, 12, 31),
            employee_id=None, department=None, status=None,
            page=1, page_size=20,
        )
