"""Tests for WebSocket event types and ConnectionManager."""

import json

from app.core.websocket_events import (
    CandidateData,
    CandidateGeneratedEvent,
    CandidateStartedEvent,
    JudgeDecidedEvent,
    JudgeDecisionData,
    JudgeStartedEvent,
    PhaseCompletedEvent,
    PhaseFailedEvent,
    PhaseStartedEvent,
    SprintEventType,
    WorkflowStatusEvent,
)


class TestSprintEventTypes:
    """Test event type enums."""

    def test_event_types_are_strings(self):
        """Verify event types are string enums."""
        assert SprintEventType.CANDIDATE_GENERATED == "candidate.generated"
        assert SprintEventType.JUDGE_DECIDED == "judge.decided"
        assert SprintEventType.PHASE_STARTED == "phase.started"
        assert SprintEventType.PHASE_COMPLETED == "phase.completed"
        assert SprintEventType.WORKFLOW_STATUS == "workflow.status"

    def test_legacy_event_type_exists(self):
        """Verify legacy sprint_update type exists for backwards compatibility."""
        assert SprintEventType.SPRINT_UPDATE == "sprint_update"


class TestPhaseEvents:
    """Test phase event schemas."""

    def test_phase_started_event_creation(self):
        """Test PhaseStartedEvent factory method."""
        event = PhaseStartedEvent.create(
            sprint_id="abc-123",
            phase="discovery",
            attempt=1,
            details="Starting discovery phase",
        )

        assert event.event == SprintEventType.PHASE_STARTED
        assert event.sprint_id == "abc-123"
        assert event.data.phase == "discovery"
        assert event.data.attempt == 1
        assert event.data.details == "Starting discovery phase"
        assert event.timestamp is not None

    def test_phase_completed_event_creation(self):
        """Test PhaseCompletedEvent factory method."""
        event = PhaseCompletedEvent.create(
            sprint_id="abc-123",
            phase="coding",
            duration_ms=5000,
            output={"files_created": 3},
            details="Implementation complete",
        )

        assert event.event == SprintEventType.PHASE_COMPLETED
        assert event.data.phase == "coding"
        assert event.data.duration_ms == 5000
        assert event.data.output == {"files_created": 3}
        assert event.data.status == "completed"

    def test_phase_failed_event_creation(self):
        """Test PhaseFailedEvent factory method."""
        event = PhaseFailedEvent.create(
            sprint_id="abc-123",
            phase="verification",
            details="Tests failed",
            attempt=2,
        )

        assert event.event == SprintEventType.PHASE_FAILED
        assert event.data.phase == "verification"
        assert event.data.status == "failed"
        assert event.data.attempt == 2

    def test_phase_event_serialization(self):
        """Test that phase events serialize to JSON correctly."""
        event = PhaseStartedEvent.create(
            sprint_id="abc-123",
            phase="discovery",
        )

        json_str = event.model_dump_json()
        data = json.loads(json_str)

        assert data["event"] == "phase.started"
        assert data["sprint_id"] == "abc-123"
        assert "timestamp" in data
        assert data["sequence"] == 0
        assert data["data"]["phase"] == "discovery"


class TestCandidateEvents:
    """Test candidate event schemas."""

    def test_candidate_started_event(self):
        """Test CandidateStartedEvent factory method."""
        event = CandidateStartedEvent.create(
            sprint_id="abc-123",
            provider="openai",
            model_name="gpt-4o",
            phase="coding",
        )

        assert event.event == SprintEventType.CANDIDATE_STARTED
        assert event.data["provider"] == "openai"
        assert event.data["model_name"] == "gpt-4o"
        assert event.data["phase"] == "coding"

    def test_candidate_generated_event(self):
        """Test CandidateGeneratedEvent with CandidateData."""
        candidate = CandidateData(
            candidate_id="cand-1",
            provider="anthropic",
            model_name="claude-3-opus",
            agent_name="anthropic",
            output="Hello world implementation",
            duration_ms=2500,
            trace_id="trace-123",
            success=True,
        )

        event = CandidateGeneratedEvent.create(
            sprint_id="abc-123",
            candidate=candidate,
        )

        assert event.event == SprintEventType.CANDIDATE_GENERATED
        assert event.data.provider == "anthropic"
        assert event.data.model_name == "claude-3-opus"
        assert event.data.duration_ms == 2500
        assert event.data.success is True

    def test_candidate_data_with_failure(self):
        """Test CandidateData with error state."""
        candidate = CandidateData(
            provider="openai",
            model_name="gpt-4o",
            success=False,
            error="Rate limit exceeded",
        )

        assert candidate.success is False
        assert candidate.error == "Rate limit exceeded"


