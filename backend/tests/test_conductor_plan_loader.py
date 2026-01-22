"""Tests for loading Conductor plan files."""

from pathlib import Path

import pytest

from app.conductor.plan_loader import load_plan


def test_load_plan_reads_conductor_plan(tmp_path):
    plan_path = tmp_path / "tracks" / "track-xyz" / "plan.md"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("# Plan\n\nDo work", encoding="utf-8")

    content = load_plan("track-xyz", tmp_path)

    assert "# Plan" in content


def test_load_plan_raises_when_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_plan("missing-track", tmp_path)
