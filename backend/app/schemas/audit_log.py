from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditLogRead(BaseModel):
    id: int
    actor_user_id: int | None
    actor_username: str | None
    actor_role: str | None
    action: str
    resource_type: str
    resource_id: str | None
    resource_label: str | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]
    total: int
