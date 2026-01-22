"""OpenAI Agents SDK runner utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from agents import Agent, ModelSettings, Runner

from app.core.config import settings

if TYPE_CHECKING:
    from agents.extensions.models.litellm_model import LitellmModel


@dataclass
class AgentsSdkRunResult:
    """Normalized result for an Agents SDK run."""

    provider: str
    model_name: str
    output_text: str
    output_json: dict[str, Any] | None
    usage: dict[str, int] | None
    tool_names: list[str]


def normalize_litellm_model(model_name: str) -> str:
    """Normalize model names to LiteLLM anthropic/ prefix."""
    if model_name.startswith("anthropic/"):
        return model_name
    if model_name.startswith("anthropic:"):
        return f"anthropic/{model_name.split(':', 1)[1]}"
    return f"anthropic/{model_name}"


class AgentsSdkRunner:
    """Run Agents SDK agents with OpenAI or LiteLLM-backed Anthropic models."""

    def __init__(
        self,
        *,
        openai_model: str | None = None,
        anthropic_model: str | None = None,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        litellm_proxy_base_url: str | None = None,
        agent_cls: Callable[..., Agent] = Agent,
        runner_cls: type[Runner] = Runner,
        model_settings_cls: Callable[..., ModelSettings] = ModelSettings,
        litellm_model_cls: Callable[..., "LitellmModel"] | None = None,
    ) -> None:
        self.openai_model = openai_model or settings.OPENAI_MODEL
        self.anthropic_model = anthropic_model or settings.ANTHROPIC_MODEL
        self.openai_api_key = openai_api_key or settings.OPENAI_API_KEY
        self.anthropic_api_key = anthropic_api_key or settings.ANTHROPIC_API_KEY
        self.litellm_proxy_base_url = litellm_proxy_base_url
        self.agent_cls = agent_cls
        self.runner_cls = runner_cls
        self.model_settings_cls = model_settings_cls
        self.litellm_model_cls = litellm_model_cls

    def _build_model(self, *, provider: str, model_name: str | None) -> Any:
        if provider == "anthropic":
            name = normalize_litellm_model(model_name or self.anthropic_model)
            model_cls = self.litellm_model_cls or self._load_litellm_model()
            return model_cls(
                model=name,
                api_key=self.anthropic_api_key,
                base_url=self.litellm_proxy_base_url,
            )
        return self._normalize_openai_model(model_name or self.openai_model)

    @staticmethod
    def _load_litellm_model() -> Callable[..., "LitellmModel"]:
        from agents.extensions.models.litellm_model import LitellmModel

        return LitellmModel

    @staticmethod
    def _normalize_openai_model(model_name: str) -> str:
        """Normalize OpenAI model strings for Agents SDK."""
        if model_name.startswith("openai-responses:"):
            return model_name.split(":", 1)[1]
        if model_name.startswith("openai:"):
            raise ValueError("OpenAI chat models are disabled; use openai-responses:<model>.")
        return model_name

    async def run_agent(
        self,
        *,
        provider: str,
        name: str,
        instructions: str,
        prompt: str,
        model_name: str | None = None,
        output_format: str = "markdown",
        output_schema: dict[str, Any] | None = None,
        tools: list[Any] | None = None,
        model_settings: ModelSettings | None = None,
    ) -> AgentsSdkRunResult:
        model = self._build_model(provider=provider, model_name=model_name)
        settings_override = model_settings or self.model_settings_cls(include_usage=True)
        agent_kwargs: dict[str, Any] = {
            "name": name,
            "instructions": instructions,
            "model": model,
            "model_settings": settings_override,
        }
        if tools is not None:
            agent_kwargs["tools"] = tools
        agent = self.agent_cls(**agent_kwargs)
        result = await self.runner_cls.run(agent, prompt)
        output_text = self._extract_output(result)
        output_json = None
        if output_format == "json":
            output_json = json.loads(output_text)
            self._validate_required_fields(output_json, output_schema)
        return AgentsSdkRunResult(
            provider=provider,
            model_name=model_name or (self.anthropic_model if provider == "anthropic" else self.openai_model),
            output_text=output_text,
            output_json=output_json,
            usage=self._extract_usage(result),
            tool_names=self._extract_tool_names(result),
        )

    @staticmethod
    def _extract_output(result: Any) -> str:
        if hasattr(result, "final_output"):
            return str(result.final_output)
        if hasattr(result, "output"):
            return str(result.output)
        return str(result)

    @staticmethod
    def _extract_usage(result: Any) -> dict[str, int] | None:
        usage = None
        context_wrapper = getattr(result, "context_wrapper", None)
        if context_wrapper is not None:
            usage = getattr(context_wrapper, "usage", None)
        if usage is None:
            return None
        return {
            "input": getattr(usage, "input_tokens", 0),
            "output": getattr(usage, "output_tokens", 0),
            "total": getattr(usage, "total_tokens", 0),
        }

    @staticmethod
    def _extract_tool_names(result: Any) -> list[str]:
        tool_names: list[str] = []
        for call in getattr(result, "tool_calls", []) or []:
            name = getattr(call, "name", None)
            if name:
                tool_names.append(name)
        return tool_names

    @staticmethod
    def _validate_required_fields(
        output_json: dict[str, Any],
        output_schema: dict[str, Any] | None,
    ) -> None:
        if not output_schema:
            return
        required = output_schema.get("required")
        if not required:
            return
        missing = [key for key in required if key not in output_json]
        if missing:
            raise ValueError(f"Output missing required fields: {', '.join(missing)}")
