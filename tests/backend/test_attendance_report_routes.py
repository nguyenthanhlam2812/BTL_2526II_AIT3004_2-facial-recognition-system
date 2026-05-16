from __future__ import annotations

from datetime import date, datetime

from backend.app.api.routes import attendance as attendance_route
from backend.app.schemas.attendance import (
    AttendanceDailyReportListResponse,
    AttendanceDailyReportRead,
    AttendanceDashboardSummaryResponse,
    AttendanceDashboardTodaySummary,
    AttendanceDashboardTrendPoint,
)
from backend.app.services.attendance_service import AttendanceValidationError


def test_get_daily_attendance_reports_returns_service_payload(client, monkeypatch):
    captured = {}

    def fake_service(_db, **kwargs):
        captured.update(kwargs)
        return AttendanceDailyReportListResponse(
            items=[
                AttendanceDailyReportRead(
                    date=date(2026, 5, 11),
                    employee_id=1,
                    employee_code="E001",
                    full_name="Nguyen Van A",
                    department="IT",
                    first_check_in=datetime(2026, 5, 11, 8, 55, 0),
                    last_check_out=datetime(2026, 5, 11, 17, 30, 0),
                    summary_status="present",
                )
            ],
            total=1,
        )

    monkeypatch.setattr(
        attendance_route,
        "list_daily_attendance_reports_service",
        fake_service,
    )

    response = client.get(
        "/api/attendance/reports/daily",
        params={
            "date": "2026-05-11",
            "department": "IT",
            "status": "present",
            "page": 2,
            "page_size": 10,
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert captured["department"] == "IT"
    assert captured["status"] == "present"
    assert captured["page"] == 2
    assert captured["page_size"] == 10


def test_get_daily_attendance_reports_returns_400_for_invalid_range(client, monkeypatch):
    def fake_service(_db, **_kwargs):
        raise AttendanceValidationError("Report range cannot exceed 31 days.")

    monkeypatch.setattr(
        attendance_route,
        "list_daily_attendance_reports_service",
        fake_service,
    )

    response = client.get(
        "/api/attendance/reports/daily",
        params={"from": "2026-04-01", "to": "2026-05-11"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Report range cannot exceed 31 days."


def test_export_daily_attendance_reports_csv_returns_attachment(client, monkeypatch):
    captured = {}

    def fake_service(_db, **kwargs):
        captured.update(kwargs)
        return "date,employee_code\n2026-05-11,E001"

    monkeypatch.setattr(
        attendance_route,
        "export_daily_attendance_reports_csv_service",
        fake_service,
    )

    response = client.get(
        "/api/attendance/reports/daily/export.csv",
        params={"from": "2026-05-11", "to": "2026-05-12", "employee_id": 3},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == 'attachment; filename="attendance-daily-report.csv"'
    assert response.text.startswith("\ufeffdate,employee_code")
    assert captured["employee_id"] == 3


def test_export_daily_attendance_reports_csv_returns_400_for_invalid_range(client, monkeypatch):
    def fake_service(_db, **_kwargs):
        raise AttendanceValidationError("Report range cannot exceed 31 days.")

    monkeypatch.setattr(
        attendance_route,
        "export_daily_attendance_reports_csv_service",
        fake_service,
    )

    response = client.get(
        "/api/attendance/reports/daily/export.csv",
        params={"from": "2026-04-01", "to": "2026-05-11"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Report range cannot exceed 31 days."


def test_get_dashboard_summary_returns_service_payload(client, monkeypatch):
    captured = {}

    def fake_service(_db, *, days):
        captured["days"] = days
        return AttendanceDashboardSummaryResponse(
            business_timezone="Asia/Ho_Chi_Minh",
            total_employees=12,
            today=AttendanceDashboardTodaySummary(present=8, late=2, absent=2),
            trend=[
                AttendanceDashboardTrendPoint(date=date(2026, 5, 10), check_in_count=7),
                AttendanceDashboardTrendPoint(date=date(2026, 5, 11), check_in_count=10),
            ],
        )

    monkeypatch.setattr(
        attendance_route,
        "get_attendance_dashboard_summary_service",
        fake_service,
    )

    response = client.get("/api/attendance/reports/dashboard-summary", params={"days": 30})

    assert response.status_code == 200
    assert response.json()["business_timezone"] == "Asia/Ho_Chi_Minh"
    assert response.json()["today"]["late"] == 2
    assert captured["days"] == 30


def test_get_dashboard_summary_rejects_unsupported_range(client):
    response = client.get("/api/attendance/reports/dashboard-summary", params={"days": 14})

    assert response.status_code == 400
    assert response.json()["detail"] == "Dashboard summary supports only 7 or 30 days."
