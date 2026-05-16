from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from backend.app.models.attendance_event import AttendanceEvent
from backend.app.models.employee import Employee
from backend.app.models.system_setting import SystemSetting
from backend.app.services import attendance_service
from backend.app.services.attendance_service import AttendanceValidationError


def seed_employee(
    db_session,
    *,
    employee_code: str,
    department: str = "IT",
) -> Employee:
    employee = Employee(
        employee_code=employee_code,
        full_name=f"Employee {employee_code}",
        department=department,
        position="Engineer",
        status="active",
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
    score: str = "0.9500",
) -> AttendanceEvent:
    event = AttendanceEvent(
        employee_id=employee_id,
        action_type=action_type,
        attendance_status="recorded",
        score=Decimal(score),
        camera_id="cam-01",
        captured_at=captured_at,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


def test_list_daily_attendance_reports_uses_business_timezone_for_bucket_and_status(db_session):
    day = date(2026, 5, 11)
    present_employee = seed_employee(db_session, employee_code="E001", department="IT")
    late_employee = seed_employee(db_session, employee_code="E002", department="IT")
    missing_employee = seed_employee(db_session, employee_code="E003", department="HR")

    seed_recorded_event(
        db_session,
        employee_id=present_employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 10, 23, 30, 0),  # 06:30 local on 2026-05-11
    )
    seed_recorded_event(
        db_session,
        employee_id=present_employee.id,
        action_type="check_out",
        captured_at=datetime(2026, 5, 11, 10, 45, 0),  # 17:45 local
    )
    seed_recorded_event(
        db_session,
        employee_id=late_employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 11, 4, 52, 0),  # 11:52 local
    )
    seed_recorded_event(
        db_session,
        employee_id=late_employee.id,
        action_type="check_out",
        captured_at=datetime(2026, 5, 11, 11, 5, 0),  # 18:05 local
    )

    response = attendance_service.list_daily_attendance_reports(
        db_session,
        date_=day,
        from_=None,
        to=None,
        employee_id=None,
        department=None,
        status=None,
        page=1,
        page_size=20,
    )

    assert response.total == 3
    rows_by_code = {row.employee_code: row for row in response.items}
    assert rows_by_code["E001"].summary_status == "present"
    assert rows_by_code["E001"].first_check_in == datetime(2026, 5, 11, 6, 30, 0)
    assert rows_by_code["E001"].last_check_out == datetime(2026, 5, 11, 17, 45, 0)
    assert rows_by_code["E002"].summary_status == "late"
    assert rows_by_code["E002"].first_check_in == datetime(2026, 5, 11, 11, 52, 0)
    assert rows_by_code["E002"].last_check_out == datetime(2026, 5, 11, 18, 5, 0)
    assert rows_by_code["E003"].summary_status == "missing"
    assert rows_by_code["E003"].first_check_in is None
    assert rows_by_code["E003"].last_check_out is None


def test_list_daily_attendance_reports_uses_db_business_timezone(db_session):
    employee = seed_employee(db_session, employee_code="E001-TZ", department="IT")
    db_session.add(
        SystemSetting(
            key="business_timezone",
            value='"UTC"',
            updated_by_user_id=None,
        )
    )
    db_session.commit()

    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 11, 4, 52, 0),
    )

    response = attendance_service.list_daily_attendance_reports(
        db_session,
        date_=date(2026, 5, 11),
        from_=None,
        to=None,
        employee_id=employee.id,
        department=None,
        status=None,
        page=1,
        page_size=20,
    )

    assert response.total == 1
    assert response.items[0].first_check_in == datetime(2026, 5, 11, 4, 52, 0)
    assert response.items[0].summary_status == "present"


def test_list_daily_attendance_reports_filters_employee_scope_and_summary_status(db_session):
    day = date(2026, 5, 11)
    it_missing = seed_employee(db_session, employee_code="E010", department="IT")
    hr_present = seed_employee(db_session, employee_code="E011", department="HR")

    seed_recorded_event(
        db_session,
        employee_id=hr_present.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 11, 1, 40, 0),  # 08:40 local
    )

    response = attendance_service.list_daily_attendance_reports(
        db_session,
        date_=day,
        from_=None,
        to=None,
        employee_id=None,
        department="  it  ",
        status="missing",
        page=1,
        page_size=20,
    )

    assert response.total == 1
    assert response.items[0].employee_id == it_missing.id
    assert response.items[0].summary_status == "missing"


def test_export_daily_attendance_reports_csv_matches_localized_columns(db_session):
    employee = seed_employee(db_session, employee_code="E020", department="IT")
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 11, 4, 5, 0),  # 11:05 local
    )
    seed_recorded_event(
        db_session,
        employee_id=employee.id,
        action_type="check_out",
        captured_at=datetime(2026, 5, 11, 10, 30, 0),  # 17:30 local
    )

    csv_content = attendance_service.export_daily_attendance_reports_csv(
        db_session,
        date_=date(2026, 5, 11),
        from_=None,
        to=None,
        employee_id=employee.id,
        department=None,
        status=None,
    )

    lines = csv_content.strip().splitlines()
    assert lines[0] == "date,employee_code,full_name,department,first_check_in,last_check_out,summary_status"
    assert len(lines) == 2
    assert (
        "2026-05-11,E020,Employee E020,IT,2026-05-11T11:05:00,2026-05-11T17:30:00,late"
        in lines[1]
    )


