"""Schemas for agent run checkpointing."""

from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class AgentRunBase(BaseSchema):
    """Base schema for an agent run."""

    status: str = Field(default="pending", max_length=20)
    input_payload: dict[str, Any] = Field(default_factory=dict)
    model_config: dict[str, Any] = Field(default_factory=dict)
    workspace_ref: str | None = Field(default=None, max_length=255)


class AgentRunCreate(AgentRunBase):
    """Create an agent run."""

    user_id: UUID | None = Field(default=None)
    pass


class AgentRunUpdate(BaseSchema):
    """Update fields for an agent run."""

    status: str | None = Field(default=None, max_length=20)
    workspace_ref: str | None = Field(default=None, max_length=255)


class AgentRunRead(AgentRunBase, TimestampSchema):
    """Read an agent run."""

    id: UUID
    user_id: UUID | None = None
    trace_id: str | None = None
    span_id: str | None = None


class AgentRunList(BaseSchema):
    """List of agent runs."""

    items: list[AgentRunRead]
    total: int


class AgentCandidateBase(BaseSchema):
    """Base schema for a subagent candidate."""

    agent_name: str = Field(max_length=100)
    provider: str | None = Field(default=None, max_length=50)
    model_name: str | None = Field(default=None, max_length=100)
    output: str | None = None
    tool_calls: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)


class AgentCandidateCreate(AgentCandidateBase):
    """Create a subagent candidate."""

    pass


class AgentCandidateRead(AgentCandidateBase, TimestampSchema):
    """Read a subagent candidate."""

    id: UUID
    run_id: UUID
    trace_id: str | None = None
    span_id: str | None = None


class AgentCandidateList(BaseSchema):
    """List of candidates."""

    items: list[AgentCandidateRead]
    total: int


class AgentDecisionBase(BaseSchema):
    """Base schema for a judge decision."""

    candidate_id: UUID | None = None
    score: float | None = None
    rationale: str | None = None
    model_name: str | None = Field(default=None, max_length=100)


class AgentDecisionCreate(AgentDecisionBase):
    """Create a judge decision."""

    pass


class AgentDecisionRead(AgentDecisionBase, TimestampSchema):
    """Read a judge decision."""

    id: UUID
    run_id: UUID
    trace_id: str | None = None
    span_id: str | None = None


class AgentCheckpointBase(BaseSchema):
    """Base schema for a checkpoint."""

    sequence: int = 0
    label: str | None = Field(default=None, max_length=100)
    state: dict[str, Any] = Field(default_factory=dict)
    workspace_ref: str | None = Field(default=None, max_length=255)


class AgentCheckpointCreate(AgentCheckpointBase):
    """Create a checkpoint."""

    pass


class AgentCheckpointRead(AgentCheckpointBase, TimestampSchema):
    """Read a checkpoint."""

    id: UUID
    run_id: UUID
    trace_id: str | None = None
    span_id: str | None = None


class AgentCheckpointList(BaseSchema):
    """List of checkpoints."""

    items: list[AgentCheckpointRead]
    total: int
