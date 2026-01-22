"""Unit tests for the AgentRegistry module.

Tests cover:
- AgentConfig validation for SDK, CLI, and HTTP agent types
- AgentRegistry CRUD operations
- Filtering and querying agents
- Edge cases and error handling
"""

import pytest

from app.agents.orchestration.registry import AgentConfig, AgentRegistry, AgentType


@pytest.fixture(autouse=True)
def clear_registry() -> None:
    """Clear the registry before and after each test to prevent state leakage."""
    AgentRegistry.clear()
    yield
    AgentRegistry.clear()


# ============================================================================
# AgentConfig Validation Tests
# ============================================================================


class TestAgentConfigValidation:
    """Tests for AgentConfig dataclass validation."""

    def test_sdk_agent_requires_client_factory(self) -> None:
        """SDK agents must have a sdk_client_factory."""
        with pytest.raises(ValueError, match="requires sdk_client_factory"):
            AgentConfig(
                name="test-sdk",
                agent_type=AgentType.SDK,
                provider="openai",
                model="gpt-4o",
            )

    def test_sdk_agent_valid_with_client_factory(self) -> None:
        """SDK agents are valid when sdk_client_factory is provided."""
        config = AgentConfig(
            name="test-sdk",
            agent_type=AgentType.SDK,
            provider="openai",
            model="gpt-4o",
            sdk_client_factory=lambda: "mock_client",
        )
        assert config.name == "test-sdk"
        assert config.agent_type == AgentType.SDK

    def test_cli_agent_requires_cli_command(self) -> None:
        """CLI agents must have a cli_command."""
        with pytest.raises(ValueError, match="requires cli_command"):
            AgentConfig(
                name="test-cli",
                agent_type=AgentType.CLI,
                provider="ollama",
                model="llama3",
            )

    def test_cli_agent_valid_with_cli_command(self) -> None:
        """CLI agents are valid when cli_command is provided."""
        config = AgentConfig(
            name="test-cli",
            agent_type=AgentType.CLI,
            provider="ollama",
            model="llama3",
            cli_command=["ollama", "run", "llama3"],
        )
        assert config.name == "test-cli"
        assert config.agent_type == AgentType.CLI
        assert config.cli_command == ["ollama", "run", "llama3"]

    def test_http_agent_requires_http_endpoint(self) -> None:
        """HTTP agents must have an http_endpoint."""
        with pytest.raises(ValueError, match="requires http_endpoint"):
            AgentConfig(
                name="test-http",
                agent_type=AgentType.HTTP,
                provider="custom",
                model="custom-model",
            )

    def test_http_agent_valid_with_http_endpoint(self) -> None:
        """HTTP agents are valid when http_endpoint is provided."""
        config = AgentConfig(
            name="test-http",
            agent_type=AgentType.HTTP,
            provider="custom",
            model="custom-model",
            http_endpoint="http://localhost:8080/v1/chat",
        )
        assert config.name == "test-http"
        assert config.agent_type == AgentType.HTTP
        assert config.http_endpoint == "http://localhost:8080/v1/chat"

    def test_default_values(self) -> None:
        """AgentConfig has sensible default values."""
        config = AgentConfig(
            name="test-agent",
            agent_type=AgentType.SDK,
            provider="anthropic",
            sdk_client_factory=lambda: "mock",
        )
        assert config.model is None
        assert config.timeout_seconds == 120
        assert config.enabled is True
        assert config.track_tokens is True
        assert config.track_tools is True
        assert config.metadata == {}

    def test_custom_metadata(self) -> None:
        """AgentConfig can store custom metadata."""
        config = AgentConfig(
            name="test-agent",
            agent_type=AgentType.SDK,
            provider="openai",
            sdk_client_factory=lambda: "mock",
            metadata={"environment": "production", "version": "1.0"},
        )
        assert config.metadata["environment"] == "production"
        assert config.metadata["version"] == "1.0"


# ============================================================================
# AgentRegistry Registration Tests
# ============================================================================


class TestAgentRegistryRegistration:
    """Tests for AgentRegistry registration operations."""

    def test_register_agent(self) -> None:
        """Can register an agent configuration."""
        config = AgentConfig(
            name="gpt-4o",
            agent_type=AgentType.SDK,
            provider="openai",
            model="gpt-4o",
            sdk_client_factory=lambda: "mock",
        )
        AgentRegistry.register(config)
        assert AgentRegistry.count() == 1

    def test_register_multiple_agents(self) -> None:
        """Can register multiple agents."""
        configs = [
            AgentConfig(
                name="agent-1",
                agent_type=AgentType.SDK,
                provider="openai",
                sdk_client_factory=lambda: "mock",
            ),
            AgentConfig(
                name="agent-2",
                agent_type=AgentType.CLI,
                provider="ollama",
                cli_command=["ollama", "run"],
            ),
            AgentConfig(
                name="agent-3",
                agent_type=AgentType.HTTP,
                provider="custom",
                http_endpoint="http://localhost:8080",
            ),
        ]
        for config in configs:
            AgentRegistry.register(config)
        assert AgentRegistry.count() == 3

    def test_register_duplicate_raises_error(self) -> None:
        """Registering an agent with the same name raises ValueError."""
        config1 = AgentConfig(
            name="test-agent",
            agent_type=AgentType.SDK,
            provider="openai",
            model="gpt-4",
            sdk_client_factory=lambda: "mock1",
        )
        config2 = AgentConfig(
            name="test-agent",
            agent_type=AgentType.SDK,
            provider="openai",
            model="gpt-4o",
            sdk_client_factory=lambda: "mock2",
        )
        AgentRegistry.register(config1)

        with pytest.raises(ValueError, match="already registered"):
            AgentRegistry.register(config2)

        # Original agent remains unchanged
        assert AgentRegistry.count() == 1
        retrieved = AgentRegistry.get("test-agent")
        assert retrieved is not None
        assert retrieved.model == "gpt-4"


