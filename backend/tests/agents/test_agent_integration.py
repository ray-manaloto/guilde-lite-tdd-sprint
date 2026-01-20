
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai import RunContext

from app.agents.deps import Deps
from app.agents.tools.agent_integration import run_claude_agent, run_codex_agent


@pytest.fixture
def mock_run_context():
    """Create a mock RunContext with Deps."""
    deps = Deps()
    return RunContext(
        deps=deps,
        retry=0,
        messages=[],
        tool_name="test_tool",
        model=MagicMock(),
        usage=MagicMock(),
    )


@patch("app.agents.tools.agent_integration.subprocess.run")
def test_run_codex_agent_success(mock_subprocess_run, mock_run_context):
    """Test successful execution of Codex agent."""
    # Setup mock return value
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Python code generated successfully."
    mock_result.stderr = ""
    mock_subprocess_run.return_value = mock_result

    prompt = "Generate a fibonacci function"
    result = run_codex_agent(mock_run_context, prompt)

    # Verify result
    assert result == "Python code generated successfully."

    # Verify subprocess call
    mock_subprocess_run.assert_called_once()
    args, kwargs = mock_subprocess_run.call_args
    assert args[0] == ["codex", "--no-alt-screen", "-a", "never", "exec", prompt]
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["timeout"] == 120


@patch("app.agents.tools.agent_integration.subprocess.run")
def test_run_codex_agent_failure(mock_subprocess_run, mock_run_context):
    """Test handling of Codex agent failure (non-zero exit code)."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Error: Invalid argument"
    mock_subprocess_run.return_value = mock_result

    result = run_codex_agent(mock_run_context, "bad prompt")

    assert "Codex agent failed with code 1" in result
    assert "Error: Invalid argument" in result


@patch("app.agents.tools.agent_integration.subprocess.run")
def test_run_codex_agent_timeout(mock_subprocess_run, mock_run_context):
    """Test handling of Codex agent timeout."""
    mock_subprocess_run.side_effect = subprocess.TimeoutExpired(cmd="codex", timeout=120)

    result = run_codex_agent(mock_run_context, "slow prompt")

    assert "Error: Codex agent timed out after 120 seconds." in result


@patch("app.agents.tools.agent_integration.subprocess.run")
def test_run_claude_agent_success(mock_subprocess_run, mock_run_context):
    """Test successful execution of Claude agent."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Here is the summary."
    mock_result.stderr = ""
    mock_subprocess_run.return_value = mock_result

    prompt = "Summarize this file"
    result = run_claude_agent(mock_run_context, prompt)

    assert result == "Here is the summary."

    mock_subprocess_run.assert_called_once()
    args, kwargs = mock_subprocess_run.call_args
    assert args[0] == ["claude", "-p", prompt]
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["timeout"] == 120


@patch("app.agents.tools.agent_integration.subprocess.run")
def test_run_claude_agent_failure(mock_subprocess_run, mock_run_context):
    """Test handling of Claude agent failure."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Authentication failed"
    mock_subprocess_run.return_value = mock_result

    result = run_claude_agent(mock_run_context, "prompt")

    assert "Claude agent failed with code 1" in result
    assert "Authentication failed" in result
