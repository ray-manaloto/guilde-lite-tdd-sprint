"""Spec workflow models."""

from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SpecComplexity(StrEnum):
    """Complexity tier for a spec."""

    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"


class SpecStatus(StrEnum):
    """Lifecycle status for a spec."""

    DRAFT = "draft"
    VALIDATED = "validated"
    APPROVED = "approved"
    REJECTED = "rejected"


class Spec(Base, TimestampMixin):
    """Spec model representing a spec workflow draft."""

    __tablename__ = "specs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    complexity: Mapped[SpecComplexity] = mapped_column(
        Enum(SpecComplexity, name="spec_complexity"),
        default=SpecComplexity.STANDARD,
        nullable=False,
    )
    status: Mapped[SpecStatus] = mapped_column(
        Enum(SpecStatus, name="spec_status"),
        default=SpecStatus.DRAFT,
        nullable=False,
    )
    phases: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    artifacts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<Spec(id={self.id}, title={self.title}, status={self.status})>"