class TestJudgeEvents:
    """Test judge event schemas."""

    def test_judge_started_event(self):
        """Test JudgeStartedEvent factory method."""
        event = JudgeStartedEvent.create(
            sprint_id="abc-123",
            candidate_count=2,
            phase="discovery",
        )

        assert event.event == SprintEventType.JUDGE_STARTED
        assert event.data["candidate_count"] == 2
        assert event.data["phase"] == "discovery"

    def test_judge_decided_event(self):
        """Test JudgeDecidedEvent with JudgeDecisionData."""
        decision = JudgeDecisionData(
            winner_candidate_id="cand-2",
            winner_provider="anthropic",
            winner_model="claude-3-opus",
            score=0.92,
            rationale="Better code structure and documentation",
            model_name="gpt-4o",
            trace_id="judge-trace-456",
        )

        event = JudgeDecidedEvent.create(
            sprint_id="abc-123",
            decision=decision,
        )

        assert event.event == SprintEventType.JUDGE_DECIDED
        assert event.data.winner_candidate_id == "cand-2"
        assert event.data.score == 0.92
        assert event.data.rationale == "Better code structure and documentation"


class TestWorkflowEvents:
    """Test workflow event schemas."""

    def test_workflow_status_event(self):
        """Test WorkflowStatusEvent factory method."""
        event = WorkflowStatusEvent.create(
            sprint_id="abc-123",
            status="active",
            phase="coding",
            details="Implementation in progress",
            progress=0.5,
        )

        assert event.event == SprintEventType.WORKFLOW_STATUS
        assert event.data.status == "active"
        assert event.data.phase == "coding"
        assert event.data.details == "Implementation in progress"
        assert event.data.progress == 0.5

    def test_workflow_completed_status(self):
        """Test workflow completed status."""
        event = WorkflowStatusEvent.create(
            sprint_id="abc-123",
            status="completed",
            phase="verification",
            details="Sprint successfully completed",
        )

        assert event.data.status == "completed"

    def test_workflow_failed_status(self):
        """Test workflow failed status."""
        event = WorkflowStatusEvent.create(
            sprint_id="abc-123",
            status="failed",
            phase="error",
            details="Max retries exceeded",
        )

        assert event.data.status == "failed"


class TestEventSequencing:
    """Test event sequence numbering."""

    def test_events_have_sequence_field(self):
        """Test that all events have a sequence field."""
        event = PhaseStartedEvent.create(
            sprint_id="abc-123",
            phase="discovery",
        )

        assert hasattr(event, "sequence")
        assert event.sequence == 0  # Default

    def test_sequence_can_be_set(self):
        """Test that sequence can be set via factory."""
        event = PhaseStartedEvent.create(
            sprint_id="abc-123",
            phase="discovery",
            sequence=42,
        )

        assert event.sequence == 42


class TestEventSerialization:
    """Test event JSON serialization."""

    def test_all_events_serialize_to_json(self):
        """Test that all event types serialize correctly."""
        events = [
            PhaseStartedEvent.create(sprint_id="abc", phase="test"),
            PhaseCompletedEvent.create(sprint_id="abc", phase="test"),
            PhaseFailedEvent.create(sprint_id="abc", phase="test"),
            CandidateStartedEvent.create(sprint_id="abc", provider="openai"),
            CandidateGeneratedEvent.create(
                sprint_id="abc",
                candidate=CandidateData(provider="openai", model_name="gpt-4o"),
            ),
            JudgeStartedEvent.create(sprint_id="abc", candidate_count=2),
            JudgeDecidedEvent.create(
                sprint_id="abc",
                decision=JudgeDecisionData(winner_model="gpt-4o"),
            ),
            WorkflowStatusEvent.create(sprint_id="abc", status="active"),
        ]

        for event in events:
            json_str = event.model_dump_json()
            data = json.loads(json_str)

            # All events should have these fields
            assert "event" in data
            assert "sprint_id" in data
            assert "timestamp" in data
            assert "sequence" in data
            assert "data" in data

    def test_uuid_sprint_id_converts_to_string(self):
        """Test that UUID sprint_id is converted to string."""
        from uuid import uuid4

        sprint_uuid = uuid4()
        event = PhaseStartedEvent.create(
            sprint_id=sprint_uuid,
            phase="test",
        )

        assert event.sprint_id == str(sprint_uuid)