# ============================================================================
# AgentRegistry Retrieval Tests
# ============================================================================


class TestAgentRegistryRetrieval:
    """Tests for AgentRegistry retrieval operations."""

    def test_get_existing_agent(self) -> None:
        """Can retrieve a registered agent by name."""
        config = AgentConfig(
            name="my-agent",
            agent_type=AgentType.SDK,
            provider="anthropic",
            model="claude-3-opus",
            sdk_client_factory=lambda: "mock",
        )
        AgentRegistry.register(config)

        retrieved = AgentRegistry.get("my-agent")
        assert retrieved is not None
        assert retrieved.name == "my-agent"
        assert retrieved.provider == "anthropic"
        assert retrieved.model == "claude-3-opus"

    def test_get_nonexistent_agent_returns_none(self) -> None:
        """Getting a non-existent agent returns None."""
        result = AgentRegistry.get("nonexistent")
        assert result is None

    def test_list_all_agents(self) -> None:
        """Can list all registered agents."""
        configs = [
            AgentConfig(
                name=f"agent-{i}",
                agent_type=AgentType.SDK,
                provider="openai",
                sdk_client_factory=lambda: "mock",
            )
            for i in range(3)
        ]
        for config in configs:
            AgentRegistry.register(config)

        all_agents = AgentRegistry.list_all()
        assert len(all_agents) == 3
        names = {a.name for a in all_agents}
        assert names == {"agent-0", "agent-1", "agent-2"}

    def test_list_all_empty_registry(self) -> None:
        """Listing agents on empty registry returns empty list."""
        assert AgentRegistry.list_all() == []


# ============================================================================
# AgentRegistry Filtering Tests
# ============================================================================


class TestAgentRegistryFiltering:
    """Tests for AgentRegistry filtering operations."""

    @pytest.fixture
    def populated_registry(self) -> None:
        """Populate registry with diverse agents for filtering tests."""
        configs = [
            AgentConfig(
                name="openai-gpt4",
                agent_type=AgentType.SDK,
                provider="openai",
                model="gpt-4o",
                enabled=True,
                sdk_client_factory=lambda: "mock",
            ),
            AgentConfig(
                name="openai-gpt35",
                agent_type=AgentType.SDK,
                provider="openai",
                model="gpt-3.5-turbo",
                enabled=False,
                sdk_client_factory=lambda: "mock",
            ),
            AgentConfig(
                name="anthropic-claude",
                agent_type=AgentType.SDK,
                provider="anthropic",
                model="claude-3-opus",
                enabled=True,
                sdk_client_factory=lambda: "mock",
            ),
            AgentConfig(
                name="ollama-llama",
                agent_type=AgentType.CLI,
                provider="ollama",
                model="llama3",
                enabled=True,
                cli_command=["ollama", "run", "llama3"],
            ),
            AgentConfig(
                name="custom-http",
                agent_type=AgentType.HTTP,
                provider="custom",
                enabled=True,
                http_endpoint="http://localhost:8080",
            ),
        ]
        for config in configs:
            AgentRegistry.register(config)

    def test_get_enabled_agents(self, populated_registry: None) -> None:
        """Can filter to only enabled agents."""
        enabled = AgentRegistry.get_enabled_agents()
        assert len(enabled) == 4
        names = {a.name for a in enabled}
        assert "openai-gpt35" not in names
        assert "openai-gpt4" in names
        assert "anthropic-claude" in names

    def test_get_enabled_agents_empty_when_all_disabled(self) -> None:
        """Returns empty list when all agents are disabled."""
        config = AgentConfig(
            name="disabled-agent",
            agent_type=AgentType.SDK,
            provider="openai",
            enabled=False,
            sdk_client_factory=lambda: "mock",
        )
        AgentRegistry.register(config)
        assert AgentRegistry.get_enabled_agents() == []

    def test_get_by_provider(self, populated_registry: None) -> None:
        """Can filter agents by provider (only returns enabled agents)."""
        openai_agents = AgentRegistry.get_by_provider("openai")
        # Only 1 because openai-gpt35 has enabled=False
        assert len(openai_agents) == 1
        assert all(a.provider == "openai" for a in openai_agents)
        assert openai_agents[0].name == "openai-gpt4"

        anthropic_agents = AgentRegistry.get_by_provider("anthropic")
        assert len(anthropic_agents) == 1
        assert anthropic_agents[0].name == "anthropic-claude"

    def test_get_by_provider_nonexistent(self, populated_registry: None) -> None:
        """Filtering by non-existent provider returns empty list."""
        result = AgentRegistry.get_by_provider("nonexistent")
        assert result == []

    def test_get_by_type(self, populated_registry: None) -> None:
        """Can filter agents by type (only returns enabled agents)."""
        sdk_agents = AgentRegistry.get_by_type(AgentType.SDK)
        # Only 2 because openai-gpt35 has enabled=False
        assert len(sdk_agents) == 2
        assert all(a.agent_type == AgentType.SDK for a in sdk_agents)
        names = {a.name for a in sdk_agents}
        assert names == {"openai-gpt4", "anthropic-claude"}

        cli_agents = AgentRegistry.get_by_type(AgentType.CLI)
        assert len(cli_agents) == 1
        assert cli_agents[0].name == "ollama-llama"

        http_agents = AgentRegistry.get_by_type(AgentType.HTTP)
        assert len(http_agents) == 1
        assert http_agents[0].name == "custom-http"

    def test_get_by_type_none_matching(self) -> None:
        """Filtering by type with no matches returns empty list."""
        config = AgentConfig(
            name="sdk-only",
            agent_type=AgentType.SDK,
            provider="openai",
            sdk_client_factory=lambda: "mock",
        )
        AgentRegistry.register(config)

        result = AgentRegistry.get_by_type(AgentType.CLI)
        assert result == []


