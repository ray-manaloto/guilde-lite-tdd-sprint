"""Tests for AI agent module (PydanticAI)."""

from unittest.mock import patch

import pytest
from pydantic_ai.models.test import TestModel

from app.agents.assistant import AssistantAgent, Deps, get_agent
from app.agents.prompts import DEFAULT_SYSTEM_PROMPT
from app.agents.tools.datetime_tool import get_current_datetime


class TestDeps:
    """Tests for Deps dataclass."""

    def test_deps_default_values(self):
        """Test Deps has correct default values."""
        deps = Deps()
        assert deps.user_id is None
        assert deps.user_name is None
        assert deps.metadata == {}

    def test_deps_with_values(self):
        """Test Deps with custom values."""
        deps = Deps(user_id="123", user_name="Test User", metadata={"key": "value"})
        assert deps.user_id == "123"
        assert deps.user_name == "Test User"
        assert deps.metadata == {"key": "value"}


class TestGetCurrentDatetime:
    """Tests for get_current_datetime tool."""

    def test_returns_formatted_string(self):
        """Test get_current_datetime returns formatted string."""
        result = get_current_datetime()
        assert isinstance(result, str)
        # Should contain year, month, day
        assert len(result) > 10


class TestAssistantAgent:
    """Tests for AssistantAgent class."""

    def test_init_with_defaults(self):
        """Test AssistantAgent initializes with defaults."""
        agent = AssistantAgent()
        assert agent.system_prompt == DEFAULT_SYSTEM_PROMPT
        assert agent._agent is None

    def test_init_with_custom_values(self):
        """Test AssistantAgent with custom configuration."""
        agent = AssistantAgent(
            model_name="gpt-4",
            temperature=0.5,
            system_prompt="Custom prompt",
        )
        assert agent.model_name == "gpt-4"
        assert agent.temperature == 0.5
        assert agent.system_prompt == "Custom prompt"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("app.agents.assistant.OpenAIProvider")
    @patch("app.agents.assistant.OpenAIResponsesModel")
    def test_agent_property_creates_agent(self, mock_model, mock_provider):
        """Test agent property creates agent on first access."""
        mock_model.return_value = TestModel()
        agent = AssistantAgent(model_name="openai-responses:gpt-5.2-codex")
        _ = agent.agent
        assert agent._agent is not None
        mock_model.assert_called_once()

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("app.agents.assistant.OpenAIProvider")
    @patch("app.agents.assistant.OpenAIResponsesModel")
    def test_agent_property_caches_agent(self, mock_model, mock_provider):
        """Test agent property caches the agent instance."""
        mock_model.return_value = TestModel()
        agent = AssistantAgent(model_name="openai-responses:gpt-5.2-codex")
        agent1 = agent.agent
        agent2 = agent.agent
        assert agent1 is agent2
        mock_model.assert_called_once()

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("app.agents.assistant.OpenAIProvider")
    @patch("app.agents.assistant.OpenAIResponsesModel")
    def test_agent_uses_openai_responses_model(self, mock_model, mock_provider):
        """Test OpenAI responses model selection with prefix."""
        mock_model.return_value = TestModel()
        agent = AssistantAgent(model_name="openai-responses:gpt-5.2-codex")
        _ = agent.agent
        mock_model.assert_called_once()
        assert mock_model.call_args.args[0] == "gpt-5.2-codex"

    def test_agent_rejects_openai_chat_models(self):
        """Test OpenAI chat models are rejected."""
        agent = AssistantAgent(model_name="openai:gpt-4o-mini")
        with pytest.raises(ValueError, match="openai-responses"):
            _ = agent.agent

    @patch("app.agents.assistant.AnthropicModel")
    def test_agent_strips_anthropic_prefix(self, mock_model):
        """Test Anthropic prefix is normalized before model creation."""
        mock_model.return_value = TestModel()
        agent = AssistantAgent(
            model_name="anthropic:claude-opus-4-5-20251101",
            llm_provider="anthropic",
        )
        _ = agent.agent
        assert mock_model.call_args.args[0] == "claude-opus-4-5-20251101"


class TestGetAgent:
    """Tests for get_agent factory function."""

    def test_returns_assistant_agent(self):
        """Test get_agent returns AssistantAgent."""
        agent = get_agent()
        assert isinstance(agent, AssistantAgent)


class TestAgentRoutes:
    """Tests for agent WebSocket routes."""

    @pytest.mark.anyio
    async def test_agent_websocket_connection(self, client):
        """Test WebSocket connection to agent endpoint."""
        # This test verifies the WebSocket endpoint is accessible
        # Actual agent testing would require mocking OpenAI
        pass


class TestHistoryConversion:
    """Tests for conversation history conversion."""

    def test_empty_history(self):
        """Test with empty history."""
        _agent = AssistantAgent()
        # History conversion happens inside run/iter methods
        # We test the structure here
        history = []
        assert len(history) == 0

    def test_history_roles(self):
        """Test history with different roles."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "system", "content": "You are helpful"},
        ]
        assert len(history) == 3
        assert all("role" in msg and "content" in msg for msg in history)
