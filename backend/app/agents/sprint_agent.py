# Sprint agent for automated development tasks.

import logging
import subprocess
from pathlib import Path
from pydantic_ai import Agent, RunContext

from app.agents.assistant import AssistantAgent
from app.agents.deps import Deps
from app.core.config import settings

logger = logging.getLogger(__name__)

SPRINT_SYSTEM_PROMPT = """
You are an expert software engineer AI agent responsible for executing development tasks within a "Sprint".
Your goal is to implement working, high-quality, and validated code.

Follow the Test-Driven Development (TDD) approach:
1. Understand the requirements.
2. Read existing code and tests.
3. Write/Modify tests to define the goal.
4. Implement the code to pass the tests.
5. Validate using the 'run_tests' tool.

You have access to the session workspace through filesystem tools.
Always ensure your code adheres to project standards and includes appropriate tests.
"""

class SprintAgent(AssistantAgent):
    """Specialized agent for sprint tasks."""

    def __init__(self, **kwargs):
        if "system_prompt" not in kwargs:
            kwargs["system_prompt"] = SPRINT_SYSTEM_PROMPT
        super().__init__(**kwargs)

    def _register_tools(self, agent: Agent[Deps, str]) -> None:
        """Register tools for the sprint agent."""
        # Register base tools from AssistantAgent
        super()._register_tools(agent)

        @agent.tool
        async def run_tests(ctx: RunContext[Deps], path: str = "tests") -> str:
            """Run tests in the workspace and return the output.
            
            Args:
                path: Path to the test file or directory.
            """
            try:
                # Use uv to run pytest in the backend directory
                # Note: In a real agentic flow, we'd need to be careful about environment paths
                backend_dir = Path(settings.BACKEND_DIR or ".")
                result = subprocess.run(
                    ["uv", "run", "pytest", path],
                    cwd=backend_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                output = result.stdout + result.stderr
                return f"Test Results (Exit Code: {result.returncode}):\n{output}"
            except subprocess.TimeoutExpired:
                return "Error: Test execution timed out."
            except Exception as e:
                return f"Error running tests: {e}"

        # Ensure filesystem tools are available even if disabled in base settings
        # for the specialized sprint agent
        if not settings.AGENT_FS_ENABLED:
            from app.agents.tools.filesystem import read_file, write_file, list_dir
            
            @agent.tool
            async def fs_read_file(ctx: RunContext[Deps], path: str) -> str:
                """Read a file from your session workspace."""
                return read_file(ctx, path)

            @agent.tool
            async def fs_write_file(ctx: RunContext[Deps], path: str, content: str) -> str:
                """Write a file to your session workspace."""
                return write_file(ctx, path, content)

            @agent.tool
            async def fs_list_dir(ctx: RunContext[Deps], path: str = ".") -> str:
                """List files in your session workspace."""
                return list_dir(ctx, path)
