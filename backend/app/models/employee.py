from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    department: Mapped[str] = mapped_column(String(128))
    position: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    attendance_events: Mapped[list["AttendanceEvent"]] = relationship(
        back_populates="employee",
    )

    @property
    def face_data_status(self) -> str:
        if not self.enrollments:
            return "missing"

        latest = max(
            self.enrollments,
            key=lambda enrollment: (enrollment.created_at, enrollment.id),
        )
        if latest.status == "pending":
            return "pending"
        if latest.status == "success":
            return "enrolled" if latest.processed_count > 0 else "failed"
        if latest.status == "failed":
            return "failed"
        return "missing"
