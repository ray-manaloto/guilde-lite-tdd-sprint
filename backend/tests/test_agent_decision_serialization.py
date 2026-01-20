"""Tests for agent decision serialization helpers."""

from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.agent_run import AgentDecisionRead


def test_agent_decision_model_dump_json_serializes_datetimes():
    """model_dump(mode='json') should stringify datetimes."""
    decision = AgentDecisionRead(
        id=uuid4(),
        run_id=uuid4(),
        candidate_id=uuid4(),
        score=0.9,
        rationale="ok",
        model_name="openai-responses:gpt-5.2-codex",
        created_at=datetime.now(UTC),
        updated_at=None,
    )
    data = decision.model_dump(mode="json")
    assert isinstance(data["created_at"], str)
