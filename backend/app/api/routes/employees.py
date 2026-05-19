from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import require_admin, require_operator
from backend.app.db.session import get_db
from backend.app.models.employee import Employee
from backend.app.models.user import User
from backend.app.schemas.employee import (
    DeleteResponse,
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeRead,
    EmployeeUpdate,
)
from backend.app.services.employee_service import (
    DuplicateEmployeeCodeError,
    create_employee as create_employee_service,
    delete_employee as delete_employee_service,
    list_departments as list_departments_service,
    list_employees as list_employees_service,
    update_employee as update_employee_service,
)
from backend.app.services.audit_log_service import record_audit_log


router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=EmployeeListResponse)
def list_employees(
    q: str | None = Query(default=None),
    department: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> EmployeeListResponse:
    items, total = list_employees_service(
        db,
        q=q,
        department=department,
        page=page,
        page_size=page_size,
    )
    return EmployeeListResponse(items=items, total=total)


@router.get("/departments", response_model=list[str])
def list_departments(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[str]:
    return list_departments_service(db)


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> EmployeeRead:
    try:
        employee = create_employee_service(db, payload)
    except DuplicateEmployeeCodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee code already exists.",
        ) from exc
    record_audit_log(
        db,
        actor=current_user,
        action="employee.create",
        resource_type="employee",
        resource_id=employee.id,
        resource_label=f"{employee.employee_code} - {employee.full_name}",
        metadata={
            "employee_code": employee.employee_code,
            "department": employee.department,
            "status": employee.status,
        },
    )
    return employee


@router.put("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> EmployeeRead:
    try:
        employee = update_employee_service(db, employee_id, payload)
    except DuplicateEmployeeCodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee code already exists.",
        ) from exc

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )

    record_audit_log(
        db,
        actor=current_user,
        action="employee.update",
        resource_type="employee",
        resource_id=employee.id,
        resource_label=f"{employee.employee_code} - {employee.full_name}",
        metadata={
            "employee_code": employee.employee_code,
            "department": employee.department,
            "status": employee.status,
        },
    )
    return employee


@router.delete("/{employee_id}", response_model=DeleteResponse)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> DeleteResponse:
    target = db.get(Employee, employee_id)
    target_label = (
        f"{target.employee_code} - {target.full_name}" if target is not None else None
    )
    target_code = target.employee_code if target is not None else None
    deleted = delete_employee_service(db, employee_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )

    record_audit_log(
        db,
        actor=current_user,
        action="employee.delete",
        resource_type="employee",
        resource_id=employee_id,
        resource_label=target_label,
        metadata={"employee_code": target_code},
    )
    return DeleteResponse(ok=True)
