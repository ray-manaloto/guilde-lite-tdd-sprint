
import os
import pytest
from app.agents.tools.agent_integration import run_claude_agent, run_codex_agent
from app.agents.deps import Deps
from pydantic_ai import RunContext
from unittest.mock import MagicMock

# Skip all tests in this module unless RUN_LIVE_TESTS is set
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS") != "1",
    reason="Skipping live integration tests. Set RUN_LIVE_TESTS=1 to run."
)

@pytest.fixture
def mock_run_context():
    """Create a mock RunContext for tool execution."""
    deps = Deps()
    return RunContext(
        deps=deps,
        retry=0,
        messages=[],
        tool_name="test_tool",
        model=MagicMock(),
        usage=MagicMock(),
    )

def test_live_claude_agent_echo(mock_run_context):
    """Test calling the actual Claude CLI with a simple print command."""
    prompt = "echo 'Live Test Successful'"
    # We use a trick: prompt injection to make claude print exactly what we want?
    # Actually, `claude -p` takes a prompt and sends it to the LLM. 
    # The LLM might not output exactly what we want unless instructed.
    # But wait, `run_claude_agent` executes `claude -p "<prompt>"`.
    # If we want to verify it works, we should ask it to repeat something unique.
    
    unique_str = f"live_test_{os.urandom(4).hex()}"
    prompt_text = f"Please just say exactly the string '{unique_str}' and nothing else."
    
    result = run_claude_agent(mock_run_context, prompt_text)
    
    print(f"Claude Output: {result}")
    assert unique_str in result, f"Expected '{unique_str}' in output, got: {result}"

def test_live_codex_agent_exec(mock_run_context):
    """Test calling the actual Codex CLI with an exec command."""
    # Codex agent runs `codex ... exec "<prompt>"`
    # The prompt for Codex is usually a command or instruction.
    # Since `exec` is used, we can directly pass a shell command if Codex allows?
    # Actually `codex exec` executes the *generated* code from the prompt? 
    # Let's check `run_codex_agent` implementation again.
    # cmd = ["codex", "--no-alt-screen", "-a", "never", "exec", prompt]
    # If prompt is "echo hello", Codex might generate python code? Or shell?
    # The tool is `run_codex_agent`. 
    
    # If `codex exec` takes a natural language prompt, generates code, run it.
    # We should ask it to print something using python, since Codex defaults to Python often?
    # Or implies it.
    
    unique_str = f"codex_test_{os.urandom(4).hex()}"
    prompt_text = f"print('{unique_str}')"
    
    result = run_codex_agent(mock_run_context, prompt_text)
    
    print(f"Codex Output: {result}")
    assert unique_str in result, f"Expected '{unique_str}' in output, got: {result}"
