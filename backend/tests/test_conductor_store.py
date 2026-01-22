"""Tests for ConductorStore file writing."""

from app.conductor.store import ConductorStore


def test_store_writes_spec_and_plan(tmp_path):
    store = ConductorStore(root=tmp_path)
    track_id = "track-123"

    spec_path = store.write_spec(track_id, "# Spec\n\nDetails")
    plan_path = store.write_plan(track_id, "# Plan\n\nSteps")

    assert spec_path.read_text(encoding="utf-8") == "# Spec\n\nDetails"
    assert plan_path.read_text(encoding="utf-8") == "# Plan\n\nSteps"
    assert spec_path.parent == plan_path.parent
    assert spec_path.parent.name == track_id
