from __future__ import annotations

import logging

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from backend.app.config import get_settings
from backend.app.models.attendance_event import AttendanceEvent
from backend.app.models.department import Department
from backend.app.models.employee import Employee
from backend.app.models.enrollment import Enrollment
from backend.app.models.enrollment_image import EnrollmentImage
from backend.app.models.position import Position
from backend.app.schemas.employee import EmployeeCreate, EmployeeUpdate
from backend.app.services.minio_service import delete_objects
from backend.app.services.qdrant_service import (
    VectorStoreError,
    delete_face_embeddings,
)


logger = logging.getLogger(__name__)


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
            "Hãy chuyển trạng thái sang Tạm ngưng để giữ lịch sử báo cáo "
            "hoặc dùng xóa vĩnh viễn (owner-only) để xóa cả dữ liệu khuôn mặt."
        )

    db.delete(employee)
    db.commit()
    return True


def force_delete_employee(db: Session, employee_id: int) -> dict[str, int] | None:
    """Force-delete an employee with biometric cleanup.

    Drops Qdrant face vectors and MinIO enrollment images, anonymises
    attendance history by setting ``employee_id`` to NULL, then deletes
    the employee row. Used when an admin needs to honour a privacy
    request (Nghị định 13/2023) or remove duplicate/test records that
    already have data attached.

    Returns a cleanup stats dict, or None if the employee does not exist.
    Biometric cleanup is best-effort: a Qdrant/MinIO failure logs a
    warning but does not block the SQL delete, since the caller has
    explicitly asked to remove this employee.
    """
    employee = get_employee(db, employee_id)
    if employee is None:
        return None

    image_rows = list(
        db.scalars(
            select(EnrollmentImage)
            .join(Enrollment, EnrollmentImage.enrollment_id == Enrollment.id)
            .where(Enrollment.employee_id == employee_id)
        ).all()
    )

    qdrant_point_ids: list[int] = []
    object_keys: list[str] = []
    for image in image_rows:
        if image.qdrant_point_id:
            try:
                qdrant_point_ids.append(int(image.qdrant_point_id))
            except (TypeError, ValueError):
                pass
        if image.object_key:
            object_keys.append(image.object_key)

    attendance_count = int(
        db.scalar(
            select(func.count())
            .select_from(AttendanceEvent)
            .where(AttendanceEvent.employee_id == employee_id)
        )
        or 0
    )

    if qdrant_point_ids:
        try:
            delete_face_embeddings(qdrant_point_ids)
        except VectorStoreError:
            logger.warning(
                "force_delete.qdrant_cleanup_failed employee_id=%s points=%s",
                employee_id,
                qdrant_point_ids,
            )

    if object_keys:
        settings = get_settings()
        delete_objects(settings.minio_bucket_enrollments, object_keys)

    # Anonymise attendance history explicitly. The FK has ON DELETE SET NULL
    # but sqlite (used in tests) does not enforce FKs by default, so we set
    # it ourselves for cross-engine consistency.
    db.execute(
        update(AttendanceEvent)
        .where(AttendanceEvent.employee_id == employee_id)
        .values(employee_id=None)
    )

    db.delete(employee)
    db.commit()

    return {
        "qdrant_points_deleted": len(qdrant_point_ids),
        "minio_objects_deleted": len(object_keys),
        "attendance_events_anonymized": attendance_count,
    }


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
