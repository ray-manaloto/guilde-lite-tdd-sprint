"""Workflow tracking service for sprint execution."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.config import settings

logger = logging.getLogger(__name__)


class SafeJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles non-serializable objects gracefully."""

    def default(self, obj: Any) -> Any:
        """Convert non-serializable objects to strings."""
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if hasattr(obj, "__dict__"):
            return str(obj)
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


def safe_json_dumps(data: Any, **kwargs: Any) -> str:
    """Safely serialize data to JSON, converting non-serializable objects to strings."""
    return json.dumps(data, cls=SafeJSONEncoder, **kwargs)


@dataclass
class TimelineEvent:
    """A single event in the workflow timeline."""

    sequence: int
    event_type: str
    timestamp: datetime
    state: str | None = None
    phase: str | None = None
    checkpoint_id: str | None = None
    trace_id: str | None = None
    trace_url: str | None = None
    duration_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "sequence": self.sequence,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "state": self.state,
            "phase": self.phase,
            "checkpoint_id": self.checkpoint_id,
            "trace_id": self.trace_id,
            "trace_url": self.trace_url,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class PhaseRecord:
    """Record of a phase execution."""

    phase: str
    sequence: int
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: int | None = None
    status: str = "in_progress"
    checkpoint_before: str | None = None
    checkpoint_after: str | None = None
    model_config: dict[str, Any] = field(default_factory=dict)
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    candidates: dict[str, Any] = field(default_factory=dict)
    judge_result: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None
    trace_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "phase": self.phase,
            "sequence": self.sequence,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "checkpoint_before": self.checkpoint_before,
            "checkpoint_after": self.checkpoint_after,
            "model_config": self.model_config,
            "input": self.input_data,
            "output": self.output_data,
            "candidates": self.candidates,
            "judge_result": self.judge_result,
            "trace_id": self.trace_id,
            "trace_url": self.trace_url,
        }


