"""Tests for the SprintAgent."""

import pytest
from unittest.mock import patch, MagicMock
from app.agents.sprint_agent import SprintAgent
from app.agents.deps import Deps
from pydantic_ai import RunContext

@pytest.fixture
def sprint_agent():
    """Create a SprintAgent instance."""
    return SprintAgent()

def test_sprint_agent_initialization(sprint_agent):
    """Test that the SprintAgent initializes correctly."""
    assert sprint_agent.model_name is not None
    assert "Sprint" in sprint_agent.system_prompt
    assert sprint_agent.agent is not None

@pytest.mark.anyio
async def test_sprint_agent_has_tools(sprint_agent):
    """Test that the SprintAgent has the required tools."""
    # Accessing internal _function_toolset to verify tools
    tool_names = list(sprint_agent.agent._function_toolset.tools.keys())
    
    assert "fs_read_file" in tool_names
    assert "fs_write_file" in tool_names
    assert "fs_list_dir" in tool_names
    assert "run_tests" in tool_names

@pytest.mark.anyio
async def test_run_tests_tool(sprint_agent):
    """Test the run_tests tool."""
    # Get the tool function
    run_tests_tool = sprint_agent.agent._function_toolset.tools["run_tests"].function
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="collected 1 item\n. [100%]\n1 passed",
            stderr="",
            returncode=0
        )
        
        ctx = RunContext(
            deps=Deps(),
            model=sprint_agent.agent._model,
            usage=MagicMock(),
            prompt="test",
            metadata={},
            messages=[],
            tool_name="run_tests"
        )
        
        result = await run_tests_tool(ctx, path="tests/dummy")
        
        assert "Test Results (Exit Code: 0)" in result
        assert "1 passed" in result
        mock_run.assert_called_once()