"""Conductor planning CLI command."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import click

from app.agents.sdk_runner import AgentsSdkRunner
from app.commands import command, error, info, success
from app.conductor.store import ConductorStore
from app.core.config import settings

_DEFAULT_PLANNING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["questions", "confidence"],
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["question"],
                "properties": {
                    "question": {"type": "string"},
                    "rationale": {"type": "string"},
                },
            },
        },
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
}

_DEFAULT_SPEC_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["spec_markdown", "plan_markdown", "open_questions", "confidence"],
    "properties": {
        "spec_markdown": {"type": "string"},
        "plan_markdown": {"type": "string"},
        "open_questions": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
}

_PLANNING_INSTRUCTIONS = (
    "You are running a planning interview. "
    "Return JSON with a list of clarifying questions and a confidence rating. "
    "Do not propose solutions or plans."
)

_SPEC_PLAN_INSTRUCTIONS = (
    "Generate a Conductor spec and plan. "
    "Return JSON with spec_markdown and plan_markdown, plus open_questions and confidence."
)


def _default_conductor_root() -> Path:
    return Path(__file__).resolve().parents[3] / "conductor"


def _load_schema(schema_path: Path | None) -> dict[str, Any] | None:
    if schema_path is None:
        return None
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _parse_markdown_sections(output: str) -> tuple[str, str]:
    spec_marker = "# Spec"
    plan_marker = "# Plan"
    if spec_marker not in output or plan_marker not in output:
        raise ValueError("Markdown output must include '# Spec' and '# Plan' headings.")
    spec_part, plan_part = output.split(plan_marker, 1)
    spec_content = spec_part.replace(spec_marker, "", 1).strip()
    plan_content = plan_part.strip()
    return f"# Spec\n\n{spec_content}", f"# Plan\n\n{plan_content}"


async def _run_planning_questions(
    runner: AgentsSdkRunner,
    task: str,
    max_questions: int,
) -> dict[str, Any]:
    prompt = (
        "Ask clarifying questions for the sprint task below. "
        f"Ask up to {max_questions} questions.\n\nTask:\n{task}"
    )
    result = await runner.run_agent(
        provider="openai",
        name="planning",
        instructions=_PLANNING_INSTRUCTIONS,
        prompt=prompt,
        output_format="json",
        output_schema=_DEFAULT_PLANNING_SCHEMA,
    )
    return result.output_json or {"questions": [], "confidence": "low"}


async def _run_spec_plan(
    runner: AgentsSdkRunner,
    task: str,
    answers: list[dict[str, str]],
    output_format: str,
    output_schema: dict[str, Any] | None,
) -> tuple[str, str, dict[str, Any]]:
    answers_block = "\n".join(
        f"Q: {item['question']}\nA: {item['answer']}" for item in answers
    )
    prompt = (
        "Create a Conductor spec and plan for the task.\n\n"
        f"Task:\n{task}\n\n"
        f"Clarifications:\n{answers_block or 'None'}"
    )
    if output_format == "json":
        schema = output_schema or _DEFAULT_SPEC_PLAN_SCHEMA
        result = await runner.run_agent(
            provider="openai",
            name="spec-plan",
            instructions=_SPEC_PLAN_INSTRUCTIONS,
            prompt=prompt,
            output_format="json",
            output_schema=schema,
        )
        payload = result.output_json or {}
        return (
            payload.get("spec_markdown", ""),
            payload.get("plan_markdown", ""),
            payload,
        )

    result = await runner.run_agent(
        provider="openai",
        name="spec-plan",
        instructions=(
            "Return Markdown with '# Spec' and '# Plan' sections. "
            "Do not include JSON."
        ),
        prompt=prompt,
        output_format="markdown",
    )
    spec_md, plan_md = _parse_markdown_sections(result.output_text)
    return spec_md, plan_md, {"confidence": "low", "open_questions": []}


@command("conductor-plan", help="Create or refresh Conductor spec + plan.")
@click.option("--track-id", required=True, help="Conductor track ID")
@click.option("--task", help="Task description")
@click.option("--task-file", type=click.Path(path_type=Path), help="Read task from file")
@click.option("--max-questions", default=5, show_default=True, type=int)
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
def conductor_plan(
    track_id: str,
    task: str | None,
    task_file: Path | None,
    max_questions: int,
    output_format: str,
    output_schema: Path | None,
    conductor_root: Path | None,
) -> None:
    """Generate a Conductor spec and plan from a CLI interview."""
    if not task and not task_file:
        error("Provide --task or --task-file")
        raise SystemExit(1)

    if task_file:
        task = task_file.read_text(encoding="utf-8").strip()

    if not task:
        error("Task description is empty.")
        raise SystemExit(1)

    runner = AgentsSdkRunner()
    store = ConductorStore(root=conductor_root or _default_conductor_root())
    schema_override = _load_schema(output_schema)

    info("Running planning interview...")
    planning_payload = asyncio.run(_run_planning_questions(runner, task, max_questions))
    questions = planning_payload.get("questions", [])

    answers: list[dict[str, str]] = []
    for item in questions:
        question = item.get("question", "").strip()
        if not question:
            continue
        answer = click.prompt(question)
        answers.append({"question": question, "answer": answer})

    info("Generating spec + plan...")
    spec_md, plan_md, payload = asyncio.run(
        _run_spec_plan(
            runner,
            task,
            answers,
            output_format=output_format.lower(),
            output_schema=schema_override,
        )
    )

    store.write_spec(track_id, spec_md)
    store.write_plan(track_id, plan_md)

    success(f"Conductor spec + plan written for track: {track_id}")
    if payload.get("confidence") == "low":
        click.echo("Confidence is low; manual confirmation required before implementation.")
