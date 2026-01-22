"""Agent registry for managing multiple AI agent configurations.

Supports three agent integration types:
- SDK: Direct SDK integration (OpenAI, Anthropic, pydantic-ai)
- CLI: External CLI tools (Claude Code, Codex CLI)
- HTTP: HTTP API endpoints
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentType(Enum):
    """Type of agent integration."""

    SDK = "sdk"  # Direct SDK integration (OpenAI, Anthropic)
    CLI = "cli"  # External CLI tool (Claude Code, Codex)
    HTTP = "http"  # HTTP API endpoint


@dataclass
class AgentConfig:
    """Configuration for an AI agent.

    Attributes:
        name: Unique identifier for the agent
        agent_type: Integration type (SDK, CLI, HTTP)
        provider: Provider name (openai, anthropic, openrouter, claude-cli, codex-cli)
        model: Model identifier (e.g., gpt-4o, claude-sonnet-4-20250514)
        timeout_seconds: Maximum execution time
        enabled: Whether agent is active
        cli_command: Command template for CLI agents
        http_endpoint: URL for HTTP agents
        sdk_client_factory: Factory function returning SDK client
        track_tokens: Enable token usage tracking
        track_tools: Enable tool call tracking
        metadata: Additional agent-specific configuration
    """

    name: str
    agent_type: AgentType
    provider: str
    model: str | None = None
    timeout_seconds: int = 120
    enabled: bool = True
    cli_command: list[str] | None = None
    http_endpoint: str | None = None
    sdk_client_factory: Callable[[], Any] | None = None
    track_tokens: bool = True
    track_tools: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration based on agent type."""
        if self.agent_type == AgentType.CLI and not self.cli_command:
            raise ValueError(f"CLI agent '{self.name}' requires cli_command")
        if self.agent_type == AgentType.HTTP and not self.http_endpoint:
            raise ValueError(f"HTTP agent '{self.name}' requires http_endpoint")
        if self.agent_type == AgentType.SDK and not self.sdk_client_factory:
            raise ValueError(f"SDK agent '{self.name}' requires sdk_client_factory")


class AgentRegistry:
    """Central registry for managing agent configurations.

    Uses class-level storage for singleton-like behavior without
    requiring explicit instantiation.

    Example:
        >>> AgentRegistry.register(AgentConfig(
        ...     name="openai-gpt4",
        ...     agent_type=AgentType.SDK,
        ...     provider="openai",
        ...     model="gpt-4o",
        ...     sdk_client_factory=lambda: OpenAIClient()
        ... ))
        >>> agents = AgentRegistry.get_enabled_agents()
    """

    _agents: dict[str, AgentConfig] = {}

    @classmethod
    def register(cls, config: AgentConfig) -> None:
        """Register an agent configuration.

        Args:
            config: Agent configuration to register

        Raises:
            ValueError: If agent with same name already registered
        """
        if config.name in cls._agents:
            raise ValueError(f"Agent '{config.name}' already registered")
        cls._agents[config.name] = config

    @classmethod
    def unregister(cls, name: str) -> bool:
        """Remove an agent from the registry.

        Args:
            name: Name of agent to remove

        Returns:
            True if agent was removed, False if not found
        """
        if name in cls._agents:
            del cls._agents[name]
            return True
        return False

    @classmethod
    def get(cls, name: str) -> AgentConfig | None:
        """Get agent configuration by name.

        Args:
            name: Agent name

        Returns:
            Agent configuration or None if not found
        """
        return cls._agents.get(name)

    @classmethod
    def get_enabled_agents(cls) -> list[AgentConfig]:
        """Get all enabled agent configurations.

        Returns:
            List of enabled agent configurations
        """
        return [agent for agent in cls._agents.values() if agent.enabled]

    @classmethod
    def get_by_provider(cls, provider: str) -> list[AgentConfig]:
        """Get agents by provider name.

        Args:
            provider: Provider name to filter by

        Returns:
            List of agent configurations for the provider
        """
        return [
            agent
            for agent in cls._agents.values()
            if agent.provider == provider and agent.enabled
        ]

    @classmethod
    def get_by_type(cls, agent_type: AgentType) -> list[AgentConfig]:
        """Get agents by integration type.

        Args:
            agent_type: Agent type to filter by

        Returns:
            List of agent configurations of the specified type
        """
        return [
            agent
            for agent in cls._agents.values()
            if agent.agent_type == agent_type and agent.enabled
        ]

    @classmethod
    def list_all(cls) -> list[AgentConfig]:
        """Get all registered agent configurations.

        Returns:
            List of all agent configurations
        """
        return list(cls._agents.values())

    @classmethod
    def clear(cls) -> None:
        """Remove all registered agents. Useful for testing."""
        cls._agents.clear()

    @classmethod
    def count(cls) -> int:
        """Get total number of registered agents.

        Returns:
            Number of registered agents
        """
        return len(cls._agents)
