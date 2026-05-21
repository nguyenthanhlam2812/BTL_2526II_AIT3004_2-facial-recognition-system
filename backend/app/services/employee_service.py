from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.attendance_event import AttendanceEvent
from backend.app.models.department import Department
from backend.app.models.employee import Employee
from backend.app.models.position import Position
from backend.app.models.enrollment import Enrollment
from backend.app.schemas.employee import EmployeeCreate, EmployeeUpdate


class DuplicateEmployeeCodeError(Exception):
    pass


class InvalidDepartmentError(Exception):
    """Raised when the department does not exist in the lookup table."""
    pass


class InvalidPositionError(Exception):
    """Raised when the position does not exist in the lookup table."""
    pass


class EmployeeHasRelatedDataError(Exception):
    """Raised when deleting an employee would detach historical business data."""

    pass


def list_employees(
    db: Session,
    *,
    q: str | None,
    department: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Employee], int]:
    filters = []
    if q:
        keyword = f"%{q.strip()}%"
        filters.append(
            or_(
                Employee.employee_code.like(keyword),
                Employee.full_name.like(keyword),
                Employee.department.like(keyword),
                Employee.position.like(keyword),
            )
        )
    if department and department.strip():
        filters.append(func.lower(Employee.department) == department.strip().lower())

    total_stmt = select(func.count()).select_from(Employee)
    items_stmt = (
        select(Employee)
        .options(selectinload(Employee.enrollments))
        .order_by(Employee.id.desc())
    )

    if filters:
        total_stmt = total_stmt.where(*filters)
        items_stmt = items_stmt.where(*filters)

    total = db.scalar(total_stmt) or 0
    items = db.scalars(
        items_stmt.offset((page - 1) * page_size).limit(page_size)
    ).all()

    return list(items), total


def get_employee(db: Session, employee_id: int) -> Employee | None:
    return db.get(Employee, employee_id)


def create_employee(db: Session, payload: EmployeeCreate) -> Employee:
    ensure_employee_code_available(db, payload.employee_code)
    _ensure_department_exists(db, payload.department)
    _ensure_position_exists(db, payload.position)

    employee = Employee(**payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def update_employee(
    db: Session,
    employee_id: int,
    payload: EmployeeUpdate,
) -> Employee | None:
    employee = get_employee(db, employee_id)
    if employee is None:
        return None

    ensure_employee_code_available(
        db,
        payload.employee_code,
        exclude_employee_id=employee_id,
    )
    _ensure_department_exists(db, payload.department)
    _ensure_position_exists(db, payload.position)

    for field, value in payload.model_dump().items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)
    return employee


def delete_employee(db: Session, employee_id: int) -> bool:
    employee = get_employee(db, employee_id)
    if employee is None:
        return False

    related_count = int(
        db.scalar(
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.employee_id == employee_id)
        )
        or 0
    )
    related_count += int(
        db.scalar(
            select(func.count())
            .select_from(AttendanceEvent)
            .where(AttendanceEvent.employee_id == employee_id)
        )
        or 0
    )
    if related_count > 0:
        raise EmployeeHasRelatedDataError(
            "Nhân viên đã có dữ liệu chấm công hoặc enrollment. "
            "Hãy chuyển trạng thái sang Tạm ngưng để giữ lịch sử báo cáo."
        )

    db.delete(employee)
    db.commit()
    return True


def list_departments(db: Session) -> list[str]:
    """Return sorted list of distinct, non-empty department names."""
    stmt = (
        select(Employee.department)
        .where(Employee.department.isnot(None), Employee.department != "")
        .distinct()
        .order_by(Employee.department.asc())
    )
    return list(db.scalars(stmt).all())


def ensure_employee_code_available(
    db: Session,
    employee_code: str,
    *,
    exclude_employee_id: int | None = None,
) -> None:
    stmt = select(Employee).where(func.lower(Employee.employee_code) == employee_code.lower())
    if exclude_employee_id is not None:
        stmt = stmt.where(Employee.id != exclude_employee_id)

    if db.scalar(stmt) is not None:
        raise DuplicateEmployeeCodeError


def _ensure_department_exists(db: Session, name: str) -> None:
    stmt = select(Department).where(func.lower(Department.name) == name.strip().lower())
    if db.scalar(stmt) is None:
        raise InvalidDepartmentError(
            f"Phòng ban '{name}' không tồn tại. Vui lòng tạo trong mục Danh mục trước."
        )


def _ensure_position_exists(db: Session, name: str) -> None:
    stmt = select(Position).where(func.lower(Position.name) == name.strip().lower())
    if db.scalar(stmt) is None:
        raise InvalidPositionError(
            f"Chức vụ '{name}' không tồn tại. Vui lòng tạo trong mục Danh mục trước."
        )
