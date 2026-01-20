"""Tests for planning interview judge parsing."""

import json

from app.agents.ralph_planner import _parse_planning_judge_output


def test_parse_planning_judge_output_valid():
    output = json.dumps(
        {
            "candidate_key": "openai",
            "score": 0.8,
            "helpfulness_score": 0.9,
            "correctness_score": 0.7,
            "rationale": "Clear questions",
        }
    )
    result = _parse_planning_judge_output(output, {"openai", "anthropic"})
    assert result is not None
    assert result["candidate_key"] == "openai"
    assert "helpfulness=0.9" in result["rationale"]
    assert "correctness=0.7" in result["rationale"]


def test_parse_planning_judge_output_rejects_unknown_candidate():
    output = json.dumps({"candidate_key": "other", "score": 0.5})
    result = _parse_planning_judge_output(output, {"openai", "anthropic"})
    assert result is None
