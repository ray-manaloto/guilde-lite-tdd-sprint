"""Tests for AgentTddService defaults and judge prompt."""

from types import SimpleNamespace
from uuid import uuid4

from app.services.agent_tdd import AgentTddService


def test_default_subagents_include_openai_and_anthropic():
    """Default subagents should include OpenAI + Anthropic."""
    service = AgentTddService(db=SimpleNamespace())
    subagents = service._resolve_subagents([])
    providers = {agent.provider for agent in subagents}
    assert providers == {"openai", "anthropic"}


def test_build_judge_prompt_includes_criteria_and_user_message():
    """Judge prompt should include helpfulness/correctness and user message."""
    candidates = [
        SimpleNamespace(
            id=uuid4(),
            agent_name="openai",
            provider="openai",
            model_name="openai-responses:gpt-5.2-codex",
            output="candidate output",
        )
    ]
    prompt = AgentTddService._build_judge_prompt("test message", candidates)
    assert "helpfulness" in prompt
    assert "correctness" in prompt
    assert "test message" in prompt


def test_parse_judge_output_formats_rationale():
    """Judge output should fold sub-scores into rationale."""
    candidates = [SimpleNamespace(id=uuid4())]
    output = (
        "{"
        f"\"candidate_id\": \"{candidates[0].id}\", "
        "\"score\": 0.8, "
        "\"helpfulness_score\": 0.9, "
        "\"correctness_score\": 0.7, "
        "\"rationale\": \"solid answer\""
        "}"
    )
    parsed = AgentTddService._parse_judge_output(output, candidates)
    assert parsed is not None
    assert parsed["candidate_id"] == candidates[0].id
    assert parsed["score"] == 0.8
    assert "helpfulness=0.9" in parsed["rationale"]
    assert "correctness=0.7" in parsed["rationale"]


def test_build_decision_state_includes_selected_candidate():
    """Decision state should include selected candidate metadata."""
    candidate_id = uuid4()
    decision = SimpleNamespace(
        id=uuid4(),
        candidate_id=candidate_id,
        model_name="openai-responses:gpt-5.2-codex",
        score=0.9,
        rationale="good",
    )
    candidates = [
        SimpleNamespace(
            id=candidate_id,
            agent_name="openai",
            provider="openai",
            model_name="openai-responses:gpt-5.2-codex",
        )
    ]

    state = AgentTddService._build_decision_state(decision, candidates)
    assert state["candidate_id"] == str(candidate_id)
    assert state["selected_candidate"]["model_name"] == "openai-responses:gpt-5.2-codex"
