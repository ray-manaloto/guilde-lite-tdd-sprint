"""Codex guard command for Conductor workflow enforcement."""

from __future__ import annotations

import os
import re
from pathlib import Path

import click

from app.commands import command, error, success

_STATUS_PATTERN = re.compile(r"^Status:\\s*(?P<status>\\S+)", re.IGNORECASE)


def _default_conductor_root() -> Path:
    return Path(__file__).resolve().parents[3] / "conductor"


def _read_plan_status(plan_path: Path) -> str | None:
    if not plan_path.exists():
        return None
    for line in plan_path.read_text(encoding="utf-8").splitlines()[:20]:
        match = _STATUS_PATTERN.match(line.strip())
        if match:
            return match.group("status").lower()
    return None


def _verify_completed(plan_path: Path, verify_id: str) -> bool | None:
    if not plan_path.exists():
        return None
    pattern = re.compile(
        rf"^\\s*-\\s*\\[(?P<mark>[^\\]])\\].*Verify\\s+{re.escape(verify_id)}\\b",
        re.IGNORECASE,
    )
    for line in plan_path.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if not match:
            continue
        mark = match.group("mark").strip().lower()
        return mark == "x"
    return None


@command("codex-guard", help="Validate Conductor workflow prerequisites.")
@click.option("--track-id", help="Conductor track ID", envvar="CONDUCTOR_TRACK_ID")
@click.option(
    "--conductor-root",
    type=click.Path(path_type=Path),
    default=None,
    help="Override Conductor root directory",
)
@click.option(
    "--require-research/--skip-research",
    default=True,
    show_default=True,
    help="Require deep research artifact",
)
@click.option(
    "--require-approved-plan/--skip-plan-approval",
    default=True,
    show_default=True,
    help="Require plan approval status",
)
@click.option(
    "--verify",
    multiple=True,
    help="Require Verify <id> to be completed (e.g. --verify 2.1).",
)
def codex_guard(
    track_id: str | None,
    conductor_root: Path | None,
    require_research: bool,
    require_approved_plan: bool,
    verify: tuple[str, ...],
) -> None:
    """Run guard checks before Codex execution."""
    if not track_id:
        error("Missing --track-id (or CONDUCTOR_TRACK_ID).")
        raise SystemExit(1)

    root = conductor_root or _default_conductor_root()
    track_dir = root / "tracks" / track_id
    spec_path = track_dir / "spec.md"
    plan_path = track_dir / "plan.md"
    research_path = track_dir / "research.md"

    issues: list[str] = []

    if not track_dir.exists():
        issues.append(f"Track not found: {track_dir}")
    if not spec_path.exists():
        issues.append(f"Missing spec: {spec_path}")
    if not plan_path.exists():
        issues.append(f"Missing plan: {plan_path}")

    if require_research and not research_path.exists():
        issues.append(f"Missing research digest: {research_path}")

    if require_approved_plan:
        status = _read_plan_status(plan_path)
        if status != "approved":
            issues.append(
                f"Plan not approved (Status: {status or 'missing'}). "
                "Set plan header to 'Status: approved'."
            )

    for verify_id in verify:
        completed = _verify_completed(plan_path, verify_id)
        if completed is None:
            issues.append(f"Verify {verify_id} not found in plan.")
        elif not completed:
            issues.append(f"Verify {verify_id} not completed.")

    if issues:
        for issue in issues:
            error(issue)
        raise SystemExit(1)

    success("Codex guard checks passed.")
