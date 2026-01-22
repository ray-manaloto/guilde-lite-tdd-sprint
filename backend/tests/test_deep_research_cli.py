"""Tests for deep research CLI command."""

from click.testing import CliRunner

from app.agents.deep_research import DeepResearchResult
from app.commands.deep_research import deep_research


class FakeRunner:
    async def run(self, *, query: str, output_format: str, output_schema=None):
        return DeepResearchResult(
            provider="openai",
            model_name="openai-responses:gpt-5.2-codex",
            query=query,
            output_markdown="# Deep Research\n\n## Summary\n\nTest",
            output_json=None,
            sources=[],
            confidence="high",
        )


def test_deep_research_writes_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.commands.deep_research.DeepResearchRunner",
        lambda *args, **kwargs: FakeRunner(),
    )

    runner = CliRunner()
    result = runner.invoke(
        deep_research,
        [
            "--track-id",
            "track-123",
            "--query",
            "Research best practices for hooks",
            "--conductor-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    research_path = tmp_path / "tracks" / "track-123" / "research.md"
    artifacts_dir = tmp_path / "tracks" / "track-123" / "artifacts" / "research"

    assert research_path.exists()
    assert artifacts_dir.exists()
    assert list(artifacts_dir.glob("*.md"))
