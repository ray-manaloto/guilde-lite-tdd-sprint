"""Response formatter for storing agent responses as markdown.

Formats responses with YAML frontmatter containing metadata,
token usage, and tool calls for easy inspection and debugging.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.agents.orchestration.dispatcher import AgentResponse


class ResponseFormatter:
    """Formats and stores agent responses as markdown files.

    Each response is saved as a markdown file with YAML frontmatter
    containing metadata, making it easy to review agent outputs
    and track execution history.

    Example:
        >>> formatter = ResponseFormatter(output_dir=Path("./responses"))
        >>> path = await formatter.save_response(
        ...     response=agent_response,
        ...     workflow_id=workflow_id,
        ...     phase="planning"
        ... )
        >>> print(f"Saved to {path}")
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        include_prompt: bool = True,
        include_tool_calls: bool = True,
    ) -> None:
        """Initialize formatter.

        Args:
            output_dir: Directory for saving responses (None = format only)
            include_prompt: Include prompt in frontmatter
            include_tool_calls: Include tool calls in frontmatter
        """
        self.output_dir = output_dir
        self.include_prompt = include_prompt
        self.include_tool_calls = include_tool_calls

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)

    def format_response(
        self,
        response: AgentResponse,
        prompt: str | None = None,
        workflow_id: UUID | None = None,
        phase: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Format a response as markdown with YAML frontmatter.

        Args:
            response: Agent response to format
            prompt: Original prompt (optional)
            workflow_id: Workflow identifier (optional)
            phase: Workflow phase (optional)
            metadata: Additional metadata (optional)

        Returns:
            Formatted markdown string
        """
        # Build frontmatter
        fm_lines = ["---"]
        fm_lines.append(f"agent: {response.agent_name}")
        fm_lines.append(f"provider: {response.provider}")
        if response.model:
            fm_lines.append(f"model: {response.model}")
        fm_lines.append(f"success: {response.success}")
        fm_lines.append(f"timestamp: {response.timestamp.isoformat()}")
        fm_lines.append(f"latency_ms: {response.latency_ms:.2f}")

        if workflow_id:
            fm_lines.append(f"workflow_id: {workflow_id}")
        if phase:
            fm_lines.append(f"phase: {phase}")

        if response.token_usage:
            fm_lines.append("token_usage:")
            for key, value in response.token_usage.items():
                fm_lines.append(f"  {key}: {value}")

        if response.error:
            fm_lines.append(f"error: {self._escape_yaml(response.error)}")

        if self.include_prompt and prompt:
            # Truncate long prompts in frontmatter
            truncated = prompt[:500] + "..." if len(prompt) > 500 else prompt
            fm_lines.append(f"prompt: {self._escape_yaml(truncated)}")

        if self.include_tool_calls and response.tool_calls:
            fm_lines.append("tool_calls:")
            for call in response.tool_calls:
                fm_lines.append(f"  - name: {call.get('name', 'unknown')}")
                if "args" in call:
                    fm_lines.append(f"    args: {call['args']}")

        if metadata:
            fm_lines.append("metadata:")
            for key, value in metadata.items():
                fm_lines.append(f"  {key}: {value}")

        fm_lines.append("---")
        fm_lines.append("")

        # Add content
        if response.success:
            fm_lines.append(response.content)
        else:
            fm_lines.append(f"**Error:** {response.error}")
            if response.content:
                fm_lines.append("")
                fm_lines.append("**Partial output:**")
                fm_lines.append("")
                fm_lines.append(response.content)

        return "\n".join(fm_lines)

    async def save_response(
        self,
        response: AgentResponse,
        prompt: str | None = None,
        workflow_id: UUID | None = None,
        phase: str | None = None,
        metadata: dict[str, Any] | None = None,
        filename: str | None = None,
    ) -> Path | None:
        """Save a formatted response to a file.

        Args:
            response: Agent response to save
            prompt: Original prompt
            workflow_id: Workflow identifier
            phase: Workflow phase
            metadata: Additional metadata
            filename: Custom filename (auto-generated if None)

        Returns:
            Path to saved file, or None if no output_dir configured
        """
        if not self.output_dir:
            return None

        content = self.format_response(
            response=response,
            prompt=prompt,
            workflow_id=workflow_id,
            phase=phase,
            metadata=metadata,
        )

        # Generate filename
        if filename is None:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid4())[:8]
            safe_agent = response.agent_name.replace("/", "-").replace("\\", "-")
            filename = f"{timestamp}_{safe_agent}_{unique_id}.md"

        # Organize by workflow if provided
        if workflow_id:
            subdir = self.output_dir / str(workflow_id)
            subdir.mkdir(parents=True, exist_ok=True)
            file_path = subdir / filename
        else:
            file_path = self.output_dir / filename

        file_path.write_text(content, encoding="utf-8")
        return file_path

    async def save_batch(
        self,
        responses: list[AgentResponse],
        prompt: str | None = None,
        workflow_id: UUID | None = None,
        phase: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[Path]:
        """Save multiple responses.

        Args:
            responses: List of agent responses
            prompt: Shared prompt
            workflow_id: Workflow identifier
            phase: Workflow phase
            metadata: Shared metadata

        Returns:
            List of paths to saved files
        """
        paths: list[Path] = []
        for response in responses:
            path = await self.save_response(
                response=response,
                prompt=prompt,
                workflow_id=workflow_id,
                phase=phase,
                metadata=metadata,
            )
            if path:
                paths.append(path)
        return paths

    def format_comparison(
        self,
        responses: list[AgentResponse],
        prompt: str | None = None,
        workflow_id: UUID | None = None,
        phase: str | None = None,
    ) -> str:
        """Format multiple responses for side-by-side comparison.

        Args:
            responses: List of responses to compare
            prompt: Shared prompt
            workflow_id: Workflow identifier
            phase: Workflow phase

        Returns:
            Formatted markdown with all responses
        """
        lines = ["---"]
        lines.append("comparison: true")
        lines.append(f"agent_count: {len(responses)}")
        if workflow_id:
            lines.append(f"workflow_id: {workflow_id}")
        if phase:
            lines.append(f"phase: {phase}")
        lines.append(f"timestamp: {datetime.now(UTC).isoformat()}")
        lines.append("---")
        lines.append("")

        if prompt:
            lines.append("## Prompt")
            lines.append("")
            lines.append(prompt)
            lines.append("")

        lines.append("## Responses")
        lines.append("")

        for i, response in enumerate(responses, 1):
            lines.append(f"### {i}. {response.agent_name}")
            lines.append("")
            lines.append(f"**Provider:** {response.provider}")
            if response.model:
                lines.append(f"**Model:** {response.model}")
            lines.append(f"**Latency:** {response.latency_ms:.2f}ms")
            if response.token_usage:
                tokens = ", ".join(
                    f"{k}: {v}" for k, v in response.token_usage.items()
                )
                lines.append(f"**Tokens:** {tokens}")
            lines.append("")

            if response.success:
                lines.append(response.content)
            else:
                lines.append(f"**Error:** {response.error}")

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _escape_yaml(self, value: str) -> str:
        """Escape a string for YAML frontmatter."""
        # Handle multiline strings
        if "\n" in value:
            return f"|\\n{value}"
        # Quote strings with special characters
        if any(c in value for c in ":#{}[]|>"):
            return f'"{value.replace('"', '\\"')}"'
        return value
