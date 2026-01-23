"""Unit tests for the evaluator system.

Tests cover:
1. EvaluationResult - failed_criteria and blocking_issues properties
2. FeedbackMemory - attempt tracking, context generation, and escalation
3. EvaluatorRegistry - registering and retrieving evaluators by phase
4. Deterministic evaluators - RuffLintEvaluator with clean/dirty code
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.runners.evaluators.deterministic import (
    PytestEvaluator,
    RuffLintEvaluator,
    TypeCheckEvaluator,
)
from app.runners.evaluators.feedback_memory import AttemptRecord, FeedbackMemory
from app.runners.evaluators.protocol import (
    CriterionResult,
    EvaluationCategory,
    EvaluationResult,
)
from app.runners.evaluators.registry import EvaluatorRegistry, create_default_registry


class TestEvaluationResult:
    """Tests for EvaluationResult model."""

    def test_failed_criteria_returns_only_failed(self):
        """Should return only criteria that did not pass."""
        result = EvaluationResult(
            evaluator_name="test_evaluator",
            category=EvaluationCategory.FUNCTIONALITY,
            passed=False,
            score=0.5,
            feedback="Some tests failed",
            criteria=[
                CriterionResult(
                    criterion="test_1",
                    passed=True,
                    score=1.0,
                    message="Test 1 passed",
                ),
                CriterionResult(
                    criterion="test_2",
                    passed=False,
                    score=0.3,
                    message="Test 2 failed",
                ),
                CriterionResult(
                    criterion="test_3",
                    passed=False,
                    score=0.0,
                    message="Test 3 failed critically",
                ),
                CriterionResult(
                    criterion="test_4",
                    passed=True,
                    score=0.9,
                    message="Test 4 passed",
                ),
            ],
        )

        failed = result.failed_criteria

        assert len(failed) == 2
        assert all(not c.passed for c in failed)
        assert failed[0].criterion == "test_2"
        assert failed[1].criterion == "test_3"

    def test_failed_criteria_empty_when_all_pass(self):
        """Should return empty list when all criteria pass."""
        result = EvaluationResult(
            evaluator_name="test_evaluator",
            category=EvaluationCategory.COMPLIANCE,
            passed=True,
            score=1.0,
            feedback="All good",
            criteria=[
                CriterionResult(
                    criterion="lint",
                    passed=True,
                    score=1.0,
                    message="No issues",
                ),
            ],
        )

        assert result.failed_criteria == []

    def test_blocking_issues_filters_by_score(self):
        """Should return messages from failed criteria with score < 0.5."""
        result = EvaluationResult(
            evaluator_name="test_evaluator",
            category=EvaluationCategory.SECURITY,
            passed=False,
            score=0.3,
            feedback="Security issues found",
            criteria=[
                CriterionResult(
                    criterion="sql_injection",
                    passed=False,
                    score=0.0,
                    message="Critical: SQL injection vulnerability",
                ),
                CriterionResult(
                    criterion="xss",
                    passed=False,
                    score=0.6,  # Above 0.5, should NOT be blocking
                    message="Minor XSS concern",
                ),
                CriterionResult(
                    criterion="auth",
                    passed=False,
                    score=0.2,
                    message="Blocking: Auth bypass possible",
                ),
            ],
        )

        blocking = result.blocking_issues

        assert len(blocking) == 2
        assert "SQL injection" in blocking[0]
        assert "Auth bypass" in blocking[1]

    def test_blocking_issues_empty_when_no_low_scores(self):
        """Should return empty list when no criteria have score < 0.5."""
        result = EvaluationResult(
            evaluator_name="test_evaluator",
            category=EvaluationCategory.MAINTAINABILITY,
            passed=False,
            score=0.7,
            feedback="Could be better",
            criteria=[
                CriterionResult(
                    criterion="complexity",
                    passed=False,
                    score=0.6,  # Above 0.5
                    message="Code could be simpler",
                ),
            ],
        )

        assert result.blocking_issues == []

    def test_evaluation_result_with_empty_criteria(self):
        """Should handle empty criteria list gracefully."""
        result = EvaluationResult(
            evaluator_name="test_evaluator",
            category=EvaluationCategory.TEST_COVERAGE,
            passed=True,
            score=1.0,
            feedback="No criteria to evaluate",
        )

        assert result.failed_criteria == []
        assert result.blocking_issues == []


class TestAttemptRecord:
    """Tests for AttemptRecord dataclass."""

    def test_duration_ms_calculated_correctly(self):
        """Should calculate duration in milliseconds."""
        start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 1, 12, 0, 5, 500000, tzinfo=UTC)  # 5.5 seconds later

        attempt = AttemptRecord(
            attempt_number=1,
            started_at=start,
            completed_at=end,
        )

        assert attempt.duration_ms == 5500

    def test_duration_ms_none_when_not_completed(self):
        """Should return None when attempt not completed."""
        attempt = AttemptRecord(
            attempt_number=1,
            started_at=datetime.now(UTC),
            completed_at=None,
        )

        assert attempt.duration_ms is None

    def test_passed_when_all_evaluations_pass(self):
        """Should return True when all evaluations pass."""
        attempt = AttemptRecord(
            attempt_number=1,
            started_at=datetime.now(UTC),
            evaluation_results=[
                EvaluationResult(
                    evaluator_name="eval1",
                    category=EvaluationCategory.FUNCTIONALITY,
                    passed=True,
                    score=1.0,
                    feedback="OK",
                ),
                EvaluationResult(
                    evaluator_name="eval2",
                    category=EvaluationCategory.COMPLIANCE,
                    passed=True,
                    score=0.9,
                    feedback="OK",
                ),
            ],
        )

        assert attempt.passed is True

    def test_passed_false_when_any_evaluation_fails(self):
        """Should return False when any evaluation fails."""
        attempt = AttemptRecord(
            attempt_number=1,
            started_at=datetime.now(UTC),
            evaluation_results=[
                EvaluationResult(
                    evaluator_name="eval1",
                    category=EvaluationCategory.FUNCTIONALITY,
                    passed=True,
                    score=1.0,
                    feedback="OK",
                ),
                EvaluationResult(
                    evaluator_name="eval2",
                    category=EvaluationCategory.COMPLIANCE,
                    passed=False,
                    score=0.3,
                    feedback="Failed",
                ),
            ],
        )

        assert attempt.passed is False

    def test_aggregate_score_averages_all_scores(self):
        """Should calculate average of all evaluation scores."""
        attempt = AttemptRecord(
            attempt_number=1,
            started_at=datetime.now(UTC),
            evaluation_results=[
                EvaluationResult(
                    evaluator_name="eval1",
                    category=EvaluationCategory.FUNCTIONALITY,
                    passed=True,
                    score=1.0,
                    feedback="OK",
                ),
                EvaluationResult(
                    evaluator_name="eval2",
                    category=EvaluationCategory.COMPLIANCE,
                    passed=False,
                    score=0.5,
                    feedback="Partial",
                ),
            ],
        )

        assert attempt.aggregate_score == 0.75

    def test_aggregate_score_zero_when_no_results(self):
        """Should return 0.0 when no evaluation results."""
        attempt = AttemptRecord(
            attempt_number=1,
            started_at=datetime.now(UTC),
        )

        assert attempt.aggregate_score == 0.0

    def test_get_failed_feedback_returns_only_failed(self):
        """Should return feedback only from failed evaluations."""
        attempt = AttemptRecord(
            attempt_number=1,
            started_at=datetime.now(UTC),
            evaluation_results=[
                EvaluationResult(
                    evaluator_name="eval1",
                    category=EvaluationCategory.FUNCTIONALITY,
                    passed=True,
                    score=1.0,
                    feedback="Tests pass",
                ),
                EvaluationResult(
                    evaluator_name="eval2",
                    category=EvaluationCategory.COMPLIANCE,
                    passed=False,
                    score=0.3,
                    feedback="Lint errors found",
                ),
            ],
        )

        feedback = attempt.get_failed_feedback()

        assert len(feedback) == 1
        assert feedback[0] == "Lint errors found"


class TestFeedbackMemory:
    """Tests for FeedbackMemory class."""

    def test_current_attempt_starts_at_one(self):
        """Should return 1 for first attempt."""
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Implement feature X",
        )

        assert memory.current_attempt == 1

    def test_current_attempt_increments_after_add(self):
        """Should increment after adding an attempt."""
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Implement feature X",
        )

        memory.add_attempt(
            phase_output="some output",
            evaluation_results=[
                EvaluationResult(
                    evaluator_name="test",
                    category=EvaluationCategory.FUNCTIONALITY,
                    passed=False,
                    score=0.5,
                    feedback="Failed",
                )
            ],
        )

        assert memory.current_attempt == 2

    def test_can_retry_true_when_under_max_attempts(self):
        """Should allow retry when under max attempts."""
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Implement feature X",
            max_attempts=3,
        )

        assert memory.can_retry is True

    def test_can_retry_false_when_at_max_attempts(self):
        """Should not allow retry when at max attempts."""
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Implement feature X",
            max_attempts=2,
        )

        # Add 2 attempts
        for _ in range(2):
            memory.add_attempt(
                phase_output="output",
                evaluation_results=[
                    EvaluationResult(
                        evaluator_name="test",
                        category=EvaluationCategory.FUNCTIONALITY,
                        passed=False,
                        score=0.5,
                        feedback="Failed",
                    )
                ],
            )

        assert memory.can_retry is False

    def test_can_retry_false_when_escalated(self):
        """Should not allow retry when escalated."""
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Implement feature X",
        )

        memory.escalate("Cannot fix automatically")

        assert memory.can_retry is False
        assert memory.escalated is True
        assert memory.escalation_reason == "Cannot fix automatically"

    def test_latest_attempt_returns_most_recent(self):
        """Should return the most recently added attempt."""
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Implement feature X",
        )

        memory.add_attempt(
            phase_output="first",
            evaluation_results=[],
        )
        memory.add_attempt(
            phase_output="second",
            evaluation_results=[],
        )

        assert memory.latest_attempt is not None
        assert memory.latest_attempt.phase_output == "second"
        assert memory.latest_attempt.attempt_number == 2

    def test_latest_attempt_none_when_no_attempts(self):
        """Should return None when no attempts recorded."""
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Implement feature X",
        )

        assert memory.latest_attempt is None

    def test_add_attempt_truncates_long_output(self):
        """Should truncate phase output to 2000 chars."""
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Implement feature X",
        )

        long_output = "x" * 5000

        memory.add_attempt(
            phase_output=long_output,
            evaluation_results=[],
        )

        assert len(memory.latest_attempt.phase_output) == 2000

    def test_add_attempt_tracks_recurring_issues(self):
        """Should accumulate recurring issues from suggestions."""
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Implement feature X",
        )

        memory.add_attempt(
            phase_output="output",
            evaluation_results=[
                EvaluationResult(
                    evaluator_name="lint",
                    category=EvaluationCategory.COMPLIANCE,
                    passed=False,
                    score=0.5,
                    feedback="Lint errors",
                    suggestions=["Fix import order", "Remove unused variable"],
                )
            ],
        )

        assert "Fix import order" in memory.accumulated_insights["recurring_issues"]
        assert "Remove unused variable" in memory.accumulated_insights["recurring_issues"]

    def test_get_optimization_context_attempt_1(self):
        """Should return basic context for first attempt."""
        sprint_id = uuid4()
        memory = FeedbackMemory(
            sprint_id=sprint_id,
            phase="coding",
            original_goal="Implement feature X",
        )

        context = memory.get_optimization_context()

        assert context["sprint_id"] == str(sprint_id)
        assert context["phase"] == "coding"
        assert context["original_goal"] == "Implement feature X"
        assert context["attempt_number"] == 1
        assert "previous_feedback" not in context

    def test_get_optimization_context_attempt_2(self):
        """Should include previous feedback for second attempt."""
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Implement feature X",
        )

        # First attempt fails
        memory.add_attempt(
            phase_output="output",
            evaluation_results=[
                EvaluationResult(
                    evaluator_name="test",
                    category=EvaluationCategory.FUNCTIONALITY,
                    passed=False,
                    score=0.6,
                    feedback="Tests failed: missing edge case",
                )
            ],
        )

        context = memory.get_optimization_context()

        assert context["attempt_number"] == 2
        assert "previous_feedback" in context
        assert "Tests failed: missing edge case" in context["previous_feedback"]
        assert context["previous_score"] == 0.6

    def test_get_optimization_context_attempt_3_full_history(self):
        """Should include full history and analysis for third attempt."""
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Implement feature X",
        )

        # Two failed attempts
        memory.add_attempt(
            phase_output="first output",
            evaluation_results=[
                EvaluationResult(
                    evaluator_name="test",
                    category=EvaluationCategory.FUNCTIONALITY,
                    passed=False,
                    score=0.4,
                    feedback="Tests failed",
                    suggestions=["Fix assertion"],
                )
            ],
        )
        memory.add_attempt(
            phase_output="second output",
            evaluation_results=[
                EvaluationResult(
                    evaluator_name="test",
                    category=EvaluationCategory.FUNCTIONALITY,
                    passed=False,
                    score=0.6,
                    feedback="Still failing",
                    suggestions=["Fix edge case"],
                )
            ],
        )

        context = memory.get_optimization_context()

        assert context["attempt_number"] == 3
        assert "attempt_history" in context
        assert len(context["attempt_history"]) == 2
        assert "recurring_issues" in context
        assert "analysis" in context
        assert "Improving" in context["analysis"]  # Score went from 0.4 to 0.6

    def test_get_summary_for_prompt_empty_when_no_attempts(self):
        """Should return empty string when no attempts."""
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Implement feature X",
        )

        assert memory.get_summary_for_prompt() == ""

    def test_get_summary_for_prompt_includes_all_attempts(self):
        """Should include summary of all attempts."""
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Implement feature X",
            max_attempts=3,
        )

        memory.add_attempt(
            phase_output="output",
            evaluation_results=[
                EvaluationResult(
                    evaluator_name="test",
                    category=EvaluationCategory.FUNCTIONALITY,
                    passed=False,
                    score=0.5,
                    feedback="Test failed",
                )
            ],
        )

        summary = memory.get_summary_for_prompt()

        assert "Previous Attempts for coding Phase" in summary
        assert "attempt 2 of 3" in summary
        assert "Attempt 1" in summary
        assert "Score: 0.50" in summary
        assert "FAILED" in summary
        assert "Test failed" in summary

    def test_get_summary_shows_critical_warning_on_final_attempt(self):
        """Should show CRITICAL warning on final attempt."""
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Implement feature X",
            max_attempts=2,
        )

        memory.add_attempt(
            phase_output="output",
            evaluation_results=[
                EvaluationResult(
                    evaluator_name="test",
                    category=EvaluationCategory.FUNCTIONALITY,
                    passed=False,
                    score=0.5,
                    feedback="Test failed",
                )
            ],
        )

        summary = memory.get_summary_for_prompt()

        assert "CRITICAL" in summary
        assert "FINAL attempt" in summary

    def test_to_dict_serialization(self):
        """Should serialize memory to dictionary."""
        sprint_id = uuid4()
        memory = FeedbackMemory(
            sprint_id=sprint_id,
            phase="coding",
            original_goal="Implement feature X",
        )

        memory.add_attempt(
            phase_output="output",
            evaluation_results=[
                EvaluationResult(
                    evaluator_name="test",
                    category=EvaluationCategory.FUNCTIONALITY,
                    passed=True,
                    score=1.0,
                    feedback="All good",
                )
            ],
            trace_id="trace-123",
        )

        data = memory.to_dict()

        assert data["sprint_id"] == str(sprint_id)
        assert data["phase"] == "coding"
        assert data["current_attempt"] == 2
        assert len(data["attempts"]) == 1
        assert data["attempts"][0]["trace_id"] == "trace-123"
        assert data["attempts"][0]["passed"] is True
        assert data["escalated"] is False


class TestEvaluatorRegistry:
    """Tests for EvaluatorRegistry class."""

    def _create_mock_evaluator(
        self, name: str, is_deterministic: bool = True
    ) -> MagicMock:
        """Create a mock evaluator for testing."""
        evaluator = MagicMock()
        evaluator.name = name
        evaluator.is_deterministic = is_deterministic
        evaluator.category = EvaluationCategory.COMPLIANCE
        return evaluator

    def test_register_to_specific_phases(self):
        """Should register evaluator to specific phases."""
        registry = EvaluatorRegistry()
        evaluator = self._create_mock_evaluator("test_eval")

        registry.register(evaluator, phases=["coding", "verification"])

        assert len(registry.get_evaluators("coding")) == 1
        assert len(registry.get_evaluators("verification")) == 1
        assert len(registry.get_evaluators("other")) == 0

    def test_register_global_evaluator(self):
        """Should register global evaluator for all phases."""
        registry = EvaluatorRegistry()
        global_eval = self._create_mock_evaluator("global_eval")

        registry.register(global_eval, phases=None)

        assert len(registry.get_evaluators("coding")) == 1
        assert len(registry.get_evaluators("verification")) == 1
        assert len(registry.get_evaluators("any_phase")) == 1

    def test_get_evaluators_combines_global_and_phase(self):
        """Should return both global and phase-specific evaluators."""
        registry = EvaluatorRegistry()
        global_eval = self._create_mock_evaluator("global")
        coding_eval = self._create_mock_evaluator("coding_only")

        registry.register(global_eval)  # Global
        registry.register(coding_eval, phases=["coding"])

        coding_evaluators = registry.get_evaluators("coding")
        other_evaluators = registry.get_evaluators("other")

        assert len(coding_evaluators) == 2
        assert len(other_evaluators) == 1
        assert coding_evaluators[0].name == "global"
        assert coding_evaluators[1].name == "coding_only"

    def test_get_deterministic_evaluators_filters_correctly(self):
        """Should return only deterministic evaluators."""
        registry = EvaluatorRegistry()
        deterministic = self._create_mock_evaluator("det", is_deterministic=True)
        llm_based = self._create_mock_evaluator("llm", is_deterministic=False)

        registry.register(deterministic)
        registry.register(llm_based)

        det_evals = registry.get_deterministic_evaluators("any")

        assert len(det_evals) == 1
        assert det_evals[0].name == "det"

    def test_get_llm_evaluators_filters_correctly(self):
        """Should return only LLM-based evaluators."""
        registry = EvaluatorRegistry()
        deterministic = self._create_mock_evaluator("det", is_deterministic=True)
        llm_based = self._create_mock_evaluator("llm", is_deterministic=False)

        registry.register(deterministic)
        registry.register(llm_based)

        llm_evals = registry.get_llm_evaluators("any")

        assert len(llm_evals) == 1
        assert llm_evals[0].name == "llm"

    def test_create_default_registry(self):
        """Should create registry with default evaluators."""
        registry = create_default_registry()

        # RuffLintEvaluator is global
        assert any(e.name == "ruff_lint" for e in registry.get_evaluators("any_phase"))

        # PytestEvaluator is for verification and coding
        verification_evals = registry.get_evaluators("verification")
        assert any(e.name == "pytest" for e in verification_evals)

        coding_evals = registry.get_evaluators("coding")
        assert any(e.name == "pytest" for e in coding_evals)
        assert any(e.name == "type_check" for e in coding_evals)


class TestRuffLintEvaluator:
    """Tests for RuffLintEvaluator deterministic evaluator."""

    @pytest.fixture
    def evaluator(self) -> RuffLintEvaluator:
        return RuffLintEvaluator()

    def test_evaluator_properties(self, evaluator: RuffLintEvaluator):
        """Should have correct properties."""
        assert evaluator.name == "ruff_lint"
        assert evaluator.category == EvaluationCategory.COMPLIANCE
        assert evaluator.is_deterministic is True

    @pytest.mark.anyio
    async def test_evaluate_no_workspace(self, evaluator: RuffLintEvaluator):
        """Should pass when no workspace provided."""
        result = await evaluator.evaluate(
            phase="coding",
            output="",
            context={},
        )

        assert result.passed is True
        assert result.score == 1.0
        assert "No workspace to lint" in result.feedback

    @pytest.mark.anyio
    async def test_evaluate_workspace_not_found(self, evaluator: RuffLintEvaluator):
        """Should fail when workspace does not exist."""
        result = await evaluator.evaluate(
            phase="coding",
            output="",
            context={"workspace_ref": "/nonexistent/path"},
        )

        assert result.passed is False
        assert result.score == 0.0
        assert "not found" in result.feedback

    @pytest.mark.anyio
    async def test_evaluate_clean_code(self, evaluator: RuffLintEvaluator):
        """Should pass for clean Python code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a clean Python file
            clean_code = '''"""Clean module."""


def hello(name: str) -> str:
    """Return greeting."""
    return f"Hello, {name}!"
'''
            code_file = Path(tmpdir) / "clean.py"
            code_file.write_text(clean_code)

            result = await evaluator.evaluate(
                phase="coding",
                output="",
                context={"workspace_ref": tmpdir},
            )

            assert result.passed is True
            assert result.score == 1.0
            assert "passes all lint checks" in result.feedback

    @pytest.mark.anyio
    async def test_evaluate_dirty_code(self, evaluator: RuffLintEvaluator):
        """Should fail for code with lint errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Python file with lint errors
            dirty_code = """import os
