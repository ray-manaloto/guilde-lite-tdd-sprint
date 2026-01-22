"""Prompt dispatcher for parallel multi-agent execution.

Executes prompts across multiple agents concurrently and collects responses.
Supports SDK, CLI, and HTTP agent types with unified response handling.
"""

import asyncio
import subprocess
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from app.agents.orchestration.registry import AgentConfig, AgentRegistry, AgentType
from app.agents.orchestration.telemetry import TelemetryCollector, TelemetryEvent


@dataclass
class AgentResponse:
    """Response from a single agent execution.

    Attributes:
        agent_name: Name of the agent that produced the response
        provider: Provider name (openai, anthropic, etc.)
        model: Model used for generation
        content: Generated response content
        success: Whether execution completed successfully
        error: Error message if execution failed
        latency_ms: Execution time in milliseconds
        token_usage: Token counts (input, output, total)
        tool_calls: List of tool calls made during execution
        metadata: Additional response metadata
        timestamp: When response was generated
    """

    agent_name: str
    provider: str
    model: str | None = None
    content: str = ""
    success: bool = True
    error: str | None = None
    latency_ms: float = 0.0
    token_usage: dict[str, int] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class PromptDispatcher:
    """Dispatches prompts to multiple agents in parallel.

    Handles execution across SDK, CLI, and HTTP agent types with
    unified response collection and error handling.

    Example:
        >>> dispatcher = PromptDispatcher(telemetry=TelemetryCollector())
        >>> responses = await dispatcher.execute_parallel(
        ...     prompt="Explain async/await",
        ...     agent_names=["openai-gpt4", "anthropic-claude"]
        ... )
    """

    def __init__(
        self,
        telemetry: TelemetryCollector | None = None,
        default_timeout: int = 120,
    ) -> None:
        """Initialize dispatcher.

        Args:
            telemetry: Optional telemetry collector for tracking
            default_timeout: Default timeout in seconds for agent execution
        """
        self.telemetry = telemetry
        self.default_timeout = default_timeout

    async def execute_parallel(
        self,
        prompt: str,
        agent_names: list[str] | None = None,
        context: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> list[AgentResponse]:
        """Execute prompt across multiple agents in parallel.

        Args:
            prompt: The prompt to send to agents
            agent_names: Specific agents to use (None = all enabled)
            context: Additional context to pass to agents
            timeout: Override timeout for this execution

        Returns:
            List of responses from all agents
        """
        if agent_names:
            agents = [
                AgentRegistry.get(name)
                for name in agent_names
                if AgentRegistry.get(name)
            ]
        else:
            agents = AgentRegistry.get_enabled_agents()

        if not agents:
            return []

        tasks = [
            self._execute_single(
                agent=agent,
                prompt=prompt,
                context=context or {},
                timeout=timeout or agent.timeout_seconds or self.default_timeout,
            )
            for agent in agents
            if agent is not None
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error responses
        results: list[AgentResponse] = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                agent = agents[i]
                if agent:
                    results.append(
                        AgentResponse(
                            agent_name=agent.name,
                            provider=agent.provider,
                            model=agent.model,
                            success=False,
                            error=str(response),
                        )
                    )
            elif isinstance(response, AgentResponse):
                results.append(response)

        return results

    async def execute_single(
        self,
        agent_name: str,
        prompt: str,
        context: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> AgentResponse:
        """Execute prompt on a single agent.

        Args:
            agent_name: Name of agent to use
            prompt: The prompt to send
            context: Additional context
            timeout: Override timeout

        Returns:
            Response from the agent

        Raises:
            ValueError: If agent not found
        """
        agent = AgentRegistry.get(agent_name)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not found")

        return await self._execute_single(
            agent=agent,
            prompt=prompt,
            context=context or {},
            timeout=timeout or agent.timeout_seconds or self.default_timeout,
        )

    async def _execute_single(
        self,
        agent: AgentConfig,
        prompt: str,
        context: dict[str, Any],
        timeout: int,
    ) -> AgentResponse:
        """Internal method to execute on a single agent.

        Routes to appropriate handler based on agent type.
        """
        start_time = time.perf_counter()

        try:
            if agent.agent_type == AgentType.SDK:
                response = await self._execute_sdk(agent, prompt, context, timeout)
            elif agent.agent_type == AgentType.CLI:
                response = await self._execute_cli(agent, prompt, context, timeout)
            elif agent.agent_type == AgentType.HTTP:
                response = await self._execute_http(agent, prompt, context, timeout)
            else:
                raise ValueError(f"Unknown agent type: {agent.agent_type}")

            response.latency_ms = (time.perf_counter() - start_time) * 1000

            # Record telemetry
            if self.telemetry:
                await self._record_telemetry(response)

            return response

        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AgentResponse(
                agent_name=agent.name,
                provider=agent.provider,
                model=agent.model,
                success=False,
                error=f"Timeout after {timeout}s",
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AgentResponse(
                agent_name=agent.name,
                provider=agent.provider,
                model=agent.model,
                success=False,
                error=str(e),
                latency_ms=latency_ms,
            )

    async def _execute_sdk(
        self,
        agent: AgentConfig,
        prompt: str,
        context: dict[str, Any],
        timeout: int,
    ) -> AgentResponse:
        """Execute prompt using SDK client.

        The SDK client factory should return a pydantic-ai Agent or
        compatible client with an async run method.
        """
        if not agent.sdk_client_factory:
            raise ValueError(f"SDK agent '{agent.name}' missing client factory")

        client = agent.sdk_client_factory()

        # Support pydantic-ai Agent interface
        if hasattr(client, "run"):
            result = await asyncio.wait_for(
                client.run(prompt, deps=context.get("deps")),
                timeout=timeout,
            )
            return AgentResponse(
                agent_name=agent.name,
                provider=agent.provider,
                model=agent.model,
                content=str(result.output) if hasattr(result, "output") else str(result),
                success=True,
                token_usage=self._extract_token_usage(result),
                tool_calls=self._extract_tool_calls(result),
            )

        # Support generic async callable
        if callable(client):
            result = await asyncio.wait_for(
                client(prompt, **context),
                timeout=timeout,
            )
            return AgentResponse(
                agent_name=agent.name,
                provider=agent.provider,
                model=agent.model,
                content=str(result),
                success=True,
            )

        raise ValueError(f"SDK client for '{agent.name}' not callable")

    async def _execute_cli(
        self,
        agent: AgentConfig,
        prompt: str,
        context: dict[str, Any],
        timeout: int,
    ) -> AgentResponse:
        """Execute prompt using CLI tool.

        Runs the CLI command as a subprocess with prompt as stdin.
        """
        if not agent.cli_command:
            raise ValueError(f"CLI agent '{agent.name}' missing command")

        # Build command with any context substitutions
        cmd = [
            part.format(prompt=prompt, **context)
            for part in agent.cli_command
        ]

        # Run in thread to avoid blocking the event loop
        result = await asyncio.wait_for(
            asyncio.to_thread(
                subprocess.run,
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
            ),
            timeout=timeout + 5,  # Extra buffer for process overhead
        )

        if result.returncode != 0:
            return AgentResponse(
                agent_name=agent.name,
                provider=agent.provider,
                model=agent.model,
                success=False,
                error=result.stderr or f"Exit code: {result.returncode}",
            )

        return AgentResponse(
            agent_name=agent.name,
            provider=agent.provider,
            model=agent.model,
            content=result.stdout,
            success=True,
        )

    async def _execute_http(
        self,
        agent: AgentConfig,
        prompt: str,
        context: dict[str, Any],
        timeout: int,
    ) -> AgentResponse:
        """Execute prompt via HTTP API.

        Sends POST request with prompt and context as JSON body.
        """
        if not agent.http_endpoint:
            raise ValueError(f"HTTP agent '{agent.name}' missing endpoint")

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                agent.http_endpoint,
                json={
                    "prompt": prompt,
                    "model": agent.model,
                    **context,
                },
                headers=agent.metadata.get("headers", {}),
            )
            response.raise_for_status()
            data = response.json()

        return AgentResponse(
            agent_name=agent.name,
            provider=agent.provider,
            model=agent.model,
            content=data.get("content", data.get("response", str(data))),
            success=True,
            token_usage=data.get("usage", {}),
            metadata=data.get("metadata", {}),
        )

    def _extract_token_usage(self, result: Any) -> dict[str, int]:
        """Extract token usage from pydantic-ai result."""
        usage: dict[str, int] = {}
        if hasattr(result, "usage"):
            u = result.usage
            if hasattr(u, "input_tokens"):
                usage["input"] = u.input_tokens
            if hasattr(u, "output_tokens"):
                usage["output"] = u.output_tokens
            if hasattr(u, "total_tokens"):
                usage["total"] = u.total_tokens
        return usage

    def _extract_tool_calls(self, result: Any) -> list[dict[str, Any]]:
        """Extract tool calls from pydantic-ai result."""
        calls: list[dict[str, Any]] = []
        if hasattr(result, "tool_calls"):
            for call in result.tool_calls:
                calls.append({
                    "name": getattr(call, "name", "unknown"),
                    "args": getattr(call, "args", {}),
                })
        return calls

    async def _record_telemetry(self, response: AgentResponse) -> None:
        """Record response telemetry."""
        if not self.telemetry:
            return

        event = TelemetryEvent(
            event_type="agent_response",
            agent_name=response.agent_name,
            provider=response.provider,
            model=response.model,
            success=response.success,
            latency_ms=response.latency_ms,
            token_usage=response.token_usage,
            error=response.error,
        )
        await self.telemetry.record(event)
