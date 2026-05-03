from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.models.employee import Employee
from backend.app.schemas.employee import EmployeeCreate, EmployeeUpdate


class DuplicateEmployeeCodeError(Exception):
    pass


def list_employees(
    db: Session,
    *,
    q: str | None,
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

    total_stmt = select(func.count()).select_from(Employee)
    items_stmt = select(Employee).order_by(Employee.id.asc())

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

    for field, value in payload.model_dump().items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)
    return employee


def delete_employee(db: Session, employee_id: int) -> bool:
    employee = get_employee(db, employee_id)
    if employee is None:
        return False

    db.delete(employee)
    db.commit()
    return True


def ensure_employee_code_available(
    db: Session,
    employee_code: str,
    *,
    exclude_employee_id: int | None = None,
) -> None:
    stmt = select(Employee).where(Employee.employee_code == employee_code)
    if exclude_employee_id is not None:
        stmt = stmt.where(Employee.id != exclude_employee_id)

    if db.scalar(stmt) is not None:
        raise DuplicateEmployeeCodeError