class WorkflowTracker:
    """Tracks workflow execution and persists artifacts to disk."""

    VERSION = "1.0.0"

    def __init__(self, sprint_id: UUID, spec_id: UUID | None = None, artifacts_dir: Path | None = None):
        """Initialize the workflow tracker.

        Args:
            sprint_id: The sprint UUID
            spec_id: The spec UUID (optional)
            artifacts_dir: Base directory for artifacts (defaults to settings)
        """
        self.sprint_id = sprint_id
        self.spec_id = spec_id
        self.artifacts_dir = artifacts_dir or settings.AUTOCODE_ARTIFACTS_DIR

        if self.artifacts_dir:
            self.base_dir = self.artifacts_dir / str(sprint_id)
        else:
            self.base_dir = None

        self.timeline: list[TimelineEvent] = []
        self.phases: dict[str, PhaseRecord] = {}
        self._sequence = 0
        self._start_time: datetime | None = None
        self._current_phase: str | None = None
        self._status = "planned"

    def _next_sequence(self) -> int:
        """Get the next sequence number."""
        self._sequence += 1
        return self._sequence

    def _get_trace_url(self, trace_id: str | None) -> str | None:
        """Build Logfire trace URL from trace ID."""
        if not trace_id:
            return None
        template = settings.LOGFIRE_TRACE_URL_TEMPLATE
        if template:
            return template.format(trace_id=trace_id)
        # Default Logfire URL pattern
        return f"https://logfire-us.pydantic.dev/sortakool/guilde-lite/trace/{trace_id}"

    def _ensure_directories(self) -> None:
        """Create the directory structure for artifacts."""
        if not self.base_dir:
            return

        dirs = [
            self.base_dir,
            self.base_dir / "spec",
            self.base_dir / "spec" / "questionnaire",
            self.base_dir / "spec" / "questionnaire" / "candidates",
            self.base_dir / "candidates",
            self.base_dir / "candidates" / "discovery",
            self.base_dir / "candidates" / "coding",
            self.base_dir / "candidates" / "verification",
            self.base_dir / "phases",
            self.base_dir / "checkpoints",
            self.base_dir / "branches",
            self.base_dir / "code",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    async def start_sprint(self, trace_id: str | None = None) -> None:
        """Initialize sprint tracking and create directory structure.

        Args:
            trace_id: Optional Logfire trace ID
        """
        self._start_time = datetime.now(timezone.utc)
        self._status = "planned"

        self._ensure_directories()

        # Record start event
        event = TimelineEvent(
            sequence=self._next_sequence(),
            event_type="sprint_started",
            timestamp=self._start_time,
            state=self._status,
            checkpoint_id="cp_001_start",
            trace_id=trace_id,
            trace_url=self._get_trace_url(trace_id),
        )
        self.timeline.append(event)

        # Save initial manifest
        await self._save_manifest()

        logger.info(f"Started workflow tracking for sprint {self.sprint_id}")

    async def record_event(
        self,
        event_type: str,
        phase: str | None = None,
        state: str | None = None,
        checkpoint_id: str | None = None,
        trace_id: str | None = None,
        duration_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TimelineEvent:
        """Record a timeline event.

        Args:
            event_type: Type of event (e.g., "phase_started", "candidates_generated")
            phase: Current phase name
            state: Sprint state at this point
            checkpoint_id: Associated checkpoint ID
            trace_id: Logfire trace ID
            duration_ms: Duration in milliseconds
            metadata: Additional event metadata

        Returns:
            The created TimelineEvent
        """
        if state:
            self._status = state

        event = TimelineEvent(
            sequence=self._next_sequence(),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            state=state or self._status,
            phase=phase or self._current_phase,
            checkpoint_id=checkpoint_id,
            trace_id=trace_id,
            trace_url=self._get_trace_url(trace_id),
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        self.timeline.append(event)

        return event

    async def start_phase(
        self,
        phase: str,
        model_config: dict[str, Any] | None = None,
        input_data: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> PhaseRecord:
        """Start tracking a phase.

        Args:
            phase: Phase name (e.g., "questionnaire", "discovery", "coding")
            model_config: Model configuration for this phase
            input_data: Input data for this phase
            trace_id: Logfire trace ID

        Returns:
            The PhaseRecord for this phase
        """
        self._current_phase = phase
        self._status = "active"

        # Create checkpoint before phase
        checkpoint_id = f"cp_{self._sequence + 1:03d}_before_{phase}"

        record = PhaseRecord(
            phase=phase,
            sequence=len(self.phases) + 1,
            start_time=datetime.now(timezone.utc),
            status="in_progress",
            checkpoint_before=checkpoint_id,
            model_config=model_config or {},
            input_data=input_data or {},
            trace_id=trace_id,
            trace_url=self._get_trace_url(trace_id),
        )
        self.phases[phase] = record

        # Record phase start event
        await self.record_event(
            event_type="phase_started",
            phase=phase,
            state="active",
            trace_id=trace_id,
            metadata={"model_config": model_config or {}},
        )

        logger.info(f"Started phase: {phase}")
        return record

    async def end_phase(
        self,
        phase: str,
        status: str = "completed",
        output_data: dict[str, Any] | None = None,
        candidates: dict[str, Any] | None = None,
        judge_result: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> PhaseRecord:
        """End phase tracking and save.

        Args:
            phase: Phase name
            status: Final status ("completed", "failed", "skipped")
            output_data: Output data from this phase
            candidates: Candidate results from providers
            judge_result: Judge decision if applicable
            trace_id: Logfire trace ID

        Returns:
            The updated PhaseRecord
        """
        if phase not in self.phases:
            raise ValueError(f"Phase {phase} was not started")

        record = self.phases[phase]
        record.end_time = datetime.now(timezone.utc)
        record.status = status
        record.duration_ms = int((record.end_time - record.start_time).total_seconds() * 1000)
        record.output_data = output_data or {}
        record.candidates = candidates or {}
        record.judge_result = judge_result or {}

        if trace_id:
            record.trace_id = trace_id
            record.trace_url = self._get_trace_url(trace_id)

        # Create checkpoint after phase
        record.checkpoint_after = f"cp_{self._sequence + 1:03d}_{phase}_complete"

        # Record phase end event
        await self.record_event(
            event_type="phase_completed",
            phase=phase,
            state="active" if status == "completed" else status,
            checkpoint_id=record.checkpoint_after,
            trace_id=trace_id,
            duration_ms=record.duration_ms,
            metadata={
                "status": status,
                "has_judge_result": bool(judge_result),
            },
        )

        # Save phase record to disk
        await self._save_phase_record(record)

        logger.info(f"Completed phase: {phase} (status={status}, duration={record.duration_ms}ms)")
        return record

    async def record_candidates(
        self,
        phase: str,
        candidates: list[dict[str, Any]],
        trace_id: str | None = None,
    ) -> None:
        """Record candidate generation results.

        Args:
            phase: Phase name
            candidates: List of candidate results with provider info
            trace_id: Logfire trace ID
        """
        await self.record_event(
            event_type="candidates_generated",
            phase=phase,
            trace_id=trace_id,
            metadata={"candidates": candidates},
        )

        # Save candidate files to disk
        if self.base_dir:
            candidates_dir = self.base_dir / "candidates" / phase
            candidates_dir.mkdir(parents=True, exist_ok=True)

            for candidate in candidates:
                provider = candidate.get("provider", "unknown")
                provider_dir = candidates_dir / provider
                provider_dir.mkdir(parents=True, exist_ok=True)

                # Save response
                response_file = provider_dir / "response.json"
                response_file.write_text(safe_json_dumps(candidate.get("response", {}), indent=2))

                # Save metadata
                metadata_file = provider_dir / "metadata.json"
                metadata_file.write_text(
                    safe_json_dumps(
                        {
                            "provider": provider,
                            "model": candidate.get("model"),
                            "started_at": candidate.get("started_at"),
                            "completed_at": candidate.get("completed_at"),
                            "duration_ms": candidate.get("duration_ms"),
                            "tokens": candidate.get("tokens", {}),
                            "trace_id": candidate.get("trace_id"),
                            "trace_url": self._get_trace_url(candidate.get("trace_id")),
                            "success": candidate.get("success", True),
                            "error": candidate.get("error"),
                        },
                        indent=2,
                    )
                )

    async def record_judge_decision(
        self,
        phase: str,
        judge_result: dict[str, Any],
        trace_id: str | None = None,
    ) -> None:
        """Record a judge decision.

        Args:
            phase: Phase name
            judge_result: Judge decision with winner, score, rationale
            trace_id: Logfire trace ID
        """
        checkpoint_id = f"cp_{self._sequence + 1:03d}_{phase}_judged"

        await self.record_event(
            event_type="judge_decision",
            phase=phase,
            checkpoint_id=checkpoint_id,
            trace_id=trace_id,
            metadata={
                "judge": {
                    "model": judge_result.get("model"),
                    "winner": judge_result.get("winner"),
                    "score": judge_result.get("score"),
                    "rationale": judge_result.get("rationale"),
                }
            },
        )

    async def complete_sprint(
        self,
        status: str = "completed",
        trace_id: str | None = None,
    ) -> None:
        """Mark sprint as complete and save final artifacts.

        Args:
            status: Final status ("completed", "failed")
            trace_id: Logfire trace ID
        """
        self._status = status

        # Calculate total duration
        total_duration_ms = None
        if self._start_time:
            total_duration_ms = int((datetime.now(timezone.utc) - self._start_time).total_seconds() * 1000)

        # Record completion event
        await self.record_event(
            event_type="sprint_completed",
            state=status,
            checkpoint_id=f"cp_{self._sequence + 1:03d}_sprint_complete",
            trace_id=trace_id,
            duration_ms=total_duration_ms,
            metadata={"final_status": status},
        )

        # Save all artifacts
        await self.save_timeline()
        await self._save_manifest()

        logger.info(f"Sprint {self.sprint_id} completed with status={status}")

    async def save_timeline(self) -> Path | None:
        """Persist timeline to disk.

        Returns:
            Path to the saved timeline file, or None if no artifacts dir
        """
        if not self.base_dir:
            return None

        total_duration_ms = None
        if self._start_time:
            total_duration_ms = int((datetime.now(timezone.utc) - self._start_time).total_seconds() * 1000)

        timeline_data = {
            "sprint_id": str(self.sprint_id),
            "total_duration_ms": total_duration_ms,
            "events": [e.to_dict() for e in self.timeline],
        }

        timeline_path = self.base_dir / "timeline.json"
        timeline_path.write_text(safe_json_dumps(timeline_data, indent=2))

        logger.debug(f"Saved timeline to {timeline_path}")
        return timeline_path

    async def get_timeline(self) -> dict[str, Any]:
        """Get the current timeline.

        Returns:
            Timeline data as dictionary
        """
        total_duration_ms = None
        if self._start_time:
            total_duration_ms = int((datetime.now(timezone.utc) - self._start_time).total_seconds() * 1000)

        return {
            "sprint_id": str(self.sprint_id),
            "total_duration_ms": total_duration_ms,
            "events": [e.to_dict() for e in self.timeline],
        }

    async def _save_manifest(self) -> None:
        """Save the sprint manifest."""
        if not self.base_dir:
            return

        manifest = {
            "version": self.VERSION,
            "sprint_id": str(self.sprint_id),
            "spec_id": str(self.spec_id) if self.spec_id else None,
            "created_at": self._start_time.isoformat() if self._start_time else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "status": self._status,
            "current_phase": self._current_phase,
            "current_checkpoint": f"cp_{self._sequence:03d}",
            "branch_id": None,
            "parent_branch": None,
            "logfire_project_url": "https://logfire-us.pydantic.dev/sortakool/guilde-lite",
            "paths": {
                "spec": "spec/spec.json",
                "timeline": "timeline.json",
                "code": "code/",
                "checkpoints": "checkpoints/",
            },
        }

        manifest_path = self.base_dir / "manifest.json"
        manifest_path.write_text(safe_json_dumps(manifest, indent=2))

    async def _save_phase_record(self, record: PhaseRecord) -> None:
        """Save a phase record to disk."""
        if not self.base_dir:
            return

        phases_dir = self.base_dir / "phases"
        phases_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{record.sequence:02d}_{record.phase}.json"
        phase_path = phases_dir / filename
        phase_path.write_text(safe_json_dumps(record.to_dict(), indent=2))

    async def create_checkpoint(
        self,
        label: str,
        state: dict[str, Any],
        can_branch: bool = True,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a checkpoint at current state.

        Args:
            label: Human-readable label for the checkpoint
            state: State snapshot to save
            can_branch: Whether branching from this checkpoint is allowed
            trace_id: Logfire trace ID

        Returns:
            Checkpoint data
        """
        checkpoint_id = f"cp_{self._sequence + 1:03d}_{label}"

        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "sequence": self._sequence + 1,
            "label": label,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sprint_state": {
                "status": self._status,
                "current_phase": self._current_phase,
                "phases_completed": [p for p, r in self.phases.items() if r.status == "completed"],
            },
            "state_snapshot": state,
            "can_branch": can_branch,
            "branch_options": [
                "change_judge_model",
                "change_candidate_models",
                "regenerate_phase",
                "skip_to_phase",
            ]
            if can_branch
            else [],
            "trace_id": trace_id,
            "trace_url": self._get_trace_url(trace_id),
        }

        # Save checkpoint to disk
        if self.base_dir:
            checkpoints_dir = self.base_dir / "checkpoints"
            checkpoints_dir.mkdir(parents=True, exist_ok=True)

            checkpoint_path = checkpoints_dir / f"{checkpoint_id}.json"
            checkpoint_path.write_text(safe_json_dumps(checkpoint, indent=2))

        logger.info(f"Created checkpoint: {checkpoint_id}")
        return checkpoint
