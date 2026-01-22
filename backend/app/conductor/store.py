"""Conductor file store for spec/plan artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ConductorStore:
    """File-backed store for Conductor track artifacts."""

    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root)

    def ensure_track_dir(self, track_id: str) -> Path:
        track_dir = self.root / "tracks" / track_id
        track_dir.mkdir(parents=True, exist_ok=True)
        return track_dir

    def write_spec(self, track_id: str, content: str) -> Path:
        track_dir = self.ensure_track_dir(track_id)
        spec_path = track_dir / "spec.md"
        spec_path.write_text(content, encoding="utf-8")
        return spec_path

    def write_plan(self, track_id: str, content: str) -> Path:
        track_dir = self.ensure_track_dir(track_id)
        plan_path = track_dir / "plan.md"
        plan_path.write_text(content, encoding="utf-8")
        return plan_path
