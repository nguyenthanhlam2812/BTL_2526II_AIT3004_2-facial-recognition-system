from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import require_owner
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.audit_log import AuditLogListResponse
from backend.app.services.audit_log_service import list_audit_logs as list_audit_logs_service


router = APIRouter(prefix="/audit/logs", tags=["audit"])


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    q: str | None = Query(default=None),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    actor_user_id: int | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_owner),
) -> AuditLogListResponse:
    items, total = list_audit_logs_service(
        db,
        q=q,
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
        from_=from_,
        to=to,
        page=page,
        page_size=page_size,
    )
    return AuditLogListResponse(items=items, total=total)
