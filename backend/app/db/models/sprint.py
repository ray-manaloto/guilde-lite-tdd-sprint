"""Sprint database models."""

from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class SprintStatus(StrEnum):
    """Lifecycle status for a sprint."""

    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"


class SprintItemStatus(StrEnum):
    """Workflow status for sprint items."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


class Sprint(Base, TimestampMixin):
    """Sprint model."""

    __tablename__ = "sprints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spec_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("specs.id", ondelete="SET NULL"),
        nullable=True,
    )
    track_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SprintStatus] = mapped_column(
        Enum(SprintStatus, name="sprint_status"),
        default=SprintStatus.PLANNED,
        nullable=False,
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    items: Mapped[list[SprintItem]] = relationship(
        back_populates="sprint",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Sprint(id={self.id}, name={self.name}, status={self.status})>"


class SprintItem(Base, TimestampMixin):
    """Sprint item model."""

    __tablename__ = "sprint_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sprints.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SprintItemStatus] = mapped_column(
        Enum(SprintItemStatus, name="sprint_item_status"),
        default=SprintItemStatus.TODO,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    estimate_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    sprint: Mapped[Sprint] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return f"<SprintItem(id={self.id}, title={self.title}, status={self.status})>"
