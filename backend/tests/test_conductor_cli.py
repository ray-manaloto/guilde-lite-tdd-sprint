"""Tests for Conductor CLI planning command."""

import pytest
from click.testing import CliRunner

from app.agents.sdk_runner import AgentsSdkRunResult
from app.commands.conductor_plan import conductor_plan

pytestmark = pytest.mark.tui


class FakeRunner:
    def __init__(self, *args, **kwargs):
        self.calls = 0

    async def run_agent(
        self,
        *,
        provider: str,
        name: str,
        instructions: str,
        prompt: str,
        model_name: str | None = None,
        output_format: str = "markdown",
        output_schema: dict | None = None,
    ) -> AgentsSdkRunResult:
        self.calls += 1
        if output_schema and "questions" in output_schema.get("required", []):
            return AgentsSdkRunResult(
                provider=provider,
                model_name=model_name or "openai-responses:gpt-5.2-codex",
                output_text="{}",
                output_json={"questions": [], "confidence": "high"},
                usage=None,
                tool_names=[],
            )
        return AgentsSdkRunResult(
            provider=provider,
            model_name=model_name or "openai-responses:gpt-5.2-codex",
            output_text="{}",
            output_json={
                "spec_markdown": "# Spec\n\nGenerated",
                "plan_markdown": "# Plan\n\nSteps",
                "open_questions": [],
                "confidence": "high",
            },
            usage=None,
            tool_names=[],
        )


def test_conductor_plan_writes_files(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.commands.conductor_plan.AgentsSdkRunner",
        lambda *args, **kwargs: FakeRunner(),
    )

    runner = CliRunner()
    result = runner.invoke(
        conductor_plan,
        [
            "--track-id",
            "track-abc",
            "--task",
            "Build a thing",
            "--output-format",
            "json",
            "--conductor-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0

    spec_path = tmp_path / "tracks" / "track-abc" / "spec.md"
    plan_path = tmp_path / "tracks" / "track-abc" / "plan.md"

    assert spec_path.exists()
    assert plan_path.exists()
    assert "# Spec" in spec_path.read_text(encoding="utf-8")
    assert "# Plan" in plan_path.read_text(encoding="utf-8")
