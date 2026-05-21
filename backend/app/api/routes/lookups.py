"""CRUD routes for Department and Position lookup tables."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import require_admin, require_operator
from backend.app.db.session import get_db
from backend.app.models.department import Department
from backend.app.models.position import Position
from backend.app.models.user import User
from backend.app.schemas.employee import DeleteResponse
from backend.app.schemas.lookup import (
    LookupItemCreate,
    LookupItemListResponse,
    LookupItemRead,
)
from backend.app.services.lookup_service import (
    DuplicateLookupNameError,
    LookupInUseError,
    create_lookup_item,
    delete_lookup_item,
    list_lookup_items,
    list_lookup_names,
    update_lookup_item,
)

router = APIRouter(tags=["lookups"])


# ── Departments ──────────────────────────────────────────────────────────

@router.get("/departments", response_model=LookupItemListResponse)
def list_departments(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> LookupItemListResponse:
    items, total = list_lookup_items(db, Department, q=q)
    return LookupItemListResponse(items=items, total=total)


@router.get("/departments/names", response_model=list[str])
def list_department_names(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[str]:
    """Return flat list of department names for select/combobox."""
    return list_lookup_names(db, Department)


@router.post("/departments", response_model=LookupItemRead, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: LookupItemCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_operator),
) -> LookupItemRead:
    try:
        return create_lookup_item(db, Department, payload.name)
    except DuplicateLookupNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phòng ban này đã tồn tại.",
        ) from exc


@router.put("/departments/{item_id}", response_model=LookupItemRead)
def update_department(
    item_id: int,
    payload: LookupItemCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_operator),
) -> LookupItemRead:
    try:
        item = update_lookup_item(db, Department, item_id, payload.name)
    except DuplicateLookupNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phòng ban này đã tồn tại.",
        ) from exc
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phòng ban.")
    return item


@router.delete("/departments/{item_id}", response_model=DeleteResponse)
def delete_department(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_operator),
) -> DeleteResponse:
    try:
        deleted = delete_lookup_item(db, Department, item_id, employee_field="department")
    except LookupInUseError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phòng ban.")
    return DeleteResponse(ok=True)


# ── Positions ────────────────────────────────────────────────────────────

@router.get("/positions", response_model=LookupItemListResponse)
def list_positions(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> LookupItemListResponse:
    items, total = list_lookup_items(db, Position, q=q)
    return LookupItemListResponse(items=items, total=total)


@router.get("/positions/names", response_model=list[str])
def list_position_names(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[str]:
    """Return flat list of position names for select/combobox."""
    return list_lookup_names(db, Position)


@router.post("/positions", response_model=LookupItemRead, status_code=status.HTTP_201_CREATED)
def create_position(
    payload: LookupItemCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_operator),
) -> LookupItemRead:
    try:
        return create_lookup_item(db, Position, payload.name)
    except DuplicateLookupNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chức vụ này đã tồn tại.",
        ) from exc


@router.put("/positions/{item_id}", response_model=LookupItemRead)
def update_position(
    item_id: int,
    payload: LookupItemCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_operator),
) -> LookupItemRead:
    try:
        item = update_lookup_item(db, Position, item_id, payload.name)
    except DuplicateLookupNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chức vụ này đã tồn tại.",
        ) from exc
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy chức vụ.")
    return item


@router.delete("/positions/{item_id}", response_model=DeleteResponse)
def delete_position(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_operator),
) -> DeleteResponse:
    try:
        deleted = delete_lookup_item(db, Position, item_id, employee_field="position")
    except LookupInUseError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy chức vụ.")
    return DeleteResponse(ok=True)
