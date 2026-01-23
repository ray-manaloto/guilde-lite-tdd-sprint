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


@command("qa-smoke", help="Run smoke QA gates (backend TUI/CLI marker only).")
@click.option("--live", is_flag=True, help="Enable live CLI integration tests.")
def qa_smoke(
    live: bool,
) -> None:
    """Run smoke QA gates."""
    repo_root = _default_repo_root()
    env = os.environ.copy()
    if live:
        env["RUN_LIVE_TESTS"] = "1"

    _run(["uv", "run", "alembic", "upgrade", "head"], repo_root / "backend", env)
    _run(["uv", "run", "pytest", "-m", "tui"], repo_root / "backend", env)

    success("QA smoke gate passed.")


@command("qa-nightly", help="Run nightly QA gates (full backend only).")
@click.option("--live", is_flag=True, help="Enable live CLI integration tests.")
def qa_nightly(
    live: bool,
) -> None:
    """Run nightly QA gates."""
    repo_root = _default_repo_root()
    env = os.environ.copy()
    if live:
        env["RUN_LIVE_TESTS"] = "1"

    _run(["uv", "run", "alembic", "upgrade", "head"], repo_root / "backend", env)
    _run(["uv", "run", "pytest"], repo_root / "backend", env)

    success("QA nightly gate passed.")


@command("qa-frontend-e2e", help="Run frontend E2E tests (manual/optional).")
@click.option("--smoke", is_flag=True, help="Run smoke-tagged E2E tests only.")
@click.option("--grep", help="Playwright grep pattern.")
@click.option(
    "--project",
    default=None,
    help="Playwright project to run (defaults to all).",
)
def qa_frontend_e2e(
    smoke: bool,
    grep: str | None,
    project: str | None,
) -> None:
    """Run frontend E2E tests."""
    if smoke and grep:
        raise click.UsageError("Use either --smoke or --grep, not both.")

    if smoke:
        grep = "@smoke"
        if project is None:
            project = "chromium"

    repo_root = _default_repo_root()
    env = os.environ.copy()
    args: list[str] = []
    if grep:
        args.extend(["--grep", grep])
    if project:
        args.extend(["--project", project])

    cmd = ["bun", "run", "test:e2e"]
    if args:
        cmd.extend(["--", *args])

    _run(cmd, repo_root / "frontend", env)
    success("Frontend E2E run completed.")
