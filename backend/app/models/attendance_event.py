from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class AttendanceEvent(Base):
    __tablename__ = "attendance_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(32), index=True)
    attendance_status: Mapped[str] = mapped_column(String(32), index=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    camera_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    snapshot_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    employee: Mapped["Employee | None"] = relationship(back_populates="attendance_events")
