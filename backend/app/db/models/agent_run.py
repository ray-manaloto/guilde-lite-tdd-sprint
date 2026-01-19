"""Agent run models for checkpointing (PostgreSQL)."""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class AgentRun(Base, TimestampMixin):
    """Agent run for a TDD workflow execution."""

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    model_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    workspace_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    span_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    candidates: Mapped[list["AgentCandidate"]] = relationship(
        "AgentCandidate",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    checkpoints: Mapped[list["AgentCheckpoint"]] = relationship(
        "AgentCheckpoint",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    decision: Mapped["AgentDecision | None"] = relationship(
        "AgentDecision",
        back_populates="run",
        uselist=False,
        cascade="all, delete-orphan",
    )


class AgentCandidate(Base, TimestampMixin):
    """Candidate result from a subagent run."""

    __tablename__ = "agent_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_calls: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    span_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="candidates")


class AgentDecision(Base, TimestampMixin):
    """Judge decision for an agent run."""

    __tablename__ = "agent_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    score: Mapped[float | None] = mapped_column(nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    span_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="decision")


class AgentCheckpoint(Base, TimestampMixin):
    """Checkpoint snapshot for replaying a run."""

    __tablename__ = "agent_checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    workspace_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    span_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="checkpoints")
