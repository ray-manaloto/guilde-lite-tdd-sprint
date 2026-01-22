"""Tests for AgentsSdkRunner."""

from types import SimpleNamespace

import pytest

from app.agents.sdk_runner import AgentsSdkRunner, normalize_litellm_model


class FakeModelSettings:
    def __init__(self, include_usage: bool = False):
        self.include_usage = include_usage


class FakeAgent:
    def __init__(self, *, name: str, instructions: str, model, model_settings):
        self.name = name
        self.instructions = instructions
        self.model = model
        self.model_settings = model_settings


class FakeRunner:
    @staticmethod
    async def run(agent, prompt: str):
        usage = SimpleNamespace(input_tokens=2, output_tokens=3, total_tokens=5)
        return SimpleNamespace(
            final_output=(
                '{"spec_markdown": "spec", "plan_markdown": "plan", '
                '"open_questions": [], "confidence": "high"}'
            ),
            context_wrapper=SimpleNamespace(usage=usage),
            tool_calls=[],
        )


class FakeLitellmModel:
    def __init__(self, model: str, api_key: str | None = None, base_url: str | None = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url


def test_normalize_litellm_model_adds_prefix():
    assert normalize_litellm_model("claude-opus") == "anthropic/claude-opus"
    assert normalize_litellm_model("anthropic/claude-opus") == "anthropic/claude-opus"
    assert normalize_litellm_model("anthropic:claude-opus") == "anthropic/claude-opus"


@pytest.mark.anyio
async def test_run_agent_parses_json_output():
    runner = AgentsSdkRunner(
        openai_model="openai-responses:gpt-5.2-codex",
        anthropic_model="claude-opus-4-5-20251101",
        openai_api_key="openai-key",
        anthropic_api_key="anthropic-key",
        agent_cls=FakeAgent,
        runner_cls=FakeRunner,
        model_settings_cls=FakeModelSettings,
        litellm_model_cls=FakeLitellmModel,
    )

    schema = {
        "type": "object",
        "required": ["spec_markdown", "plan_markdown", "open_questions", "confidence"],
    }

    result = await runner.run_agent(
        provider="openai",
        name="planner",
        instructions="Return JSON",
        prompt="Plan this",
        output_format="json",
        output_schema=schema,
    )

    assert result.output_json == {
        "spec_markdown": "spec",
        "plan_markdown": "plan",
        "open_questions": [],
        "confidence": "high",
    }
    assert result.output_text.startswith("{")
    assert result.usage == {"input": 2, "output": 3, "total": 5}


def test_builds_litellm_model_for_anthropic():
    runner = AgentsSdkRunner(
        openai_model="openai-responses:gpt-5.2-codex",
        anthropic_model="claude-opus-4-5-20251101",
        openai_api_key="openai-key",
        anthropic_api_key="anthropic-key",
        litellm_proxy_base_url="https://litellm.local",
        agent_cls=FakeAgent,
        runner_cls=FakeRunner,
        model_settings_cls=FakeModelSettings,
        litellm_model_cls=FakeLitellmModel,
    )

    model = runner._build_model(provider="anthropic", model_name=None)

    assert isinstance(model, FakeLitellmModel)
    assert model.model == "anthropic/claude-opus-4-5-20251101"
    assert model.api_key == "anthropic-key"
    assert model.base_url == "https://litellm.local"
