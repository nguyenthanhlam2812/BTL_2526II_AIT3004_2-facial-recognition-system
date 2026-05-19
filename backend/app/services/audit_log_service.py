from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.models.audit_log import AuditLog
from backend.app.models.user import User
from backend.app.schemas.audit_log import AuditLogRead


def record_audit_log(
    db: Session,
    *,
    actor: User | None,
    action: str,
    resource_type: str,
    resource_id: int | str | None = None,
    resource_label: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        actor_user_id=actor.id if actor is not None else None,
        actor_username=actor.username if actor is not None else None,
        actor_role=actor.role if actor is not None else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        resource_label=resource_label,
        metadata_json=_serialize_metadata(metadata),
    )
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    return audit_log


def list_audit_logs(
    db: Session,
    *,
    q: str | None,
    action: str | None,
    resource_type: str | None,
    actor_user_id: int | None,
    from_: datetime | None,
    to: datetime | None,
    page: int,
    page_size: int,
) -> tuple[list[AuditLogRead], int]:
    filters = []
    query = (q or "").strip().lower()
    if query:
        pattern = f"%{query}%"
        filters.append(
            or_(
                func.lower(AuditLog.actor_username).like(pattern),
                func.lower(AuditLog.action).like(pattern),
                func.lower(AuditLog.resource_type).like(pattern),
                func.lower(AuditLog.resource_label).like(pattern),
                func.lower(AuditLog.metadata_json).like(pattern),
            )
        )
    if action and action.strip():
        filters.append(AuditLog.action == action.strip())
    if resource_type and resource_type.strip():
        filters.append(AuditLog.resource_type == resource_type.strip())
    if actor_user_id is not None:
        filters.append(AuditLog.actor_user_id == actor_user_id)
    if from_ is not None:
        filters.append(AuditLog.created_at >= from_)
    if to is not None:
        filters.append(AuditLog.created_at <= to)

    count_stmt = select(func.count()).select_from(AuditLog)
    items_stmt = select(AuditLog).order_by(AuditLog.id.desc())
    if filters:
        count_stmt = count_stmt.where(*filters)
        items_stmt = items_stmt.where(*filters)

    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(items_stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return [_to_read_model(row) for row in rows], total


def _serialize_metadata(metadata: Mapping[str, Any] | None) -> str:
    return json.dumps(dict(metadata or {}), ensure_ascii=False, sort_keys=True, default=str)


def _deserialize_metadata(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _to_read_model(row: AuditLog) -> AuditLogRead:
    return AuditLogRead(
        id=row.id,
        actor_user_id=row.actor_user_id,
        actor_username=row.actor_username,
        actor_role=row.actor_role,
        action=row.action,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        resource_label=row.resource_label,
        metadata=_deserialize_metadata(row.metadata_json),
        created_at=row.created_at,
    )
