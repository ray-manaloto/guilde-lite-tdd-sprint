# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
"""Spec workflow CLI command."""

import asyncio
from pathlib import Path

import click

from app.commands import command, error, info, success
from app.schemas.spec import SpecCreate
from app.services.spec import SpecService


@command("spec-run", help="Create a spec draft from a task description")
@click.option("--task", help="Task description for the spec")
@click.option("--task-file", type=click.Path(path_type=Path), help="Read task from a file")
@click.option("--title", help="Optional spec title")
@click.option("--validate", is_flag=True, help="Validate the spec after creation")
def spec_run(task: str | None, task_file: Path | None, title: str | None, validate: bool) -> None:
    """Create a spec draft and optionally validate it."""
    if not task and not task_file:
        error("Provide --task or --task-file")
        raise SystemExit(1)

    if task_file:
        task = task_file.read_text(encoding="utf-8").strip()

    if not task:
        error("Task description is empty.")
        raise SystemExit(1)

    spec_in = SpecCreate(title=title, task=task)

    from app.db.session import async_session_maker

    async def _run():
        async with async_session_maker() as session:
            service = SpecService(session)
            spec = await service.create(spec_in)
            await session.commit()
            if validate:
                spec, validation = await service.validate(spec.id)
                await session.commit()
                return spec, validation
            return spec, None

    info("Creating spec draft...")
    spec, validation = asyncio.run(_run())
    success(f"Spec created: {spec.id}")
    click.echo(f"Title: {spec.title}")
    click.echo(f"Complexity: {spec.complexity}")
    click.echo(f"Phases: {', '.join(spec.phases)}")
    if validation:
        click.echo(f"Validated: {validation['valid']}")
