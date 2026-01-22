"""WebSocket event types and schemas for real-time sprint updates.

This module provides typed event schemas for broadcasting granular updates
during sprint execution, including candidate generation, judge decisions,
and phase transitions.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SprintEventType(str, Enum):
    """Event types for sprint WebSocket messages."""

    # Legacy event (backwards compatible)
    SPRINT_UPDATE = "sprint_update"

    # Candidate events
    CANDIDATE_STARTED = "candidate.started"
    CANDIDATE_GENERATED = "candidate.generated"
    CANDIDATE_FAILED = "candidate.failed"

    # Judge events
    JUDGE_STARTED = "judge.started"
    JUDGE_DECIDED = "judge.decided"

    # Phase events
    PHASE_STARTED = "phase.started"
    PHASE_COMPLETED = "phase.completed"
    PHASE_FAILED = "phase.failed"

    # Workflow events
    WORKFLOW_STATUS = "workflow.status"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"

    # Tool events
    TOOL_CALLED = "tool.called"
    TOOL_RESULT = "tool.result"


class BaseSprintEvent(BaseModel):
    """Base schema for all sprint WebSocket events."""

    event: SprintEventType
    sprint_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sequence: int = Field(default=0, description="Monotonic sequence number for ordering")

    model_config = {"use_enum_values": True}


class CandidateData(BaseModel):
    """Data about a candidate response."""

    candidate_id: str | None = None
    provider: str
    model_name: str | None = None
    agent_name: str | None = None
    output: str | None = None
    duration_ms: int | None = None
    trace_id: str | None = None
    success: bool = True
    error: str | None = None


class CandidateStartedEvent(BaseSprintEvent):
    """Event when a candidate agent starts processing."""

    event: SprintEventType = SprintEventType.CANDIDATE_STARTED
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        sprint_id: str | UUID,
        provider: str,
        model_name: str | None = None,
        phase: str | None = None,
        sequence: int = 0,
    ) -> "CandidateStartedEvent":
        return cls(
            sprint_id=str(sprint_id),
            sequence=sequence,
            data={
                "provider": provider,
                "model_name": model_name,
                "phase": phase,
            },
        )


class CandidateGeneratedEvent(BaseSprintEvent):
    """Event when a candidate completes generation."""

    event: SprintEventType = SprintEventType.CANDIDATE_GENERATED
    data: CandidateData

    @classmethod
    def create(
        cls,
        sprint_id: str | UUID,
        candidate: CandidateData,
        sequence: int = 0,
    ) -> "CandidateGeneratedEvent":
        return cls(
            sprint_id=str(sprint_id),
            sequence=sequence,
            data=candidate,
        )


class CandidateFailedEvent(BaseSprintEvent):
    """Event when a candidate fails to generate."""

    event: SprintEventType = SprintEventType.CANDIDATE_FAILED
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        sprint_id: str | UUID,
        provider: str,
        error: str,
        model_name: str | None = None,
        sequence: int = 0,
    ) -> "CandidateFailedEvent":
        return cls(
            sprint_id=str(sprint_id),
            sequence=sequence,
            data={
                "provider": provider,
                "model_name": model_name,
                "error": error,
            },
        )


class JudgeDecisionData(BaseModel):
    """Data about a judge decision."""

    winner_candidate_id: str | None = None
    winner_provider: str | None = None
    winner_model: str | None = None
    score: float | None = None
    rationale: str | None = None
    model_name: str | None = None
    trace_id: str | None = None


class JudgeStartedEvent(BaseSprintEvent):
    """Event when the judge starts evaluating candidates."""

    event: SprintEventType = SprintEventType.JUDGE_STARTED
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        sprint_id: str | UUID,
        candidate_count: int,
        phase: str | None = None,
        sequence: int = 0,
    ) -> "JudgeStartedEvent":
        return cls(
            sprint_id=str(sprint_id),
            sequence=sequence,
            data={
                "candidate_count": candidate_count,
                "phase": phase,
            },
        )


class JudgeDecidedEvent(BaseSprintEvent):
    """Event when the judge makes a decision."""

    event: SprintEventType = SprintEventType.JUDGE_DECIDED
    data: JudgeDecisionData

    @classmethod
    def create(
        cls,
        sprint_id: str | UUID,
        decision: JudgeDecisionData,
        sequence: int = 0,
    ) -> "JudgeDecidedEvent":
        return cls(
            sprint_id=str(sprint_id),
            sequence=sequence,
            data=decision,
        )


class PhaseData(BaseModel):
    """Data about a phase."""

    phase: str
    attempt: int | None = None
    details: str | None = None
    status: str | None = None
    duration_ms: int | None = None
    output: dict[str, Any] | None = None


class PhaseStartedEvent(BaseSprintEvent):
    """Event when a phase begins."""

    event: SprintEventType = SprintEventType.PHASE_STARTED
    data: PhaseData

    @classmethod
    def create(
        cls,
        sprint_id: str | UUID,
        phase: str,
        attempt: int | None = None,
        details: str | None = None,
        sequence: int = 0,
    ) -> "PhaseStartedEvent":
        return cls(
            sprint_id=str(sprint_id),
            sequence=sequence,
            data=PhaseData(phase=phase, attempt=attempt, details=details),
        )


class PhaseCompletedEvent(BaseSprintEvent):
    """Event when a phase completes successfully."""

    event: SprintEventType = SprintEventType.PHASE_COMPLETED
    data: PhaseData

    @classmethod
    def create(
        cls,
        sprint_id: str | UUID,
        phase: str,
        duration_ms: int | None = None,
        output: dict[str, Any] | None = None,
        details: str | None = None,
        sequence: int = 0,
    ) -> "PhaseCompletedEvent":
        return cls(
            sprint_id=str(sprint_id),
            sequence=sequence,
            data=PhaseData(
                phase=phase,
                status="completed",
                duration_ms=duration_ms,
                output=output,
                details=details,
            ),
        )


class PhaseFailedEvent(BaseSprintEvent):
    """Event when a phase fails."""

    event: SprintEventType = SprintEventType.PHASE_FAILED
    data: PhaseData

    @classmethod
    def create(
        cls,
        sprint_id: str | UUID,
        phase: str,
        details: str | None = None,
        attempt: int | None = None,
        sequence: int = 0,
    ) -> "PhaseFailedEvent":
        return cls(
            sprint_id=str(sprint_id),
            sequence=sequence,
            data=PhaseData(phase=phase, status="failed", details=details, attempt=attempt),
        )


class WorkflowStatusData(BaseModel):
    """Data about workflow status."""

    status: str
    phase: str | None = None
    details: str | None = None
    progress: float | None = None
    total_phases: int | None = None
    completed_phases: int | None = None


class WorkflowStatusEvent(BaseSprintEvent):
    """Event for overall workflow status changes."""

    event: SprintEventType = SprintEventType.WORKFLOW_STATUS
    data: WorkflowStatusData

    @classmethod
    def create(
        cls,
        sprint_id: str | UUID,
        status: str,
        phase: str | None = None,
        details: str | None = None,
        progress: float | None = None,
        sequence: int = 0,
    ) -> "WorkflowStatusEvent":
        return cls(
            sprint_id=str(sprint_id),
            sequence=sequence,
            data=WorkflowStatusData(
                status=status,
                phase=phase,
                details=details,
                progress=progress,
            ),
        )


class ToolEventData(BaseModel):
    """Data about a tool call."""

    tool_name: str
    args: dict[str, Any] | None = None
    result: str | None = None
    duration_ms: int | None = None
    success: bool = True
    error: str | None = None


class ToolCalledEvent(BaseSprintEvent):
    """Event when a tool is called."""

    event: SprintEventType = SprintEventType.TOOL_CALLED
    data: ToolEventData

    @classmethod
    def create(
        cls,
        sprint_id: str | UUID,
        tool_name: str,
        args: dict[str, Any] | None = None,
        sequence: int = 0,
    ) -> "ToolCalledEvent":
        return cls(
            sprint_id=str(sprint_id),
            sequence=sequence,
            data=ToolEventData(tool_name=tool_name, args=args),
        )


class ToolResultEvent(BaseSprintEvent):
    """Event when a tool returns a result."""

    event: SprintEventType = SprintEventType.TOOL_RESULT
    data: ToolEventData

    @classmethod
    def create(
        cls,
        sprint_id: str | UUID,
        tool_name: str,
        result: str | None = None,
        duration_ms: int | None = None,
        success: bool = True,
        error: str | None = None,
        sequence: int = 0,
    ) -> "ToolResultEvent":
        return cls(
            sprint_id=str(sprint_id),
            sequence=sequence,
            data=ToolEventData(
                tool_name=tool_name,
                result=result,
                duration_ms=duration_ms,
                success=success,
                error=error,
            ),
        )


# Type alias for all event types
SprintEvent = (
    CandidateStartedEvent
    | CandidateGeneratedEvent
    | CandidateFailedEvent
    | JudgeStartedEvent
    | JudgeDecidedEvent
    | PhaseStartedEvent
    | PhaseCompletedEvent
    | PhaseFailedEvent
    | WorkflowStatusEvent
    | ToolCalledEvent
    | ToolResultEvent
)
