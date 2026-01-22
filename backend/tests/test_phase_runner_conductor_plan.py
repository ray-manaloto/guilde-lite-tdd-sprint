"""Tests for PhaseRunner Conductor plan resolution."""

from types import SimpleNamespace

from app.runners.phase_runner import PhaseRunner


def test_phase_runner_reads_conductor_plan(tmp_path):
    plan_path = tmp_path / "tracks" / "track-123" / "plan.md"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("# Plan\n\nSteps", encoding="utf-8")

    sprint = SimpleNamespace(track_id="track-123")
    content = PhaseRunner._resolve_plan_content(sprint, conductor_root=tmp_path)

    assert "# Plan" in content
