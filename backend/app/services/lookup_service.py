"""Generic CRUD service for simple lookup tables (Department, Position)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.base import Base


class DuplicateLookupNameError(Exception):
    pass


class LookupInUseError(Exception):
    """Raised when trying to delete a lookup item that is still referenced."""

    pass


def list_lookup_items(
    db: Session,
    model: type[Base],
    *,
    q: str | None = None,
) -> tuple[list[Base], int]:
    """List all items of the given lookup model, optionally filtered by search."""
    filters = []
    if q and q.strip():
        keyword = f"%{q.strip()}%"
        filters.append(model.name.ilike(keyword))

    total_stmt = select(func.count()).select_from(model)
    items_stmt = select(model).order_by(model.name.asc())

    if filters:
        total_stmt = total_stmt.where(*filters)
        items_stmt = items_stmt.where(*filters)

    total = db.scalar(total_stmt) or 0
    items = db.scalars(items_stmt).all()
    return list(items), total


def get_lookup_item(db: Session, model: type[Base], item_id: int) -> Base | None:
    return db.get(model, item_id)


def create_lookup_item(db: Session, model: type[Base], name: str) -> Base:
    _ensure_name_available(db, model, name)
    item = model(name=name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_lookup_item(
    db: Session,
    model: type[Base],
    item_id: int,
    name: str,
) -> Base | None:
    item = get_lookup_item(db, model, item_id)
    if item is None:
        return None

    _ensure_name_available(db, model, name, exclude_id=item_id)
    item.name = name
    db.commit()
    db.refresh(item)
    return item


def delete_lookup_item(
    db: Session,
    model: type[Base],
    item_id: int,
    *,
    employee_field: str | None = None,
) -> bool:
    """Delete a lookup item. If employee_field is given, check no employees reference it."""
    item = get_lookup_item(db, model, item_id)
    if item is None:
        return False

    if employee_field:
        from backend.app.models.employee import Employee

        field = getattr(Employee, employee_field)
        count = db.scalar(
            select(func.count()).select_from(Employee).where(
                func.lower(field) == item.name.lower()
            )
        )
        if count:
            raise LookupInUseError(
                f"Không thể xóa vì còn {count} nhân viên đang sử dụng giá trị này."
            )

    db.delete(item)
    db.commit()
    return True


def list_lookup_names(db: Session, model: type[Base]) -> list[str]:
    """Return sorted list of all names for the given lookup model."""
    stmt = select(model.name).order_by(model.name.asc())
    return list(db.scalars(stmt).all())


def _ensure_name_available(
    db: Session,
    model: type[Base],
    name: str,
    *,
    exclude_id: int | None = None,
) -> None:
    stmt = select(model).where(func.lower(model.name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(model.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise DuplicateLookupNameError
