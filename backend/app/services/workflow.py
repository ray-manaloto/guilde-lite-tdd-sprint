"""Workflow service for reading sprint execution artifacts."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.schemas.workflow import (
    ArtifactInfo,
    ArtifactsListResponse,
    CandidateSummary,
    JudgeDecisionResponse,
    PhaseResponse,
    PhaseStatus,
    TimelineEventResponse,
    TimelineResponse,
    TokenCost,
    TokenUsage,
    WorkflowResponse,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for reading workflow artifacts from disk.

    Reads timeline, phases, candidates, and other artifacts saved by WorkflowTracker.
    """

    def __init__(self, artifacts_dir: Path | None = None):
        """Initialize the workflow service.

        Args:
            artifacts_dir: Base directory for artifacts (defaults to settings)
        """
        self.artifacts_dir = artifacts_dir or settings.AUTOCODE_ARTIFACTS_DIR

    def _get_sprint_dir(self, sprint_id: UUID) -> Path:
        """Get the directory path for a sprint.

        Args:
            sprint_id: The sprint UUID

        Returns:
            Path to the sprint directory

        Raises:
            NotFoundError: If artifacts directory not configured or sprint not found
        """
        if not self.artifacts_dir:
            raise NotFoundError(
                message="Artifacts directory not configured",
                details={"sprint_id": str(sprint_id)},
            )

        sprint_dir = self.artifacts_dir / str(sprint_id)
        if not sprint_dir.exists():
            raise NotFoundError(
                message="Sprint artifacts not found",
                details={"sprint_id": str(sprint_id), "path": str(sprint_dir)},
            )

        return sprint_dir

    def _load_json(self, path: Path) -> dict[str, Any] | None:
        """Load JSON file if it exists.

        Args:
            path: Path to JSON file

        Returns:
            Parsed JSON data or None if file doesn't exist
        """
        if not path.exists():
            return None

        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load {path}: {e}")
            return None

    def _parse_datetime(self, value: str | None) -> datetime | None:
        """Parse ISO datetime string.

        Args:
            value: ISO datetime string or None

        Returns:
            Parsed datetime or None
        """
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    def _parse_timeline_event(self, event_data: dict[str, Any]) -> TimelineEventResponse:
        """Parse a timeline event from JSON data.

        Args:
            event_data: Raw event data

        Returns:
            TimelineEventResponse object
        """
        return TimelineEventResponse(
            sequence=event_data.get("sequence", 0),
            event_type=event_data.get("event_type", "unknown"),
            timestamp=self._parse_datetime(event_data.get("timestamp")) or datetime.now(UTC),
            state=event_data.get("state"),
            phase=event_data.get("phase"),
            checkpoint_id=event_data.get("checkpoint_id"),
            trace_id=event_data.get("trace_id"),
            trace_url=event_data.get("trace_url"),
            duration_ms=event_data.get("duration_ms"),
            metadata=event_data.get("metadata", {}),
        )

    def _parse_candidate(self, candidate_data: dict[str, Any]) -> CandidateSummary:
        """Parse a candidate from JSON data.

        Args:
            candidate_data: Raw candidate data

        Returns:
            CandidateSummary object
        """
        tokens_data = candidate_data.get("tokens", {})
        tokens = TokenUsage(
            input_tokens=tokens_data.get("input_tokens", 0),
            output_tokens=tokens_data.get("output_tokens", 0),
            total_tokens=tokens_data.get("total_tokens", 0),
        )

        return CandidateSummary(
            provider=candidate_data.get("provider", "unknown"),
            model=candidate_data.get("model"),
            started_at=self._parse_datetime(candidate_data.get("started_at")),
            completed_at=self._parse_datetime(candidate_data.get("completed_at")),
            duration_ms=candidate_data.get("duration_ms"),
            tokens=tokens,
            success=candidate_data.get("success", True),
            error=candidate_data.get("error"),
            trace_id=candidate_data.get("trace_id"),
            trace_url=candidate_data.get("trace_url"),
        )

    def _parse_judge_result(
        self, judge_data: dict[str, Any] | None
    ) -> JudgeDecisionResponse | None:
        """Parse a judge result from JSON data.

        Args:
            judge_data: Raw judge data

        Returns:
            JudgeDecisionResponse object or None
        """
        if not judge_data:
            return None

        return JudgeDecisionResponse(
            model=judge_data.get("model"),
            winner=judge_data.get("winner"),
            score=judge_data.get("score"),
            rationale=judge_data.get("rationale"),
            trace_id=judge_data.get("trace_id"),
            trace_url=judge_data.get("trace_url"),
        )

    def _parse_phase(self, phase_data: dict[str, Any]) -> PhaseResponse:
        """Parse a phase record from JSON data.

        Args:
            phase_data: Raw phase data

        Returns:
            PhaseResponse object
        """
        # Parse candidates list
        candidates_raw = phase_data.get("candidates", {})
        candidates = []
        if isinstance(candidates_raw, dict):
            for provider, candidate in candidates_raw.items():
                if isinstance(candidate, dict):
                    candidate["provider"] = provider
                    candidates.append(self._parse_candidate(candidate))
        elif isinstance(candidates_raw, list):
            candidates = [self._parse_candidate(c) for c in candidates_raw]

        # Parse status
        status_str = phase_data.get("status", "pending")
        try:
            status = PhaseStatus(status_str)
        except ValueError:
            status = PhaseStatus.PENDING

        return PhaseResponse(
            phase=phase_data.get("phase", "unknown"),
            sequence=phase_data.get("sequence", 0),
            status=status,
            start_time=self._parse_datetime(phase_data.get("start_time")),
            end_time=self._parse_datetime(phase_data.get("end_time")),
            duration_ms=phase_data.get("duration_ms"),
            checkpoint_before=phase_data.get("checkpoint_before"),
            checkpoint_after=phase_data.get("checkpoint_after"),
            llm_config=phase_data.get("model_config", {}),
            input_data=phase_data.get("input", {}),
            output_data=phase_data.get("output", {}),
            candidates=candidates,
            judge_result=self._parse_judge_result(phase_data.get("judge_result")),
            trace_id=phase_data.get("trace_id"),
            trace_url=phase_data.get("trace_url"),
        )

    def _load_phases(self, sprint_dir: Path) -> list[PhaseResponse]:
        """Load all phase records from disk.

        Args:
            sprint_dir: Sprint directory path

        Returns:
            List of PhaseResponse objects
        """
        phases_dir = sprint_dir / "phases"
        if not phases_dir.exists():
            return []

        phases = []
        for phase_file in sorted(phases_dir.glob("*.json")):
            phase_data = self._load_json(phase_file)
            if phase_data:
                phases.append(self._parse_phase(phase_data))

        return phases

    def _aggregate_metrics(self, phases: list[PhaseResponse]) -> tuple[TokenUsage, TokenCost]:
        """Aggregate token usage and cost across all phases.

        Args:
            phases: List of phase responses

        Returns:
            Tuple of (TokenUsage, TokenCost)
        """
        total_input = 0
        total_output = 0
        total_tokens = 0

        for phase in phases:
            for candidate in phase.candidates:
                total_input += candidate.tokens.input_tokens
                total_output += candidate.tokens.output_tokens
                total_tokens += candidate.tokens.total_tokens

        tokens = TokenUsage(
            input_tokens=total_input,
            output_tokens=total_output,
            total_tokens=total_tokens,
        )

        # Rough cost estimation (configurable per model in future)
        # Using approximate GPT-4o pricing as default
        input_cost = total_input * 0.0025 / 1000
        output_cost = total_output * 0.01 / 1000
        cost = TokenCost(
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=input_cost + output_cost,
        )

        return tokens, cost

    async def get_workflow(self, sprint_id: UUID) -> WorkflowResponse:
        """Get full workflow state for a sprint.

        Args:
            sprint_id: Sprint UUID

        Returns:
            WorkflowResponse with full state

        Raises:
            NotFoundError: If sprint artifacts not found
        """
        sprint_dir = self._get_sprint_dir(sprint_id)

        # Load manifest
        manifest = self._load_json(sprint_dir / "manifest.json") or {}

        # Load timeline
        timeline_data = self._load_json(sprint_dir / "timeline.json") or {}
        events = [self._parse_timeline_event(e) for e in timeline_data.get("events", [])]

        # Load phases
        phases = self._load_phases(sprint_dir)

        # Aggregate metrics
        tokens, cost = self._aggregate_metrics(phases)

        # Parse status
        status_str = manifest.get("status", "planned")
        try:
            status = WorkflowStatus(status_str)
        except ValueError:
            status = WorkflowStatus.PLANNED

        return WorkflowResponse(
            sprint_id=sprint_id,
            spec_id=UUID(manifest["spec_id"]) if manifest.get("spec_id") else None,
            status=status,
            current_phase=manifest.get("current_phase"),
            current_checkpoint=manifest.get("current_checkpoint"),
            created_at=self._parse_datetime(manifest.get("created_at")),
            updated_at=self._parse_datetime(manifest.get("updated_at")),
            total_duration_ms=timeline_data.get("total_duration_ms"),
            phases=phases,
            timeline=events,
            aggregated_tokens=tokens,
            aggregated_cost=cost,
            logfire_project_url=manifest.get("logfire_project_url"),
        )

    async def get_timeline(self, sprint_id: UUID) -> TimelineResponse:
        """Get timeline events for a sprint.

        Args:
            sprint_id: Sprint UUID

        Returns:
            TimelineResponse with events

        Raises:
            NotFoundError: If sprint artifacts not found
        """
        sprint_dir = self._get_sprint_dir(sprint_id)

        timeline_data = self._load_json(sprint_dir / "timeline.json") or {}
        events = [self._parse_timeline_event(e) for e in timeline_data.get("events", [])]

        return TimelineResponse(
            sprint_id=sprint_id,
            total_duration_ms=timeline_data.get("total_duration_ms"),
            events=events,
        )

    async def list_artifacts(self, sprint_id: UUID) -> ArtifactsListResponse:
        """List all artifacts for a sprint.

        Args:
            sprint_id: Sprint UUID

        Returns:
            ArtifactsListResponse with artifact info

        Raises:
            NotFoundError: If sprint artifacts not found
        """
        sprint_dir = self._get_sprint_dir(sprint_id)
        artifacts = []

        # Walk the directory tree
        for path in sprint_dir.rglob("*"):
            if path.is_file():
                relative_path = path.relative_to(sprint_dir)

                # Determine type from extension
                suffix = path.suffix.lower()
                file_type = {
                    ".json": "json",
                    ".md": "markdown",
                    ".py": "python",
                    ".ts": "typescript",
                    ".tsx": "typescript",
                    ".js": "javascript",
                    ".jsx": "javascript",
                    ".txt": "text",
                }.get(suffix, "unknown")

                # Get file stats
                try:
                    stat = path.stat()
                    size_bytes = stat.st_size
                    created_at = datetime.fromtimestamp(stat.st_ctime, tz=UTC)
                except OSError:
                    size_bytes = None
                    created_at = None

                artifacts.append(
                    ArtifactInfo(
                        name=path.name,
                        path=str(relative_path),
                        type=file_type,
                        size_bytes=size_bytes,
                        created_at=created_at,
                    )
                )

        # Sort by path
        artifacts.sort(key=lambda a: a.path)

        return ArtifactsListResponse(
            sprint_id=sprint_id,
            base_path=str(sprint_dir),
            artifacts=artifacts,
        )
