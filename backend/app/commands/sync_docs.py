"""Doc sync helper for Conductor tracks."""

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


def _git_lines(cmd: list[str], repo_root: Path) -> list[str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _suggest_docs(changed_files: list[str]) -> list[str]:
    suggestions: set[str] = set()
    for path in changed_files:
        if path.startswith("backend/app/commands") or path.startswith("scripts/"):
            suggestions.update(
                {"docs/spec-workflow.md", "docs/testing.md", "docs/skills.md"}
            )
        if path.startswith("frontend/"):
            suggestions.add("docs/testing.md")
        if path.startswith("conductor/"):
            suggestions.add("docs/sprints.md")
        if path.startswith("docs/"):
            suggestions.add("docs/external-links.md")
    return sorted(suggestions)


@command("sync-docs", help="Create a doc sync report for the active track.")
@click.option("--track-id", help="Conductor track ID", envvar="CONDUCTOR_TRACK_ID")
@click.option(
    "--conductor-root",
    type=click.Path(path_type=Path),
    default=None,
    help="Override Conductor root directory",
)
@click.option("--note", help="Optional note to include in the report.")
def sync_docs(
    track_id: str | None,
    conductor_root: Path | None,
    note: str | None,
) -> None:
    """Generate a documentation sync report."""
    if not track_id:
        error("Missing --track-id (or CONDUCTOR_TRACK_ID).")
        raise SystemExit(1)

    repo_root = _default_repo_root()
    root = conductor_root or _default_conductor_root(repo_root)
    track_dir = root / "tracks" / track_id
    if not track_dir.exists():
        error(f"Track not found: {track_dir}")
        raise SystemExit(1)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    state_dir = track_dir / "artifacts" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    changed_files = _git_lines(["git", "status", "--porcelain"], repo_root)
    changed_paths = [line.split(maxsplit=1)[-1] for line in changed_files]
    suggestions = _suggest_docs(changed_paths)

    markdown = [
        f"# Doc Sync Report {timestamp}",
        f"Track: `{track_id}`",
    ]
    if note:
        markdown.append(f"Note: {note}")
    changed_block = [f"- {path}" for path in changed_paths] or ["- (none)"]
    suggestions_block = [f"- {path}" for path in suggestions] or ["- (none)"]

    markdown.extend(
        [
            "",
            "## Changed Files",
            *changed_block,
            "",
            "## Suggested Docs to Review",
            *suggestions_block,
        ]
    )

    md_path = state_dir / f"{timestamp}-doc-sync.md"
    md_path.write_text("\n".join(markdown), encoding="utf-8")

    payload = {
        "track_id": track_id,
        "timestamp": timestamp,
        "note": note,
        "changed_files": changed_paths,
        "suggested_docs": suggestions,
    }
    json_path = state_dir / f"{timestamp}-doc-sync.state.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    success(f"Doc sync report written: {md_path}")
