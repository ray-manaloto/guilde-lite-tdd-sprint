"""Deep research CLI command."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import click

from app.agents.deep_research import DeepResearchRunner, write_deep_research_artifacts
from app.commands import command, error, info, success, warning


def _default_conductor_root() -> Path:
    return Path(__file__).resolve().parents[3] / "conductor"


def _load_schema(schema_path: Path | None) -> dict[str, Any] | None:
    if schema_path is None:
        return None
    return json.loads(schema_path.read_text(encoding="utf-8"))


@command("deep-research", help="Run deep research and write Conductor artifacts.")
@click.option("--track-id", required=True, help="Conductor track ID")
@click.option("--query", help="Research question or task")
@click.option("--query-file", type=click.Path(path_type=Path), help="Read query from file")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic"], case_sensitive=False),
    default="openai",
    show_default=True,
)
@click.option("--model", help="Override model name")
@click.option(
    "--output-format",
    type=click.Choice(["markdown", "json"], case_sensitive=False),
    default="markdown",
    show_default=True,
)
@click.option("--output-schema", type=click.Path(path_type=Path), help="JSON schema file")
@click.option(
    "--conductor-root",
    type=click.Path(path_type=Path),
    default=None,
    help="Override Conductor root directory",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing research digest for the track",
)
def deep_research(
    track_id: str,
    query: str | None,
    query_file: Path | None,
    provider: str,
    model: str | None,
    output_format: str,
    output_schema: Path | None,
    conductor_root: Path | None,
    force: bool,
) -> None:
    """Run deep research and persist artifacts for a track."""
    if not query and not query_file:
        error("Provide --query or --query-file")
        raise SystemExit(1)

    if query_file:
        query = query_file.read_text(encoding="utf-8").strip()

    if not query:
        error("Query is empty.")
        raise SystemExit(1)

    root = conductor_root or _default_conductor_root()
    research_path = Path(root) / "tracks" / track_id / "research.md"
    if research_path.exists() and not force:
        warning("Research digest already exists; use --force to overwrite.")
        raise SystemExit(0)

    schema_override = _load_schema(output_schema)
    runner = DeepResearchRunner(provider=provider.lower(), model_name=model)

    info("Running deep research...")
    result = asyncio.run(
        runner.run(
            query=query,
            output_format=output_format.lower(),
            output_schema=schema_override,
        )
    )

    artifacts = write_deep_research_artifacts(
        track_id=track_id,
        result=result,
        conductor_root=root,
    )

    success(f"Deep research digest written: {artifacts.research_path}")
    success(f"Deep research artifact written: {artifacts.artifact_path}")
    if artifacts.json_path:
        success(f"Deep research JSON artifact written: {artifacts.json_path}")
