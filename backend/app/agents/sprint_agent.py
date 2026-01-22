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
        async def run_tests(ctx: RunContext[Deps], path: str | None = None) -> str:
            """Run tests in the workspace and return the output.

            Args:
                path: Optional path to the test file. If not provided, it will look for tests
                      in the current session directory.
            """
            try:
                backend_dir = Path(settings.BACKEND_DIR or ".")

                # If no path provided, try to find tests in the session directory
                if path is None:
                    if ctx.deps.session_dir:
                        path = str(ctx.deps.session_dir)
                    else:
                        return "Error: No path provided and no session directory found."

                # Safety: Ensure we don't accidentally run the entire project's test suite
                # which might include recursive E2E tests.
                cmd = [
                    "uv",
                    "run",
                    "pytest",
                    path,
                    "-c",
                    "/dev/null",
                ]  # Use empty config to avoid picking up root conftest if needed

                # If path is just "tests", we should probably block it to be safe
                # or ensure it's restricted.
                if path == "tests":
                    return "Error: Running all tests in 'tests/' is disabled for safety. Please specify a file or subdirectory."

                result = subprocess.run(
                    cmd, cwd=backend_dir, capture_output=True, text=True, timeout=60
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
            from app.agents.tools.filesystem import list_dir, read_file, write_file

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
