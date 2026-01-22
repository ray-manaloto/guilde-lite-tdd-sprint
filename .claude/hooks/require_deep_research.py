#!/usr/bin/env python3
"""Block research workflows unless a deep research artifact exists."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

KEYWORDS = (
    "research",
    "deep research",
    "investigate",
    "benchmark",
    "compare",
    "survey",
    "best practices",
    "sources",
)


def _load_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def _iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def _mentions_research(payload: dict) -> bool:
    combined = " ".join(_iter_strings(payload)).lower()
    return any(keyword in combined for keyword in KEYWORDS)


def _read_active_tracks(tracks_path: Path) -> list[str]:
    if not tracks_path.exists():
        return []
    active_tracks: list[str] = []
    in_active = False
    for line in tracks_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("## Active Tracks"):
            in_active = True
            continue
        if line.strip().startswith("## ") and not line.strip().startswith("## Active Tracks"):
            if in_active:
                break
        if in_active:
            match = re.match(r"- \[[^\]]+\]\s+(\S+)", line.strip())
            if match:
                active_tracks.append(match.group(1))
    return active_tracks


def _most_recent_track(track_ids: list[str], conductor_root: Path) -> str | None:
    if not track_ids:
        return None
    if len(track_ids) == 1:
        return track_ids[0]

    def _aware_min() -> datetime:
        return datetime.min.replace(tzinfo=timezone.utc)

    def _ensure_aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def track_timestamp(track_id: str) -> datetime:
        metadata_path = conductor_root / "tracks" / track_id / "metadata.json"
        if not metadata_path.exists():
            return _aware_min()
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            updated = payload.get("updated") or ""
            return _ensure_aware(datetime.fromisoformat(updated.replace("Z", "+00:00")))
        except (json.JSONDecodeError, ValueError):
            return _aware_min()

    return max(track_ids, key=track_timestamp)


def _has_research_artifact(track_id: str, conductor_root: Path) -> bool:
    track_dir = conductor_root / "tracks" / track_id
    if (track_dir / "research.md").exists():
        return True
    artifacts_dir = track_dir / "artifacts" / "research"
    return artifacts_dir.exists() and any(artifacts_dir.glob("*.md"))


def _any_research_artifact(conductor_root: Path) -> bool:
    tracks_dir = conductor_root / "tracks"
    if not tracks_dir.exists():
        return False
    for track_dir in tracks_dir.iterdir():
        if not track_dir.is_dir():
            continue
        if _has_research_artifact(track_dir.name, conductor_root):
            return True
    return False


def main() -> int:
    payload = _load_payload()
    if not _mentions_research(payload):
        return 0

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    conductor_root = Path(os.environ.get("CONDUCTOR_ROOT", project_dir / "conductor"))
    if not conductor_root.exists():
        return 0

    env_track_id = os.environ.get("CONDUCTOR_TRACK_ID")
    if env_track_id and _has_research_artifact(env_track_id, conductor_root):
        return 0

    track_ids = _read_active_tracks(conductor_root / "tracks.md")
    track_id = _most_recent_track(track_ids, conductor_root)

    if track_id and _has_research_artifact(track_id, conductor_root):
        return 0

    if not track_id and _any_research_artifact(conductor_root):
        return 0

    message = (
        "Deep research artifact missing. Run: "
        "project cmd deep-research --track-id <track> --query '<question>' "
        "or project cmd conductor-plan --track-id <track> --task '<task>'."
    )
    print(message, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