def test_list_daily_attendance_reports_rejects_ranges_over_31_days(db_session):
    seed_employee(db_session, employee_code="E030", department="IT")

    with pytest.raises(AttendanceValidationError, match="31 days"):
        attendance_service.list_daily_attendance_reports(
            db_session,
            date_=None,
            from_=date(2026, 4, 1),
            to=date(2026, 5, 11),
            employee_id=None,
            department=None,
            status=None,
            page=1,
            page_size=20,
        )


def test_get_attendance_dashboard_summary_uses_report_source_of_truth(db_session, monkeypatch):
    fixed_now = datetime(2026, 5, 11, 12, 0, 0)
    monkeypatch.setattr(attendance_service, "_business_now", lambda: fixed_now)

    present_employee = seed_employee(db_session, employee_code="E100", department="IT")
    late_employee = seed_employee(db_session, employee_code="E101", department="IT")
    missing_employee = seed_employee(db_session, employee_code="E102", department="HR")
    assert missing_employee.id

    seed_recorded_event(
        db_session,
        employee_id=present_employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 11, 1, 30, 0),  # 08:30 local
    )
    seed_recorded_event(
        db_session,
        employee_id=late_employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 11, 3, 30, 0),  # 10:30 local
    )
    seed_recorded_event(
        db_session,
        employee_id=present_employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 10, 1, 30, 0),  # previous day
    )

    summary = attendance_service.get_attendance_dashboard_summary(db_session, days=7)

    assert summary.business_timezone == "Asia/Ho_Chi_Minh"
    assert summary.total_employees == 3
    assert summary.today.present == 1
    assert summary.today.late == 1
    assert summary.today.absent == 1
    assert len(summary.trend) == 7
    assert summary.trend[-1].date == date(2026, 5, 11)
    assert summary.trend[-1].check_in_count == 2
    assert summary.trend[-2].date == date(2026, 5, 10)
    assert summary.trend[-2].check_in_count == 1


def test_list_daily_attendance_reports_includes_business_timezone(db_session):
    seed_employee(db_session, employee_code="E040", department="IT")

    response = attendance_service.list_daily_attendance_reports(
        db_session,
        date_=date(2026, 5, 11),
        from_=None,
        to=None,
        employee_id=None,
        department=None,
        status=None,
        page=1,
        page_size=20,
    )

    assert response.business_timezone == "Asia/Ho_Chi_Minh"


def test_list_daily_attendance_reports_includes_db_business_timezone(db_session):
    seed_employee(db_session, employee_code="E041", department="IT")
    db_session.add(
        SystemSetting(
            key="business_timezone",
            value='"UTC"',
            updated_by_user_id=None,
        )
    )
    db_session.commit()

    response = attendance_service.list_daily_attendance_reports(
        db_session,
        date_=date(2026, 5, 11),
        from_=None,
        to=None,
        employee_id=None,
        department=None,
        status=None,
        page=1,
        page_size=20,
    )

    assert response.business_timezone == "UTC"


def test_list_daily_attendance_reports_excludes_inactive_employees(db_session):
    active_employee = seed_employee(db_session, employee_code="E050", department="IT")
    inactive_employee = Employee(
        employee_code="E051",
        full_name="Employee E051",
        department="IT",
        position="Engineer",
        status="inactive",
    )
    db_session.add(inactive_employee)
    db_session.commit()
    db_session.refresh(inactive_employee)

    response = attendance_service.list_daily_attendance_reports(
        db_session,
        date_=date(2026, 5, 11),
        from_=None,
        to=None,
        employee_id=None,
        department=None,
        status=None,
        page=1,
        page_size=20,
    )

    employee_ids = {row.employee_id for row in response.items}
    assert active_employee.id in employee_ids
    assert inactive_employee.id not in employee_ids


def test_dashboard_summary_counts_only_active_employees(db_session, monkeypatch):
    fixed_now = datetime(2026, 5, 11, 12, 0, 0)
    monkeypatch.setattr(attendance_service, "_business_now", lambda: fixed_now)

    active_employee = seed_employee(db_session, employee_code="E060", department="IT")
    inactive_employee = Employee(
        employee_code="E061",
        full_name="Employee E061",
        department="IT",
        position="Engineer",
        status="inactive",
    )
    db_session.add(inactive_employee)
    db_session.commit()
    db_session.refresh(inactive_employee)

    seed_recorded_event(
        db_session,
        employee_id=active_employee.id,
        action_type="check_in",
        captured_at=datetime(2026, 5, 11, 1, 30, 0),
    )

    summary = attendance_service.get_attendance_dashboard_summary(db_session, days=7)

    # Only 1 active employee should be counted
    assert summary.total_employees == 1
    assert summary.today.present == 1
    assert summary.today.absent == 0