# ============================================================================
# AgentRegistry Unregistration Tests
# ============================================================================


class TestAgentRegistryUnregistration:
    """Tests for AgentRegistry unregistration operations."""

    def test_unregister_existing_agent(self) -> None:
        """Can unregister an existing agent."""
        config = AgentConfig(
            name="to-remove",
            agent_type=AgentType.SDK,
            provider="openai",
            sdk_client_factory=lambda: "mock",
        )
        AgentRegistry.register(config)
        assert AgentRegistry.count() == 1

        result = AgentRegistry.unregister("to-remove")
        assert result is True
        assert AgentRegistry.count() == 0
        assert AgentRegistry.get("to-remove") is None

    def test_unregister_nonexistent_agent(self) -> None:
        """Unregistering non-existent agent returns False."""
        result = AgentRegistry.unregister("nonexistent")
        assert result is False

    def test_clear_registry(self) -> None:
        """Can clear all agents from registry."""
        for i in range(5):
            config = AgentConfig(
                name=f"agent-{i}",
                agent_type=AgentType.SDK,
                provider="openai",
                sdk_client_factory=lambda: "mock",
            )
            AgentRegistry.register(config)

        assert AgentRegistry.count() == 5
        AgentRegistry.clear()
        assert AgentRegistry.count() == 0
        assert AgentRegistry.list_all() == []


# ============================================================================
# AgentRegistry Count Tests
# ============================================================================


class TestAgentRegistryCount:
    """Tests for AgentRegistry count operation."""

    def test_count_empty_registry(self) -> None:
        """Empty registry has count of 0."""
        assert AgentRegistry.count() == 0

    def test_count_after_registration(self) -> None:
        """Count increments after registration."""
        for i in range(3):
            config = AgentConfig(
                name=f"agent-{i}",
                agent_type=AgentType.SDK,
                provider="openai",
                sdk_client_factory=lambda: "mock",
            )
            AgentRegistry.register(config)
            assert AgentRegistry.count() == i + 1

    def test_count_after_unregistration(self) -> None:
        """Count decrements after unregistration."""
        configs = [
            AgentConfig(
                name=f"agent-{i}",
                agent_type=AgentType.SDK,
                provider="openai",
                sdk_client_factory=lambda: "mock",
            )
            for i in range(3)
        ]
        for config in configs:
            AgentRegistry.register(config)

        assert AgentRegistry.count() == 3
        AgentRegistry.unregister("agent-1")
        assert AgentRegistry.count() == 2


# ============================================================================
# AgentType Enum Tests
# ============================================================================


class TestAgentTypeEnum:
    """Tests for the AgentType enumeration."""

    def test_agent_type_values(self) -> None:
        """AgentType has expected values."""
        assert AgentType.SDK.value == "sdk"
        assert AgentType.CLI.value == "cli"
        assert AgentType.HTTP.value == "http"

    def test_agent_type_from_string(self) -> None:
        """Can create AgentType from string value."""
        assert AgentType("sdk") == AgentType.SDK
        assert AgentType("cli") == AgentType.CLI
        assert AgentType("http") == AgentType.HTTP

    def test_agent_type_invalid_string(self) -> None:
        """Invalid string raises ValueError."""
        with pytest.raises(ValueError):
            AgentType("invalid")
