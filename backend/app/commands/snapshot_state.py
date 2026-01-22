"""Snapshot current workflow state for recovery."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import click

from app.commands import command, error, success


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_conductor_root(repo_root: Path) -> Path:
    return repo_root / "conductor"


def _run_git(cmd: list[str], repo_root: Path) -> str:
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return "git not available"
    output = result.stdout.strip()
    if output:
        return output
    return result.stderr.strip() or "no output"


@command("snapshot-state", help="Write a recovery snapshot for the active track.")
@click.option("--track-id", help="Conductor track ID", envvar="CONDUCTOR_TRACK_ID")
@click.option(
    "--conductor-root",
    type=click.Path(path_type=Path),
    default=None,
    help="Override Conductor root directory",
)
@click.option("--note", help="Optional note to include in the snapshot.")
def snapshot_state(
    track_id: str | None,
    conductor_root: Path | None,
    note: str | None,
) -> None:
    """Capture a recovery snapshot for the active Conductor track."""
    if not track_id:
        error("Missing --track-id (or CONDUCTOR_TRACK_ID).")
        raise SystemExit(1)

    repo_root = _default_repo_root()
    root = conductor_root or _default_conductor_root(repo_root)
    track_dir = root / "tracks" / track_id
    if not track_dir.exists():
        error(f"Track not found: {track_dir}")
        raise SystemExit(1)

    state_dir = track_dir / "artifacts" / "state"
    logs_dir = track_dir / "artifacts" / "logs"
    state_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    git_status = _run_git(["git", "status", "-sb"], repo_root)
    git_diff = _run_git(["git", "diff", "--stat"], repo_root)

    plan_status = None
    plan_path = track_dir / "plan.md"
    if plan_path.exists():
        for line in plan_path.read_text(encoding="utf-8").splitlines()[:20]:
            if line.lower().startswith("status:"):
                plan_status = line.split(":", 1)[1].strip()
                break

    markdown = [
        f"# Snapshot {timestamp}",
        f"Track: `{track_id}`",
    ]
    if note:
        markdown.append(f"Note: {note}")
    if plan_status:
        markdown.append(f"Plan Status: {plan_status}")
    markdown.extend(
        [
            "",
            "## Git Status",
            "```",
            git_status,
            "```",
            "",
            "## Git Diff Summary",
            "```",
            git_diff,
            "```",
        ]
    )

    md_path = state_dir / f"{timestamp}.md"
    md_path.write_text("\n".join(markdown), encoding="utf-8")

    payload = {
        "track_id": track_id,
        "timestamp": timestamp,
        "note": note,
        "plan_status": plan_status,
        "git_status": git_status,
        "git_diff_stat": git_diff,
    }
    json_path = state_dir / f"{timestamp}.state.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    log_path = logs_dir / f"{timestamp}.md"
    log_path.write_text("\n".join(markdown), encoding="utf-8")

    success(f"Snapshot written: {md_path}")