import sys
import json
x=1
def bad():
    pass
"""
            code_file = Path(tmpdir) / "dirty.py"
            code_file.write_text(dirty_code)

            result = await evaluator.evaluate(
                phase="coding",
                output="",
                context={"workspace_ref": tmpdir},
            )

            assert result.passed is False
            assert result.score < 1.0
            assert "lint error" in result.feedback.lower()
            assert len(result.suggestions) > 0


class TestPytestEvaluator:
    """Tests for PytestEvaluator deterministic evaluator."""

    @pytest.fixture
    def evaluator(self) -> PytestEvaluator:
        return PytestEvaluator()

    def test_evaluator_properties(self, evaluator: PytestEvaluator):
        """Should have correct properties."""
        assert evaluator.name == "pytest"
        assert evaluator.category == EvaluationCategory.FUNCTIONALITY
        assert evaluator.is_deterministic is True

    @pytest.mark.anyio
    async def test_evaluate_no_workspace(self, evaluator: PytestEvaluator):
        """Should pass when no workspace provided."""
        result = await evaluator.evaluate(
            phase="verification",
            output="",
            context={},
        )

        assert result.passed is True
        assert "No workspace to test" in result.feedback


class TestTypeCheckEvaluator:
    """Tests for TypeCheckEvaluator deterministic evaluator."""

    @pytest.fixture
    def evaluator(self) -> TypeCheckEvaluator:
        return TypeCheckEvaluator()

    def test_evaluator_properties(self, evaluator: TypeCheckEvaluator):
        """Should have correct properties."""
        assert evaluator.name == "type_check"
        assert evaluator.category == EvaluationCategory.COMPLIANCE
        assert evaluator.is_deterministic is True

    @pytest.mark.anyio
    async def test_evaluate_no_workspace(self, evaluator: TypeCheckEvaluator):
        """Should pass when no workspace provided."""
        result = await evaluator.evaluate(
            phase="coding",
            output="",
            context={},
        )

        assert result.passed is True
        assert "No workspace to type check" in result.feedback
