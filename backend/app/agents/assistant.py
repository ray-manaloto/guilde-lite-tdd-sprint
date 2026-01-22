"""Assistant agent with PydanticAI.

The main conversational agent that can be extended with custom tools.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from app.agents.deps import Deps
from app.agents.prompts import DEFAULT_SYSTEM_PROMPT
from app.agents.tools import fetch_url_content, get_current_datetime, run_agent_browser
from app.agents.tools.filesystem import read_file, write_file, list_dir
from app.agents.tools.agent_integration import run_codex_agent, run_claude_agent
from app.core.config import settings

logger = logging.getLogger(__name__)





class AssistantAgent:
    """Assistant agent wrapper for conversational AI.

    Encapsulates agent creation and execution with tool support.
    """

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
        llm_provider: str | None = None,
        allow_cli_tools: bool | None = None,
    ):
        self.llm_provider = (llm_provider or settings.LLM_PROVIDER).lower()
        self.model_name = model_name or settings.model_for_provider(self.llm_provider)
        self.temperature = temperature or settings.AI_TEMPERATURE
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.allow_cli_tools = True if allow_cli_tools is None else allow_cli_tools
        self._agent: Agent[Deps, str] | None = None

    def _create_agent(self) -> Agent[Deps, str]:
        """Create and configure the PydanticAI agent."""
        model = self._build_model()

        agent = Agent[Deps, str](
            model=model,
            model_settings=ModelSettings(temperature=self.temperature),
            system_prompt=self.system_prompt,
        )

        self._register_tools(agent)

        return agent

    def _build_model(self):
        """Select the provider-specific model implementation."""
        provider = self.llm_provider
        if provider == "anthropic":
            model_name = self._normalize_anthropic_model(self.model_name)
            anthropic_provider = AnthropicProvider(
                api_key=settings.api_key_for_provider(provider),
                base_url=settings.ANTHROPIC_BASE_URL or None,
            )
            return AnthropicModel(
                model_name,
                provider=anthropic_provider,
            )
        if provider == "openrouter":
            from pydantic_ai.models.openrouter import OpenRouterModel
            from pydantic_ai.providers.openrouter import OpenRouterProvider

            return OpenRouterModel(
                self.model_name,
                provider=OpenRouterProvider(api_key=settings.api_key_for_provider(provider)),
            )
        model_name = self._normalize_openai_model(self.model_name)
        openai_provider = OpenAIProvider(api_key=settings.api_key_for_provider(provider))
        return OpenAIResponsesModel(model_name, provider=openai_provider)

    @staticmethod
    def _normalize_openai_model(model_name: str) -> str:
        """Normalize OpenAI model strings for Responses API usage."""
        if model_name.startswith("openai-responses:"):
            return model_name.split(":", 1)[1]
        if model_name.startswith("openai:"):
            raise ValueError("OpenAI chat models are disabled; use openai-responses:<model>.")
        raise ValueError("OpenAI models must use openai-responses:<model>.")

    @staticmethod
    def _normalize_anthropic_model(model_name: str) -> str:
        """Normalize Anthropic model strings for SDK usage."""
        if model_name.startswith("anthropic:"):
            return model_name.split(":", 1)[1]
        return model_name

    def _register_tools(self, agent: Agent[Deps, str]) -> None:
        """Register all tools on the agent."""

        @agent.tool
        async def current_datetime(ctx: RunContext[Deps]) -> str:
            """Get the current date and time.

            Use this tool when you need to know the current date or time.
            """
            return get_current_datetime()

        if settings.AGENT_BROWSER_ENABLED:

            @agent.tool
            async def agent_browser(ctx: RunContext[Deps], command: str) -> str:
                """Run an agent-browser command for live web interactions."""
                return run_agent_browser(command, settings.AGENT_BROWSER_TIMEOUT_SECONDS)

        if settings.HTTP_FETCH_ENABLED:

            @agent.tool
            async def http_fetch(ctx: RunContext[Deps], url: str) -> str:
                """Fetch a URL over HTTP and return the page text."""
                return fetch_url_content(
                    url,
                    timeout_seconds=settings.HTTP_FETCH_TIMEOUT_SECONDS,
                    max_chars=settings.HTTP_FETCH_MAX_CHARS,
                )

        if settings.AGENT_FS_ENABLED and settings.AUTOCODE_ARTIFACTS_DIR:
            
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

        if self.allow_cli_tools:

            @agent.tool
            async def call_codex_agent(ctx: RunContext[Deps], prompt: str) -> str:
                """Delegate a task to the Codex CLI agent."""
                return run_codex_agent(ctx, prompt)

            @agent.tool
            async def call_claude_agent(ctx: RunContext[Deps], prompt: str) -> str:
                """Delegate a task to the Claude Code CLI agent."""
                return run_claude_agent(ctx, prompt)

    @property
    def agent(self) -> Agent[Deps, str]:
        """Get or create the agent instance."""
        if self._agent is None:
            self._agent = self._create_agent()
        return self._agent

    async def run(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        deps: Deps | None = None,
    ) -> tuple[str, list[Any], Deps]:
        """Run agent and return the output along with tool call events.

        Args:
            user_input: User's message.
            history: Conversation history as list of {"role": "...", "content": "..."}.
            deps: Optional dependencies. If not provided, a new Deps will be created.

        Returns:
            Tuple of (output_text, tool_events, deps).
        """
        model_history: list[ModelRequest | ModelResponse] = []

        for msg in history or []:
            if msg["role"] == "user":
                model_history.append(ModelRequest(parts=[UserPromptPart(content=msg["content"])]))
            elif msg["role"] == "assistant":
                model_history.append(ModelResponse(parts=[TextPart(content=msg["content"])]))
            elif msg["role"] == "system":
                model_history.append(ModelRequest(parts=[SystemPromptPart(content=msg["content"])]))

        agent_deps = deps if deps is not None else Deps()
        
        # Initialize session-scoped artifact directory if configured
        if settings.AUTOCODE_ARTIFACTS_DIR and agent_deps.session_dir is None:
            # 9-digit precision emulation (microseconds + 000) or just standard high precision
            timestamp = datetime.now().strftime("%Y-%m-%dT%H%M%S.%f")
            session_path = settings.AUTOCODE_ARTIFACTS_DIR / timestamp
            try:
                session_path.mkdir(parents=True, exist_ok=True)
                agent_deps.session_dir = session_path
                logger.info(f"Created session artifact directory: {session_path}")
            except Exception as e:
                logger.error(f"Failed to create session artifact directory: {e}")

        logger.info(f"Running agent with user input: {user_input[:100]}...")
        result = await self.agent.run(user_input, deps=agent_deps, message_history=model_history)

        tool_events: list[Any] = []
        for message in result.all_messages():
            if hasattr(message, "parts"):
                for part in message.parts:
                    if hasattr(part, "tool_name"):
                        tool_events.append(part)

        logger.info(f"Agent run complete. Output length: {len(result.output)} chars")

        return result.output, tool_events, agent_deps

    async def iter(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        deps: Deps | None = None,
    ):
        """Stream agent execution with full event access.

        Args:
            user_input: User's message.
            history: Conversation history.
            deps: Optional dependencies.

        Yields:
            Agent events for streaming responses.
        """
        model_history: list[ModelRequest | ModelResponse] = []

        for msg in history or []:
            if msg["role"] == "user":
                model_history.append(ModelRequest(parts=[UserPromptPart(content=msg["content"])]))
            elif msg["role"] == "assistant":
                model_history.append(ModelResponse(parts=[TextPart(content=msg["content"])]))
            elif msg["role"] == "system":
                model_history.append(ModelRequest(parts=[SystemPromptPart(content=msg["content"])]))

        agent_deps = deps if deps is not None else Deps()

        # Initialize session-scoped artifact directory if configured
        if settings.AUTOCODE_ARTIFACTS_DIR and agent_deps.session_dir is None:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H%M%S.%f")
            session_path = settings.AUTOCODE_ARTIFACTS_DIR / timestamp
            try:
                session_path.mkdir(parents=True, exist_ok=True)
                agent_deps.session_dir = session_path
                logger.info(f"Created session artifact directory: {session_path}")
            except Exception as e:
                logger.error(f"Failed to create session artifact directory: {e}")

        async with self.agent.iter(
            user_input,
            deps=agent_deps,
            message_history=model_history,
        ) as run:
            async for event in run:
                yield event


def get_agent() -> AssistantAgent:
    """Factory function to create an AssistantAgent.

    Returns:
        Configured AssistantAgent instance.
    """
    return AssistantAgent()


async def run_agent(
    user_input: str,
    history: list[dict[str, str]],
    deps: Deps | None = None,
) -> tuple[str, list[Any], Deps]:
    """Run agent and return the output along with tool call events.

    This is a convenience function for backwards compatibility.

    Args:
        user_input: User's message.
        history: Conversation history.
        deps: Optional dependencies.

    Returns:
        Tuple of (output_text, tool_events, deps).
    """
    agent = get_agent()
    return await agent.run(user_input, history, deps)
