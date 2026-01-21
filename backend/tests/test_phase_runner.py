"""Tests for the PhaseRunner."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from app.runners.phase_runner import PhaseRunner
from app.db.models.sprint import Sprint

@pytest.mark.anyio
async def test_phase_runner_start_success():
    """Test that PhaseRunner orchestrates phases correctly."""
    sprint_id = uuid4()
    mock_sprint = MagicMock(spec=Sprint)
    mock_sprint.id = sprint_id
    mock_sprint.name = "Test Sprint"
    mock_sprint.goal = "Build a hello world script"

    with patch("app.runners.phase_runner.get_db_context") as mock_db_ctx, \
         patch("app.runners.phase_runner.SprintService") as mock_sprint_service_cls, \
         patch("app.runners.phase_runner.AgentTddService") as mock_agent_tdd_service_cls, \
         patch("app.runners.phase_runner.manager") as mock_manager:
        
        # Mock DB context
        mock_db = AsyncMock()
        mock_db_ctx.return_value.__aenter__.return_value = mock_db
        
        # Mock SprintService
        mock_sprint_service = mock_sprint_service_cls.return_value
        mock_sprint_service.get_by_id = AsyncMock(return_value=mock_sprint)
        mock_sprint_service.update = AsyncMock()
        
        # Mock manager
        mock_manager.broadcast_to_room = AsyncMock()
        
        # Mock AgentTddService
        mock_agent_tdd_service = mock_agent_tdd_service_cls.return_value
        mock_agent_tdd_service.execute = AsyncMock()
        
        # Mock results for 3 phases
        mock_result_p1 = MagicMock()
        mock_result_p1.run.workspace_ref = "ws_123"
        
        mock_result_p2 = MagicMock()
        
        mock_result_p3 = MagicMock()
        mock_result_p3.decision.candidate_id = "c1"
        mock_candidate = MagicMock()
        mock_candidate.id = "c1"
        mock_candidate.output = "VERIFICATION_SUCCESS"
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
        args, kwargs = mock_agent_tdd_service.execute.call_args_list[0]
        assert args[0].metadata["agent_type"] == "sprint"
        
        mock_sprint_service.get_by_id.assert_called_once_with(sprint_id)
