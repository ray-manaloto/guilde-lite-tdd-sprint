"""Workflow schemas for sprint visualization."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema


class WorkflowStatus(str, Enum):
    """Overall workflow status."""

    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class PhaseStatus(str, Enum):
    """Status of a workflow phase."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TokenUsage(BaseSchema):
    """Token usage metrics for a candidate or phase."""

    input_tokens: int = Field(default=0, description="Number of input tokens")
    output_tokens: int = Field(default=0, description="Number of output tokens")
    total_tokens: int = Field(default=0, description="Total tokens used")


class TokenCost(BaseSchema):
    """Cost metrics for token usage."""

    input_cost: float = Field(default=0.0, description="Cost for input tokens (USD)")
    output_cost: float = Field(default=0.0, description="Cost for output tokens (USD)")
    total_cost: float = Field(default=0.0, description="Total cost (USD)")


class CandidateSummary(BaseSchema):
    """Summary of a candidate response from a provider."""

    provider: str = Field(..., description="Provider name (e.g., openai, anthropic)")
    model: str | None = Field(default=None, description="Model used")
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    duration_ms: int | None = Field(default=None, description="Duration in milliseconds")
    tokens: TokenUsage = Field(default_factory=TokenUsage)
    success: bool = Field(default=True, description="Whether candidate succeeded")
    error: str | None = Field(default=None, description="Error message if failed")
    trace_id: str | None = Field(default=None, description="Logfire trace ID")
    trace_url: str | None = Field(default=None, description="Logfire trace URL")


class CandidateResponse(CandidateSummary):
    """Full candidate response including content."""

    response: dict[str, Any] = Field(default_factory=dict, description="Candidate response data")


class JudgeDecisionResponse(BaseSchema):
    """Response schema for a judge decision."""

    model: str | None = Field(default=None, description="Judge model used")
    winner: str | None = Field(default=None, description="Winning provider")
    score: float | None = Field(default=None, description="Confidence score")
    rationale: str | None = Field(default=None, description="Reasoning for decision")
    trace_id: str | None = Field(default=None)
    trace_url: str | None = Field(default=None)


class TimelineEventResponse(BaseSchema):
    """Response schema for a timeline event."""

    sequence: int = Field(..., description="Event sequence number")
    event_type: str = Field(..., description="Type of event")
    timestamp: datetime = Field(..., description="When event occurred")
    state: str | None = Field(default=None, description="Workflow state at this point")
    phase: str | None = Field(default=None, description="Current phase name")
    checkpoint_id: str | None = Field(default=None, description="Associated checkpoint")
    trace_id: str | None = Field(default=None)
    trace_url: str | None = Field(default=None)
    duration_ms: int | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PhaseResponse(BaseSchema):
    """Response schema for a workflow phase."""

    phase: str = Field(..., description="Phase name")
    sequence: int = Field(..., description="Phase execution order")
    status: PhaseStatus = Field(default=PhaseStatus.PENDING)
    start_time: datetime | None = Field(default=None)
    end_time: datetime | None = Field(default=None)
    duration_ms: int | None = Field(default=None)
    checkpoint_before: str | None = Field(default=None)
    checkpoint_after: str | None = Field(default=None)
    llm_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Model configuration used",
    )
    input_data: dict[str, Any] = Field(default_factory=dict, description="Phase input data")
    output_data: dict[str, Any] = Field(default_factory=dict, description="Phase output data")
    candidates: list[CandidateSummary] = Field(default_factory=list)
    judge_result: JudgeDecisionResponse | None = Field(default=None)
    trace_id: str | None = Field(default=None)
    trace_url: str | None = Field(default=None)


class TimelineResponse(BaseSchema):
    """Response schema for the workflow timeline."""

    sprint_id: UUID = Field(..., description="Sprint UUID")
    total_duration_ms: int | None = Field(default=None)
    events: list[TimelineEventResponse] = Field(default_factory=list)


class ArtifactInfo(BaseSchema):
    """Information about a workflow artifact."""

    name: str = Field(..., description="Artifact name")
    path: str = Field(..., description="Relative path within sprint directory")
    type: str = Field(..., description="Artifact type (json, md, code, etc.)")
    size_bytes: int | None = Field(default=None, description="File size in bytes")
    created_at: datetime | None = Field(default=None)


class ArtifactsListResponse(BaseSchema):
    """Response schema for listing workflow artifacts."""

    sprint_id: UUID = Field(..., description="Sprint UUID")
    base_path: str = Field(..., description="Base directory path")
    artifacts: list[ArtifactInfo] = Field(default_factory=list)


class WorkflowResponse(BaseSchema):
    """Full workflow state response."""

    sprint_id: UUID = Field(..., description="Sprint UUID")
    spec_id: UUID | None = Field(default=None, description="Associated spec UUID")
    status: WorkflowStatus = Field(default=WorkflowStatus.PLANNED)
    current_phase: str | None = Field(default=None, description="Currently active phase")
    current_checkpoint: str | None = Field(default=None, description="Current checkpoint ID")
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)
    total_duration_ms: int | None = Field(default=None)
    phases: list[PhaseResponse] = Field(default_factory=list)
    timeline: list[TimelineEventResponse] = Field(default_factory=list)
    aggregated_tokens: TokenUsage = Field(default_factory=TokenUsage)
    aggregated_cost: TokenCost = Field(default_factory=TokenCost)
    logfire_project_url: str | None = Field(default=None)
