"""Tests for AgentRunService helpers."""

from types import SimpleNamespace

from app.services.agent_run import AgentRunService


def test_merge_checkpoint_state_includes_history():
    """Checkpoint state should include input history payload."""
    run = SimpleNamespace(
        input_payload={"message": "hello", "history": [{"role": "user", "content": "hi"}]},
        model_config={"provider": "openai", "model": "openai-responses:gpt-5.2-codex"},
    )
    service = AgentRunService(db=SimpleNamespace())

    state = service._merge_checkpoint_state(run, {"label": "candidate"})
    assert "input_payload" in state
    assert state["input_payload"]["history"][0]["content"] == "hi"
