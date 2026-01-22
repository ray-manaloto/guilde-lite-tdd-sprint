"""QA gate commands for smoke and nightly runs."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import click

from app.commands import command, error, info, success


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    info(f"Running: {' '.join(cmd)} (cwd={cwd})")
    result = subprocess.run(cmd, cwd=cwd, env=env, text=True)
    if result.returncode != 0:
        error(f"Command failed ({result.returncode}): {' '.join(cmd)}")
        raise SystemExit(result.returncode)


@command("qa-smoke", help="Run smoke QA gates (backend integration + frontend smoke E2E).")
@click.option("--skip-backend", is_flag=True, help="Skip backend integration tests.")
@click.option("--skip-frontend", is_flag=True, help="Skip frontend smoke E2E tests.")
@click.option("--live", is_flag=True, help="Enable live CLI integration tests.")
@click.option(
    "--project",
    default="chromium",
    show_default=True,
    help="Playwright project to run for smoke tests.",
)
def qa_smoke(
    skip_backend: bool,
    skip_frontend: bool,
    live: bool,
    project: str,
) -> None:
    """Run smoke QA gates."""
    repo_root = _default_repo_root()
    env = os.environ.copy()
    if live:
        env["RUN_LIVE_TESTS"] = "1"

    if not skip_backend:
        _run(["uv", "run", "pytest", "-m", "integration"], repo_root / "backend", env)

    if not skip_frontend:
        _run(
            ["bun", "run", "test:e2e", "--", "--grep", "@smoke", "--project", project],
            repo_root / "frontend",
            env,
        )

    success("QA smoke gate passed.")


@command("qa-nightly", help="Run nightly QA gates (full backend + full E2E).")
@click.option("--skip-backend", is_flag=True, help="Skip backend tests.")
@click.option("--skip-frontend", is_flag=True, help="Skip frontend E2E tests.")
@click.option("--live", is_flag=True, help="Enable live CLI integration tests.")
def qa_nightly(
    skip_backend: bool,
    skip_frontend: bool,
    live: bool,
) -> None:
    """Run nightly QA gates."""
    repo_root = _default_repo_root()
    env = os.environ.copy()
    if live:
        env["RUN_LIVE_TESTS"] = "1"

    if not skip_backend:
        _run(["uv", "run", "pytest"], repo_root / "backend", env)

    if not skip_frontend:
        _run(["bun", "run", "test:e2e"], repo_root / "frontend", env)

    success("QA nightly gate passed.")
