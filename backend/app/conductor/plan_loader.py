"""Load Conductor plan files."""

from __future__ import annotations

from pathlib import Path


def load_plan(track_id: str, conductor_root: Path) -> str:
    plan_path = Path(conductor_root) / "tracks" / track_id / "plan.md"
    if not plan_path.exists():
        raise FileNotFoundError(f"Conductor plan not found: {plan_path}")
    return plan_path.read_text(encoding="utf-8")
