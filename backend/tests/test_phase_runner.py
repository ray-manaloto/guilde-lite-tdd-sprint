"""Tests for the PhaseRunner."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.db.models.sprint import Sprint
from app.runners.phase_runner import PhaseRunner


@pytest.mark.anyio
async def test_phase_runner_start_success():
    """Test that PhaseRunner orchestrates phases correctly."""
    sprint_id = uuid4()
    spec_id = uuid4()
    mock_sprint = MagicMock(spec=Sprint)
    mock_sprint.id = sprint_id
    mock_sprint.name = "Test Sprint"
    mock_sprint.goal = "Build a hello world script"
    mock_sprint.spec_id = spec_id

    with patch("app.runners.phase_runner.get_db_context") as mock_db_ctx, \
         patch("app.runners.phase_runner.SprintService") as mock_sprint_service_cls, \
         patch("app.runners.phase_runner.AgentTddService") as mock_agent_tdd_service_cls, \
         patch("app.runners.phase_runner.SpecService") as mock_spec_service_cls, \
         patch("app.runners.phase_runner.WorkflowTracker") as mock_tracker_cls, \
         patch("app.runners.phase_runner.settings") as mock_settings, \
         patch("app.runners.phase_runner.manager") as mock_manager:

        # Mock DB context
        mock_db = AsyncMock()
        mock_db_ctx.return_value.__aenter__.return_value = mock_db

        # Mock settings
        mock_settings.AUTOCODE_ARTIFACTS_DIR = None  # Disable file system operations
        mock_settings.model_for_provider = MagicMock(return_value="test-model")

        # Mock SprintService
        mock_sprint_service = mock_sprint_service_cls.return_value
        mock_sprint_service.get_by_id = AsyncMock(return_value=mock_sprint)
        mock_sprint_service.update = AsyncMock()

        # Mock SpecService
        mock_spec_service = mock_spec_service_cls.return_value
        mock_spec_service.export_to_disk = AsyncMock(return_value=None)

        # Mock WorkflowTracker
        mock_tracker = mock_tracker_cls.return_value
        mock_tracker.base_dir = None
        mock_tracker.start_sprint = AsyncMock()
        mock_tracker.record_event = AsyncMock()
        mock_tracker.start_phase = AsyncMock()
        mock_tracker.end_phase = AsyncMock()
        mock_tracker.record_candidates = AsyncMock()
        mock_tracker.record_judge_decision = AsyncMock()
        mock_tracker.complete_sprint = AsyncMock()

        # Mock manager (including new methods)
        mock_manager.broadcast_to_room = AsyncMock()
        mock_manager.broadcast_legacy_status = AsyncMock()
        mock_manager.broadcast_event = AsyncMock()

        # Mock AgentTddService
        mock_agent_tdd_service = mock_agent_tdd_service_cls.return_value
        mock_agent_tdd_service.execute = AsyncMock()

        # Mock results for 3 phases
        mock_result_p1 = MagicMock()
        mock_result_p1.run.workspace_ref = "ws_123"
        mock_candidate_p1 = MagicMock()
        mock_candidate_p1.id = "c1_p1"
        mock_candidate_p1.provider = "openai"
        mock_candidate_p1.model_name = "gpt-4"
        mock_candidate_p1.agent_name = "openai"
        mock_candidate_p1.output = "Discovery Complete"
        mock_candidate_p1.metrics = {"trace_id": "trace123", "duration_ms": 1000, "status": "ok"}
        mock_result_p1.candidates = [mock_candidate_p1]
        mock_result_p1.decision = MagicMock()
        mock_result_p1.decision.candidate_id = "c1_p1"
        mock_result_p1.decision.model_name = "gpt-4"
        mock_result_p1.decision.score = 0.9
        mock_result_p1.decision.rationale = "Good response"
        mock_result_p1.decision.trace_id = "trace_judge_p1"

        mock_result_p2 = MagicMock()
        mock_candidate_p2 = MagicMock()
        mock_candidate_p2.id = "c1_p2"
        mock_candidate_p2.provider = "openai"
        mock_candidate_p2.model_name = "gpt-4"
        mock_candidate_p2.agent_name = "openai"
        mock_candidate_p2.output = "Coding Complete"
        mock_candidate_p2.metrics = {"trace_id": "trace456", "duration_ms": 2000, "status": "ok"}
        mock_result_p2.candidates = [mock_candidate_p2]

        mock_result_p3 = MagicMock()
        mock_result_p3.decision.candidate_id = "c1"
        mock_candidate = MagicMock()
        mock_candidate.id = "c1"
        mock_candidate.output = "VERIFICATION_SUCCESS"
        mock_candidate.provider = "openai"
        mock_candidate.model_name = "gpt-4"
        mock_candidate.agent_name = "openai"
        mock_candidate.metrics = {"trace_id": "trace789", "duration_ms": 1500, "status": "ok"}
        mock_result_p3.candidates = [mock_candidate]

        mock_agent_tdd_service.execute.side_effect = [
            mock_result_p1, # Phase 1
            mock_result_p2, # Phase 2 (Coding)
            mock_result_p3  # Phase 3 (Verification)
        ]

        # Run the runner
        await PhaseRunner.start(sprint_id)

        # Verify calls
        assert mock_agent_tdd_service.execute.call_count == 3
        # Check that agent_type="sprint" was passed
        args, _kwargs = mock_agent_tdd_service.execute.call_args_list[0]
        assert args[0].metadata["agent_type"] == "sprint"

        mock_sprint_service.get_by_id.assert_called_once_with(sprint_id)
