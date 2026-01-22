"""Deep research runner using OpenAI Agents SDK."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents import ModelSettings

from app.agents.sdk_runner import AgentsSdkRunner
from app.core.config import settings

_RESEARCH_KEYWORDS = (
    "research",
    "deep research",
    "investigate",
    "benchmark",
    "compare",
    "best practices",
    "survey",
    "sources",
)

_DEFAULT_RESEARCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["summary_markdown", "sources", "open_questions", "confidence"],
    "properties": {
        "summary_markdown": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
        "open_questions": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
}

_DEEP_RESEARCH_INSTRUCTIONS = (
    "You are a deep research assistant. Provide evidence-backed findings. "
    "Return Markdown with these sections: Summary, Findings, Recommendations, "
    "Sources, Open Questions. Keep sources as a bulleted list of URLs or citations."
)

_DEEP_RESEARCH_JSON_INSTRUCTIONS = (
    "You are a deep research assistant. Return JSON with keys: "
    "summary_markdown, sources, open_questions, confidence. "
    "summary_markdown should include Findings and Recommendations sections."
)


@dataclass
class DeepResearchResult:
    """Result payload from a deep research run."""

    provider: str
    model_name: str
    query: str
    output_markdown: str
    output_json: dict[str, Any] | None
    sources: list[str]
    confidence: str | None


@dataclass
class DeepResearchArtifacts:
    """Paths to deep research artifacts written for a track."""

    research_path: Path
    artifact_path: Path
    json_path: Path | None


def should_run_deep_research(task: str | None) -> bool:
    """Return True when a task description indicates research is needed."""
    if not task:
        return False
    lowered = task.lower()
    return any(keyword in lowered for keyword in _RESEARCH_KEYWORDS)


def has_research_artifact(track_id: str, conductor_root: Path) -> bool:
    """Check whether a track already has a research artifact."""
    track_dir = Path(conductor_root) / "tracks" / track_id
    research_path = track_dir / "research.md"
    if research_path.exists():
        return True
    artifacts_dir = track_dir / "artifacts" / "research"
    return artifacts_dir.exists() and any(artifacts_dir.glob("*.md"))


class DeepResearchRunner:
    """Run deep research prompts via Agents SDK."""

    def __init__(
        self,
        *,
        provider: str = "openai",
        model_name: str | None = None,
        runner: AgentsSdkRunner | None = None,
    ) -> None:
        self.provider = provider
        self.model_name = model_name or self._resolve_default_model(provider)
        self.runner = runner or AgentsSdkRunner()

    async def run(
        self,
        *,
        query: str,
        output_format: str = "markdown",
        output_schema: dict[str, Any] | None = None,
    ) -> DeepResearchResult:
        prompt = f"Deep research task:\n{query}"
        model_settings = self._build_model_settings()
        if output_format == "json":
            result = await self.runner.run_agent(
                provider=self.provider,
                name="deep-research",
                instructions=_DEEP_RESEARCH_JSON_INSTRUCTIONS,
                prompt=prompt,
                model_name=self.model_name,
                output_format="json",
                output_schema=output_schema or _DEFAULT_RESEARCH_SCHEMA,
                model_settings=model_settings,
            )
            payload = result.output_json or {}
            markdown = _render_json_markdown(query, payload)
            return DeepResearchResult(
                provider=result.provider,
                model_name=result.model_name,
                query=query,
                output_markdown=markdown,
                output_json=payload,
                sources=list(payload.get("sources", []) or []),
                confidence=payload.get("confidence"),
            )

        result = await self.runner.run_agent(
            provider=self.provider,
            name="deep-research",
            instructions=_DEEP_RESEARCH_INSTRUCTIONS,
            prompt=prompt,
            model_name=self.model_name,
            output_format="markdown",
            model_settings=model_settings,
        )
        markdown = _normalize_markdown(query, result.output_text, sources=None, confidence=None)
        return DeepResearchResult(
            provider=result.provider,
            model_name=result.model_name,
            query=query,
            output_markdown=markdown,
            output_json=None,
            sources=[],
            confidence=None,
        )

    @staticmethod
    def _resolve_default_model(provider: str) -> str | None:
        if settings.DEEP_RESEARCH_MODEL:
            return settings.DEEP_RESEARCH_MODEL
        if provider == "anthropic":
            return settings.ANTHROPIC_MODEL
        return settings.OPENAI_MODEL

    def _build_model_settings(self) -> ModelSettings | None:
        if not self.model_name or self.provider != "openai":
            return None
        if "deep-research" not in self.model_name:
            return None
        return ModelSettings(
            include_usage=True,
            tool_choice="web_search_preview",
            extra_body={"tools": [{"type": "web_search_preview"}]},
        )


def write_deep_research_artifacts(
    *,
    track_id: str,
    result: DeepResearchResult,
    conductor_root: Path,
) -> DeepResearchArtifacts:
    """Write deep research digest + immutable artifact for a track."""
    track_dir = Path(conductor_root) / "tracks" / track_id
    artifacts_dir = track_dir / "artifacts" / "research"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    research_path = track_dir / "research.md"
    artifact_path = artifacts_dir / f"{timestamp}.md"

    research_path.write_text(result.output_markdown, encoding="utf-8")
    artifact_path.write_text(result.output_markdown, encoding="utf-8")

    json_path = None
    if result.output_json is not None:
        json_path = artifacts_dir / f"{timestamp}.json"
        json_path.write_text(_json_dump(result.output_json), encoding="utf-8")

    return DeepResearchArtifacts(
        research_path=research_path,
        artifact_path=artifact_path,
        json_path=json_path,
    )


def _json_dump(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, indent=2, sort_keys=True)


def _render_json_markdown(query: str, payload: dict[str, Any]) -> str:
    summary = str(payload.get("summary_markdown", "")).strip()
    if summary:
        markdown = summary
    else:
        markdown = "## Summary\n\n(No summary provided.)"

    open_questions = payload.get("open_questions") or []
    sources = payload.get("sources") or []
    confidence = payload.get("confidence")

    markdown = _normalize_markdown(query, markdown, sources=sources, confidence=confidence)
    if open_questions:
        markdown = (
            f"{markdown}\n\n## Open Questions\n"
            + "\n".join(f"- {question}" for question in open_questions)
        )
    return markdown


def _normalize_markdown(
    query: str,
    output: str,
    *,
    sources: list[str] | None,
    confidence: str | None,
) -> str:
    trimmed = output.strip()
    if not trimmed.startswith("#"):
        trimmed = f"# Deep Research\n\n{trimmed}"
    if "## Research Question" not in trimmed:
        trimmed = f"{trimmed}\n\n## Research Question\n\n{query}"
    if sources and "## Sources" not in trimmed:
        trimmed = f"{trimmed}\n\n## Sources\n" + "\n".join(
            f"- {source}" for source in sources
        )
    if confidence and "## Confidence" not in trimmed:
        trimmed = f"{trimmed}\n\n## Confidence\n\n{confidence}"
    return trimmed


__all__ = [
    "DeepResearchArtifacts",
    "DeepResearchResult",
    "DeepResearchRunner",
    "has_research_artifact",
    "should_run_deep_research",
    "write_deep_research_artifacts",
]
