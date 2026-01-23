# Evaluator-Optimizer Architecture for PhaseRunner

**Version:** 1.0
**Date:** 2026-01-22
**Author:** Software Architect Agent
**Status:** Proposed

---

## Executive Summary

This document defines the architecture for integrating an Evaluator-Optimizer pattern into the PhaseRunner, enabling structured evaluation of phase outputs with feedback-driven retry loops. Based on research findings from Phase 1 (see `docs/research/phase1-requirements-summary.md`), this design implements:

1. **Evaluator Interface** - Protocol/ABC for pluggable evaluation functions
2. **EvaluationResult** - Pydantic model for standardized evaluation output
3. **FeedbackMemory** - Data structure for retry history and context accumulation
4. **PhaseRunner Integration** - `evaluate_phase_output()` and `optimize_and_retry()` methods

---

## 1. Architecture Overview

### 1.1 High-Level Class Diagram

```
+------------------+       +---------------------+       +------------------+
|   PhaseRunner    |------>|  EvaluatorRegistry  |------>|    Evaluator     |
+------------------+       +---------------------+       |    (Protocol)    |
| - tracker        |       | - evaluators: dict  |       +------------------+
| - feedback_memory|       | + get(phase, type)  |       | + evaluate()     |
| + run_phase()    |       | + register()        |       | + name: str      |
| + evaluate()     |       +---------------------+       | + category: str  |
| + optimize()     |                                     +------------------+
+------------------+                                              ^
        |                                                         |
        v                                         +---------------+---------------+
+------------------+                              |               |               |
| FeedbackMemory   |                   +----------+----+ +---------+-----+ +------+--------+
+------------------+                   | CodeEvaluator | | TestEvaluator | | LLMEvaluator  |
| - attempts: list |                   | (Deterministic)| | (Deterministic)| | (Subjective) |
| - context: dict  |                   +---------------+ +---------------+ +---------------+
| + add_attempt()  |
| + get_context()  |                   +------------------+
| + get_summary()  |                   | EvaluationResult |
+------------------+                   +------------------+
                                       | - passed: bool   |
                                       | - score: float   |
                                       | - feedback: str  |
                                       | - category: str  |
                                       | - criteria: list |
                                       | - suggestions: [] |
                                       +------------------+
```

### 1.2 Sequence Diagram: Retry Flow with Evaluation

```
                                        Evaluator-Optimizer Retry Flow
+----------+    +-----------+    +----------+    +-----------+    +---------------+
|PhaseRunner|   |AgentTDD   |    |Evaluator |    |Optimizer  |    |FeedbackMemory |
+----+-----+    +-----+-----+    +----+-----+    +-----+-----+    +-------+-------+
     |                |               |               |                   |
     | run_phase()    |               |               |                   |
     |--------------->|               |               |                   |
     |                | execute()     |               |                   |
     |                |-------------->|               |                   |
     |                |    result     |               |                   |
     |<---------------|               |               |                   |
     |                |               |               |                   |
     | evaluate_phase_output(result)  |               |                   |
     |------------------------------>||               |                   |
     |                               || evaluate()    |                   |
     |                               ||-------------->|                   |
     |                               ||  EvalResult   |                   |
     |<------------------------------||               |                   |
     |                |               |               |                   |
     | [if !passed && attempt < 3]   |               |                   |
     |                |               |               |                   |
     | add_attempt(result, eval)     |               |                   |
     |------------------------------------------------------------------>|
     |                |               |               |                   |
     | get_optimization_context()    |               |                   |
     |------------------------------------------------------------------>|
     |                |               |               |    context        |
     |<------------------------------------------------------------------|
     |                |               |               |                   |
     | optimize_and_retry(context)   |               |                   |
     |---------------------------------------------->|                   |
     |                |               |               | generate_prompt() |
     |                |               |               |------------------>|
     |                |               |               |   optimized_prompt|
     |<----------------------------------------------|                   |
     |                |               |               |                   |
     | execute(optimized_prompt)     |               |                   |
     |--------------->|               |               |                   |
     |                |               |               |                   |
     | [Loop: max 3 retries]         |               |                   |
     |                |               |               |                   |
     | [if attempt >= 3 && !passed]  |               |                   |
     |                |               |               |                   |
     | escalate_to_human()           |               |                   |
     |---X            |               |               |                   |
```

---

## 2. Component Specifications

### 2.1 Evaluator Interface (Protocol)

The Evaluator interface defines a contract for all evaluation functions, supporting both deterministic (code-based) and LLM-based evaluators.

```python
# File: backend/app/runners/evaluators/protocol.py

from abc import abstractmethod
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class EvaluationCategory(StrEnum):
    """Categories for evaluation criteria."""

    FUNCTIONALITY = "functionality"      # Does the code work?
    CORRECTNESS = "correctness"          # Does it produce correct output?
    SECURITY = "security"                # Are there security vulnerabilities?
    PERFORMANCE = "performance"          # Does it meet performance requirements?
    MAINTAINABILITY = "maintainability"  # Is the code maintainable?
    COMPLIANCE = "compliance"            # Does it follow standards/patterns?
    TEST_COVERAGE = "test_coverage"      # Are tests adequate?


class CriterionResult(BaseModel):
    """Result for a single evaluation criterion."""

    criterion: str = Field(..., description="Name of the criterion evaluated")
    passed: bool = Field(..., description="Whether this criterion passed")
    score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score from 0.0 to 1.0"
    )
    message: str = Field(default="", description="Explanation of the result")
    evidence: str | None = Field(
        default=None,
        description="Supporting evidence (e.g., test output, lint errors)"
    )


class EvaluationResult(BaseModel):
    """Standardized output from any evaluator."""

    evaluator_name: str = Field(..., description="Name of the evaluator that produced this result")
    category: EvaluationCategory = Field(..., description="Category of evaluation")
    passed: bool = Field(..., description="Overall pass/fail status")
    score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Aggregate score from 0.0 (fail) to 1.0 (perfect)"
    )
    feedback: str = Field(..., description="Human-readable feedback for the agent")
    criteria: list[CriterionResult] = Field(
        default_factory=list,
        description="Individual criterion results"
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Specific suggestions for improvement"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional evaluator-specific metadata"
    )

    @property
    def failed_criteria(self) -> list[CriterionResult]:
        """Get criteria that failed."""
        return [c for c in self.criteria if not c.passed]

    @property
    def blocking_issues(self) -> list[str]:
        """Get blocking issues that must be fixed."""
        return [c.message for c in self.failed_criteria if c.score < 0.5]


@runtime_checkable
class Evaluator(Protocol):
    """Protocol for phase output evaluators.

    Evaluators can be:
    - Deterministic: Code-based checks (lint, tests, type checking)
    - LLM-based: Subjective quality assessment

    All evaluators return standardized EvaluationResult.
    """

    @property
    def name(self) -> str:
        """Unique name for this evaluator."""
        ...

    @property
    def category(self) -> EvaluationCategory:
        """Category of evaluation this performs."""
        ...

    @property
    def is_deterministic(self) -> bool:
        """Whether this evaluator uses deterministic (non-LLM) checks."""
        ...

    @abstractmethod
    async def evaluate(
        self,
        phase: str,
        output: str,
        context: dict,
    ) -> EvaluationResult:
        """Evaluate phase output.

        Args:
            phase: Name of the phase being evaluated (e.g., "coding", "verification")
            output: The output from the phase to evaluate
            context: Additional context (workspace_ref, goal, previous feedback, etc.)

        Returns:
            EvaluationResult with pass/fail, score, and feedback
        """
        ...
```

### 2.2 EvaluationResult Schema

The EvaluationResult is designed to integrate with existing workflow schemas.

```python
# File: backend/app/schemas/evaluation.py

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema


class EvaluationCategory(StrEnum):
    """Categories for evaluation criteria."""

    FUNCTIONALITY = "functionality"
    CORRECTNESS = "correctness"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    COMPLIANCE = "compliance"
    TEST_COVERAGE = "test_coverage"


class CriterionResultSchema(BaseSchema):
    """Schema for a single evaluation criterion result."""

    criterion: str
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    message: str = ""
    evidence: str | None = None


class EvaluationResultSchema(BaseSchema):
    """Schema for evaluation results (API response)."""

    evaluator_name: str
    category: EvaluationCategory
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    feedback: str
    criteria: list[CriterionResultSchema] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    evaluated_at: datetime | None = None
    duration_ms: int | None = None


class PhaseEvaluationSummary(BaseSchema):
    """Summary of all evaluations for a phase."""

    phase: str
    attempt: int
    overall_passed: bool
    overall_score: float = Field(ge=0.0, le=1.0)
    evaluations: list[EvaluationResultSchema] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)

    @property
    def can_proceed(self) -> bool:
        """Whether the phase can proceed to the next stage."""
        return self.overall_passed and len(self.blocking_issues) == 0


class AttemptRecord(BaseSchema):
    """Record of a single retry attempt."""

    attempt_number: int
    started_at: datetime
    completed_at: datetime | None = None
    output_summary: str = ""
    evaluation: PhaseEvaluationSummary | None = None
    optimization_applied: str | None = None
    trace_id: str | None = None


class FeedbackMemorySchema(BaseSchema):
    """Schema for feedback memory (API response)."""

    sprint_id: UUID
    phase: str
    max_attempts: int = 3
    current_attempt: int = 0
    attempts: list[AttemptRecord] = Field(default_factory=list)
    accumulated_context: dict[str, Any] = Field(default_factory=dict)
    escalated: bool = False
    escalation_reason: str | None = None
```

### 2.3 FeedbackMemory Data Structure

FeedbackMemory stores retry history and accumulated context for the optimizer.

```python
# File: backend/app/runners/evaluators/feedback_memory.py

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass
class AttemptRecord:
    """Record of a single evaluation attempt."""

    attempt_number: int
    started_at: datetime
    completed_at: datetime | None = None
    phase_output: str = ""
    evaluation_results: list["EvaluationResult"] = field(default_factory=list)
    optimization_prompt: str | None = None
    trace_id: str | None = None

    @property
    def duration_ms(self) -> int | None:
        """Duration of this attempt in milliseconds."""
        if self.completed_at and self.started_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return None

    @property
    def passed(self) -> bool:
        """Whether all evaluations passed."""
        return all(e.passed for e in self.evaluation_results)

    @property
    def aggregate_score(self) -> float:
        """Average score across all evaluations."""
        if not self.evaluation_results:
            return 0.0
        return sum(e.score for e in self.evaluation_results) / len(self.evaluation_results)

    def get_failed_feedback(self) -> list[str]:
        """Get feedback from failed evaluations."""
        return [e.feedback for e in self.evaluation_results if not e.passed]


@dataclass
class FeedbackMemory:
    """Stores retry history and context for the optimizer.

    Implements exponentially increasing context for retry attempts:
    - Attempt 1: Original task only
    - Attempt 2: Original task + attempt 1 feedback
    - Attempt 3: Original task + all previous feedback + detailed analysis

    After 3 failed attempts, escalates to human review.
    """

    sprint_id: UUID
    phase: str
    original_goal: str
    max_attempts: int = 3
    attempts: list[AttemptRecord] = field(default_factory=list)
    accumulated_insights: dict[str, Any] = field(default_factory=dict)
    escalated: bool = False
    escalation_reason: str | None = None

    @property
    def current_attempt(self) -> int:
        """Current attempt number (1-indexed)."""
        return len(self.attempts) + 1

    @property
    def can_retry(self) -> bool:
        """Whether another retry is allowed."""
        return len(self.attempts) < self.max_attempts and not self.escalated

    @property
    def latest_attempt(self) -> AttemptRecord | None:
        """Get the most recent attempt."""
        return self.attempts[-1] if self.attempts else None

    def add_attempt(
        self,
        phase_output: str,
        evaluation_results: list["EvaluationResult"],
        optimization_prompt: str | None = None,
        trace_id: str | None = None,
    ) -> AttemptRecord:
        """Record a new attempt.

        Args:
            phase_output: The output from the phase execution
            evaluation_results: List of evaluation results
            optimization_prompt: The prompt used for this attempt (if optimized)
            trace_id: Logfire trace ID

        Returns:
            The created AttemptRecord
        """
        attempt = AttemptRecord(
            attempt_number=self.current_attempt,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            phase_output=phase_output[:2000],  # Truncate for memory efficiency
            evaluation_results=evaluation_results,
            optimization_prompt=optimization_prompt,
            trace_id=trace_id,
        )
        self.attempts.append(attempt)

        # Update accumulated insights
        self._update_insights(attempt)

        return attempt

    def _update_insights(self, attempt: AttemptRecord) -> None:
        """Update accumulated insights from attempt results."""
        if "recurring_issues" not in self.accumulated_insights:
            self.accumulated_insights["recurring_issues"] = []

        if "successful_patterns" not in self.accumulated_insights:
            self.accumulated_insights["successful_patterns"] = []

        # Track recurring issues
        for eval_result in attempt.evaluation_results:
            if not eval_result.passed:
                for suggestion in eval_result.suggestions:
                    if suggestion not in self.accumulated_insights["recurring_issues"]:
                        self.accumulated_insights["recurring_issues"].append(suggestion)

    def get_optimization_context(self) -> dict[str, Any]:
        """Get context for the optimizer with exponentially increasing detail.

        Returns context appropriate to the current attempt number:
        - Attempt 2: Basic feedback summary
        - Attempt 3: Full history with detailed analysis

        Returns:
            Context dictionary for the optimizer
        """
        context = {
            "sprint_id": str(self.sprint_id),
            "phase": self.phase,
            "original_goal": self.original_goal,
            "attempt_number": self.current_attempt,
            "max_attempts": self.max_attempts,
        }

        if self.current_attempt == 2 and self.attempts:
            # Basic feedback from first attempt
            latest = self.attempts[-1]
            context["previous_feedback"] = latest.get_failed_feedback()
            context["previous_score"] = latest.aggregate_score

        elif self.current_attempt >= 3 and self.attempts:
            # Full history with analysis
            context["attempt_history"] = [
                {
                    "attempt": a.attempt_number,
                    "score": a.aggregate_score,
                    "passed": a.passed,
                    "feedback": a.get_failed_feedback(),
                    "output_preview": a.phase_output[:500],
                }
                for a in self.attempts
            ]
            context["recurring_issues"] = self.accumulated_insights.get("recurring_issues", [])
            context["analysis"] = self._generate_failure_analysis()

        return context

    def _generate_failure_analysis(self) -> str:
        """Generate analysis of repeated failures."""
        if len(self.attempts) < 2:
            return ""

        scores = [a.aggregate_score for a in self.attempts]
        improving = scores[-1] > scores[0]

        analysis_parts = [
            f"After {len(self.attempts)} attempts:",
            f"- Score trend: {'Improving' if improving else 'Not improving'} ({scores[0]:.2f} -> {scores[-1]:.2f})",
        ]

        recurring = self.accumulated_insights.get("recurring_issues", [])
        if recurring:
            analysis_parts.append(f"- Recurring issues ({len(recurring)}): {', '.join(recurring[:3])}")

        return "\n".join(analysis_parts)

    def get_summary_for_prompt(self) -> str:
        """Get a formatted summary suitable for inclusion in agent prompts.

        Returns:
            Markdown-formatted summary of feedback history
        """
        if not self.attempts:
            return ""

        lines = [
            f"## Previous Attempts for {self.phase} Phase",
            f"You are on attempt {self.current_attempt} of {self.max_attempts}.",
            "",
        ]

        for attempt in self.attempts:
            lines.append(f"### Attempt {attempt.attempt_number}")
            lines.append(f"- Score: {attempt.aggregate_score:.2f}")
            lines.append(f"- Status: {'PASSED' if attempt.passed else 'FAILED'}")

            if not attempt.passed:
                lines.append("- Issues to fix:")
                for feedback in attempt.get_failed_feedback():
                    lines.append(f"  - {feedback}")
            lines.append("")

        if self.current_attempt == self.max_attempts:
            lines.append("**CRITICAL: This is your FINAL attempt. Address ALL issues below.**")
            lines.append("")

        return "\n".join(lines)

    def escalate(self, reason: str) -> None:
        """Mark this phase for human escalation.

        Args:
            reason: Explanation of why escalation is needed
        """
        self.escalated = True
        self.escalation_reason = reason

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "sprint_id": str(self.sprint_id),
            "phase": self.phase,
            "original_goal": self.original_goal,
            "max_attempts": self.max_attempts,
            "current_attempt": self.current_attempt,
            "attempts": [
                {
                    "attempt_number": a.attempt_number,
                    "started_at": a.started_at.isoformat(),
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                    "passed": a.passed,
                    "score": a.aggregate_score,
                    "feedback": a.get_failed_feedback(),
                    "trace_id": a.trace_id,
                }
                for a in self.attempts
            ],
            "accumulated_insights": self.accumulated_insights,
            "escalated": self.escalated,
            "escalation_reason": self.escalation_reason,
        }
```

### 2.4 Evaluator Implementations

#### 2.4.1 Deterministic Evaluators

```python
# File: backend/app/runners/evaluators/deterministic.py

import asyncio
import logging
import subprocess
from pathlib import Path

from app.runners.evaluators.protocol import (
    CriterionResult,
    EvaluationCategory,
    EvaluationResult,
    Evaluator,
)

logger = logging.getLogger(__name__)


class RuffLintEvaluator:
    """Deterministic evaluator using Ruff for Python linting."""

    @property
    def name(self) -> str:
        return "ruff_lint"

    @property
    def category(self) -> EvaluationCategory:
        return EvaluationCategory.COMPLIANCE

    @property
    def is_deterministic(self) -> bool:
        return True

    async def evaluate(
        self,
        phase: str,
        output: str,
        context: dict,
    ) -> EvaluationResult:
        """Run ruff check on workspace files."""
        workspace_ref = context.get("workspace_ref")
        if not workspace_ref:
            return EvaluationResult(
                evaluator_name=self.name,
                category=self.category,
                passed=True,
                score=1.0,
                feedback="No workspace to lint",
            )

        workspace_path = Path(workspace_ref)
        if not workspace_path.exists():
            return EvaluationResult(
                evaluator_name=self.name,
                category=self.category,
                passed=False,
                score=0.0,
                feedback=f"Workspace not found: {workspace_ref}",
            )

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["ruff", "check", str(workspace_path), "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            criteria = []
            if result.returncode == 0:
                criteria.append(CriterionResult(
                    criterion="no_lint_errors",
                    passed=True,
                    score=1.0,
                    message="No linting errors found",
                ))
                return EvaluationResult(
                    evaluator_name=self.name,
                    category=self.category,
                    passed=True,
                    score=1.0,
                    feedback="Code passes all lint checks",
                    criteria=criteria,
                )
            else:
                import json
                try:
                    errors = json.loads(result.stdout) if result.stdout else []
                except json.JSONDecodeError:
                    errors = []

                error_count = len(errors)
                score = max(0.0, 1.0 - (error_count * 0.1))  # Deduct 0.1 per error

                suggestions = []
                for error in errors[:5]:  # Limit to first 5
                    suggestions.append(
                        f"Fix {error.get('code', 'error')}: {error.get('message', '')} "
                        f"at {error.get('filename', '')}:{error.get('location', {}).get('row', '')}"
                    )

                criteria.append(CriterionResult(
                    criterion="no_lint_errors",
                    passed=False,
                    score=score,
                    message=f"Found {error_count} lint error(s)",
                    evidence=result.stdout[:1000],
                ))

                return EvaluationResult(
                    evaluator_name=self.name,
                    category=self.category,
                    passed=False,
                    score=score,
                    feedback=f"Code has {error_count} lint error(s). Run 'ruff check --fix' to auto-fix.",
                    criteria=criteria,
                    suggestions=suggestions,
                    metadata={"error_count": error_count},
                )

        except subprocess.TimeoutExpired:
            return EvaluationResult(
                evaluator_name=self.name,
                category=self.category,
                passed=False,
                score=0.0,
                feedback="Lint check timed out",
            )
        except Exception as e:
            logger.error(f"Ruff evaluation failed: {e}")
            return EvaluationResult(
                evaluator_name=self.name,
                category=self.category,
                passed=False,
                score=0.0,
                feedback=f"Lint check failed: {e}",
            )


class PytestEvaluator:
    """Deterministic evaluator using pytest for test execution."""

    @property
    def name(self) -> str:
        return "pytest"

    @property
    def category(self) -> EvaluationCategory:
        return EvaluationCategory.FUNCTIONALITY

    @property
    def is_deterministic(self) -> bool:
        return True

    async def evaluate(
        self,
        phase: str,
        output: str,
        context: dict,
    ) -> EvaluationResult:
        """Run pytest on workspace."""
        workspace_ref = context.get("workspace_ref")
        if not workspace_ref:
            return EvaluationResult(
                evaluator_name=self.name,
                category=self.category,
                passed=True,
                score=1.0,
                feedback="No workspace to test",
            )

        workspace_path = Path(workspace_ref)

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["python", "-m", "pytest", str(workspace_path), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=workspace_path,
            )

            criteria = []

            if result.returncode == 0:
                # Parse test count from output
                passed_tests = result.stdout.count(" PASSED")
                criteria.append(CriterionResult(
                    criterion="tests_pass",
                    passed=True,
                    score=1.0,
                    message=f"All {passed_tests} test(s) passed",
                ))

                return EvaluationResult(
                    evaluator_name=self.name,
                    category=self.category,
                    passed=True,
                    score=1.0,
                    feedback=f"All tests passed ({passed_tests} tests)",
                    criteria=criteria,
                    metadata={"passed_tests": passed_tests},
                )
            else:
                failed_tests = result.stdout.count(" FAILED")
                passed_tests = result.stdout.count(" PASSED")
                total = failed_tests + passed_tests
                score = passed_tests / total if total > 0 else 0.0

                criteria.append(CriterionResult(
                    criterion="tests_pass",
                    passed=False,
                    score=score,
                    message=f"{failed_tests} of {total} test(s) failed",
                    evidence=result.stdout[-2000:],  # Last 2000 chars of output
                ))

                # Extract failure messages for suggestions
                suggestions = []
                for line in result.stdout.split("\n"):
                    if "FAILED" in line or "AssertionError" in line:
                        suggestions.append(line.strip()[:200])

                return EvaluationResult(
                    evaluator_name=self.name,
                    category=self.category,
                    passed=False,
                    score=score,
                    feedback=f"{failed_tests} test(s) failed. Review test output and fix issues.",
                    criteria=criteria,
                    suggestions=suggestions[:5],
                    metadata={
                        "passed_tests": passed_tests,
                        "failed_tests": failed_tests,
                    },
                )

        except subprocess.TimeoutExpired:
            return EvaluationResult(
                evaluator_name=self.name,
                category=self.category,
                passed=False,
                score=0.0,
                feedback="Tests timed out after 120 seconds",
                suggestions=["Check for infinite loops or blocking operations"],
            )
        except Exception as e:
            logger.error(f"Pytest evaluation failed: {e}")
            return EvaluationResult(
                evaluator_name=self.name,
                category=self.category,
                passed=False,
                score=0.0,
                feedback=f"Test execution failed: {e}",
            )


class TypeCheckEvaluator:
    """Deterministic evaluator using pyright/mypy for type checking."""

    @property
    def name(self) -> str:
        return "type_check"

    @property
    def category(self) -> EvaluationCategory:
        return EvaluationCategory.COMPLIANCE

    @property
    def is_deterministic(self) -> bool:
        return True

    async def evaluate(
        self,
        phase: str,
        output: str,
        context: dict,
    ) -> EvaluationResult:
        """Run pyright on workspace files."""
        workspace_ref = context.get("workspace_ref")
        if not workspace_ref:
            return EvaluationResult(
                evaluator_name=self.name,
                category=self.category,
                passed=True,
                score=1.0,
                feedback="No workspace to type check",
            )

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["pyright", workspace_ref, "--outputjson"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                return EvaluationResult(
                    evaluator_name=self.name,
                    category=self.category,
                    passed=True,
                    score=1.0,
                    feedback="No type errors found",
                )
            else:
                import json
                try:
                    data = json.loads(result.stdout)
                    error_count = data.get("summary", {}).get("errorCount", 0)
                except (json.JSONDecodeError, KeyError):
                    error_count = result.stdout.count("error:")

                score = max(0.0, 1.0 - (error_count * 0.1))

                return EvaluationResult(
                    evaluator_name=self.name,
                    category=self.category,
                    passed=error_count == 0,
                    score=score,
                    feedback=f"Found {error_count} type error(s)",
                    suggestions=["Add type hints to function parameters and return values"],
                    metadata={"error_count": error_count},
                )

        except FileNotFoundError:
            # Pyright not installed, skip
            return EvaluationResult(
                evaluator_name=self.name,
                category=self.category,
                passed=True,
                score=1.0,
                feedback="Type checker not available (skipped)",
            )
        except Exception as e:
            logger.error(f"Type check failed: {e}")
            return EvaluationResult(
                evaluator_name=self.name,
                category=self.category,
                passed=True,
                score=1.0,
                feedback=f"Type check skipped: {e}",
            )
```

#### 2.4.2 LLM-Based Evaluator

```python
# File: backend/app/runners/evaluators/llm_evaluator.py

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings
from app.runners.evaluators.protocol import (
    CriterionResult,
    EvaluationCategory,
    EvaluationResult,
)

logger = logging.getLogger(__name__)


class LLMEvaluationResponse(BaseModel):
    """Expected response structure from LLM evaluator."""

    overall_assessment: str = Field(..., description="Brief overall assessment")
    score: float = Field(ge=0.0, le=1.0, description="Score from 0 to 1")
    criteria_results: list[dict[str, Any]] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)


class LLMCodeQualityEvaluator:
    """LLM-based evaluator for subjective code quality assessment."""

    EVALUATION_PROMPT = """You are a code quality evaluator. Assess the following code output for quality.

## Code Output
```
{output}
```

## Original Goal
{goal}

## Evaluation Criteria
1. **Correctness**: Does the code achieve the stated goal?
2. **Clarity**: Is the code readable and well-organized?
3. **Completeness**: Are all requirements addressed?
4. **Best Practices**: Does it follow Python/language best practices?

## Response Format
Respond with valid JSON matching this structure:
{{
    "overall_assessment": "Brief 1-2 sentence assessment",
    "score": 0.85,
    "criteria_results": [
        {{"criterion": "correctness", "passed": true, "score": 0.9, "message": "..."}},
        {{"criterion": "clarity", "passed": true, "score": 0.8, "message": "..."}},
        {{"criterion": "completeness", "passed": false, "score": 0.6, "message": "..."}},
        {{"criterion": "best_practices", "passed": true, "score": 0.9, "message": "..."}}
    ],
    "suggestions": ["Specific suggestion 1", "Specific suggestion 2"],
    "blocking_issues": ["Critical issue that must be fixed"]
}}
"""

    @property
    def name(self) -> str:
        return "llm_code_quality"

    @property
    def category(self) -> EvaluationCategory:
        return EvaluationCategory.MAINTAINABILITY

    @property
    def is_deterministic(self) -> bool:
        return False

    async def evaluate(
        self,
        phase: str,
        output: str,
        context: dict,
    ) -> EvaluationResult:
        """Evaluate code quality using LLM."""
        from pydantic_ai import Agent

        goal = context.get("goal", "Unknown goal")

        prompt = self.EVALUATION_PROMPT.format(
            output=output[:4000],  # Limit output size
            goal=goal,
        )

        try:
            # Use a faster model for evaluation (Sonnet recommended)
            agent = Agent(
                model=settings.EVALUATOR_MODEL or "anthropic:claude-sonnet-4-20250514",
                result_type=LLMEvaluationResponse,
            )

            result = await agent.run(prompt)
            response = result.data

            # Convert to EvaluationResult
            criteria = [
                CriterionResult(
                    criterion=c.get("criterion", "unknown"),
                    passed=c.get("passed", False),
                    score=c.get("score", 0.0),
                    message=c.get("message", ""),
                )
                for c in response.criteria_results
            ]

            return EvaluationResult(
                evaluator_name=self.name,
                category=self.category,
                passed=response.score >= 0.7 and len(response.blocking_issues) == 0,
                score=response.score,
                feedback=response.overall_assessment,
                criteria=criteria,
                suggestions=response.suggestions,
                metadata={
                    "blocking_issues": response.blocking_issues,
                    "model": str(agent.model),
                },
            )

        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            return EvaluationResult(
                evaluator_name=self.name,
                category=self.category,
                passed=True,  # Don't block on LLM evaluation failures
                score=0.5,
                feedback=f"LLM evaluation unavailable: {e}",
                metadata={"error": str(e)},
            )
```

### 2.5 Evaluator Registry

```python
# File: backend/app/runners/evaluators/registry.py

from typing import Callable

from app.runners.evaluators.protocol import Evaluator, EvaluationCategory


class EvaluatorRegistry:
    """Registry for managing evaluators by phase and category."""

    def __init__(self):
        self._evaluators: dict[str, dict[str, Evaluator]] = {}
        self._global_evaluators: list[Evaluator] = []

    def register(
        self,
        evaluator: Evaluator,
        phases: list[str] | None = None,
    ) -> None:
        """Register an evaluator.

        Args:
            evaluator: The evaluator instance
            phases: Specific phases this evaluator applies to (None = all phases)
        """
        if phases is None:
            self._global_evaluators.append(evaluator)
        else:
            for phase in phases:
                if phase not in self._evaluators:
                    self._evaluators[phase] = {}
                self._evaluators[phase][evaluator.name] = evaluator

    def get_evaluators(self, phase: str) -> list[Evaluator]:
        """Get all evaluators for a phase.

        Args:
            phase: The phase name

        Returns:
            List of applicable evaluators (phase-specific + global)
        """
        evaluators = list(self._global_evaluators)
        if phase in self._evaluators:
            evaluators.extend(self._evaluators[phase].values())
        return evaluators

    def get_deterministic_evaluators(self, phase: str) -> list[Evaluator]:
        """Get only deterministic evaluators for a phase."""
        return [e for e in self.get_evaluators(phase) if e.is_deterministic]

    def get_llm_evaluators(self, phase: str) -> list[Evaluator]:
        """Get only LLM-based evaluators for a phase."""
        return [e for e in self.get_evaluators(phase) if not e.is_deterministic]


def create_default_registry() -> EvaluatorRegistry:
    """Create registry with default evaluators."""
    from app.runners.evaluators.deterministic import (
        PytestEvaluator,
        RuffLintEvaluator,
        TypeCheckEvaluator,
    )
    from app.runners.evaluators.llm_evaluator import LLMCodeQualityEvaluator

    registry = EvaluatorRegistry()

    # Global evaluators (all phases)
    registry.register(RuffLintEvaluator())

    # Phase-specific evaluators
    registry.register(PytestEvaluator(), phases=["verification", "coding"])
    registry.register(TypeCheckEvaluator(), phases=["coding"])
    registry.register(LLMCodeQualityEvaluator(), phases=["coding", "discovery"])

    return registry
```

---

## 3. PhaseRunner Integration

### 3.1 Integration Points

The following methods will be added to `PhaseRunner`:

```python
# File: backend/app/runners/phase_runner.py (additions)

from app.runners.evaluators.feedback_memory import FeedbackMemory
from app.runners.evaluators.protocol import EvaluationResult
from app.runners.evaluators.registry import EvaluatorRegistry, create_default_registry


class PhaseRunner:
    """Orchestrates the automated software development lifecycle phases."""

    MAX_RETRIES = 3

    # New class-level registry
    _evaluator_registry: EvaluatorRegistry | None = None

    @classmethod
    def get_evaluator_registry(cls) -> EvaluatorRegistry:
        """Get or create the evaluator registry."""
        if cls._evaluator_registry is None:
            cls._evaluator_registry = create_default_registry()
        return cls._evaluator_registry

    @classmethod
    async def evaluate_phase_output(
        cls,
        phase: str,
        output: str,
        context: dict,
        deterministic_only: bool = False,
    ) -> list[EvaluationResult]:
        """Evaluate phase output using registered evaluators.

        Args:
            phase: Name of the phase (e.g., "coding", "verification")
            output: The phase output to evaluate
            context: Evaluation context (workspace_ref, goal, etc.)
            deterministic_only: If True, skip LLM-based evaluators

        Returns:
            List of EvaluationResult from all applicable evaluators
        """
        registry = cls.get_evaluator_registry()

        if deterministic_only:
            evaluators = registry.get_deterministic_evaluators(phase)
        else:
            evaluators = registry.get_evaluators(phase)

        results = []
        for evaluator in evaluators:
            try:
                result = await evaluator.evaluate(phase, output, context)
                results.append(result)

                logger.info(
                    f"Evaluator {evaluator.name} for phase {phase}: "
                    f"passed={result.passed}, score={result.score:.2f}"
                )
            except Exception as e:
                logger.error(f"Evaluator {evaluator.name} failed: {e}")
                # Don't block on evaluator failures
                continue

        return results

    @classmethod
    async def optimize_and_retry(
        cls,
        phase: str,
        feedback_memory: FeedbackMemory,
        agent_tdd_service: "AgentTddService",
        sprint: "Sprint",
    ) -> tuple[str, str | None]:
        """Generate optimized prompt based on feedback and retry.

        Args:
            phase: The phase to retry
            feedback_memory: Memory containing previous attempts
            agent_tdd_service: Service for executing agent
            sprint: The sprint being processed

        Returns:
            Tuple of (optimized_prompt, optimized_output or None if failed)
        """
        context = feedback_memory.get_optimization_context()
        feedback_summary = feedback_memory.get_summary_for_prompt()

        # Build optimized prompt
        base_prompt = cls._get_base_prompt_for_phase(phase, sprint)

        optimized_prompt = f"""
{feedback_summary}

## Your Task
{base_prompt}

## CRITICAL Requirements Based on Previous Feedback
{cls._format_requirements_from_feedback(context)}

Remember: This is attempt {context['attempt_number']} of {context['max_attempts']}.
"""

        return optimized_prompt

    @classmethod
    def _get_base_prompt_for_phase(cls, phase: str, sprint: "Sprint") -> str:
        """Get the base prompt for a phase."""
        goal = sprint.goal or sprint.name

        prompts = {
            "discovery": (
                f"Perform Discovery and Planning for: '{goal}'\n"
                f"1. Analyze the requirements.\n"
                f"2. Create 'implementation_plan.md' in the workspace.\n"
                f"3. Return 'Discovery Complete' when done."
            ),
            "coding": (
                f"Implement the code for: '{goal}'\n"
                f"1. Read 'implementation_plan.md'.\n"
                f"2. Create the implementation files.\n"
                f"3. Return 'Coding Complete' when done."
            ),
            "verification": (
                f"Verify the implementation for: '{goal}'\n"
                f"1. Run tests using run_tests().\n"
                f"2. Return 'VERIFICATION_SUCCESS' if all tests pass.\n"
                f"3. Return 'VERIFICATION_FAILURE' if tests fail."
            ),
        }
        return prompts.get(phase, f"Execute {phase} phase for: {goal}")

    @classmethod
    def _format_requirements_from_feedback(cls, context: dict) -> str:
        """Format requirements based on feedback context."""
        requirements = []

        if "previous_feedback" in context:
            for i, feedback in enumerate(context["previous_feedback"], 1):
                requirements.append(f"{i}. FIX: {feedback}")

        if "recurring_issues" in context:
            for issue in context["recurring_issues"]:
                if issue not in str(requirements):
                    requirements.append(f"- RECURRING ISSUE: {issue}")

        if not requirements:
            return "No specific requirements from previous feedback."

        return "\n".join(requirements)

    @classmethod
    async def run_phase_with_evaluation(
        cls,
        phase: str,
        sprint: "Sprint",
        workspace_ref: str,
        agent_tdd_service: "AgentTddService",
        tracker: "WorkflowTracker",
        broadcast_fn: Callable,
    ) -> tuple[bool, str]:
        """Run a phase with evaluation and retry logic.

        Args:
            phase: Phase name
            sprint: Sprint being processed
            workspace_ref: Workspace reference
            agent_tdd_service: Service for agent execution
            tracker: Workflow tracker
            broadcast_fn: Function to broadcast status updates

        Returns:
            Tuple of (success: bool, output: str)
        """
        feedback_memory = FeedbackMemory(
            sprint_id=sprint.id,
            phase=phase,
            original_goal=sprint.goal or sprint.name,
            max_attempts=cls.MAX_RETRIES,
        )

        for attempt in range(cls.MAX_RETRIES):
            logger.info(f"Phase {phase} attempt {attempt + 1}/{cls.MAX_RETRIES}")

            # Get prompt (original or optimized)
            if attempt == 0:
                prompt = cls._get_base_prompt_for_phase(phase, sprint)
            else:
                prompt = await cls.optimize_and_retry(
                    phase, feedback_memory, agent_tdd_service, sprint
                )

            # Execute phase
            result = await agent_tdd_service.execute(
                AgentTddRunCreate(
                    message=prompt,
                    workspace_ref=workspace_ref,
                    metadata={
                        "sprint_id": str(sprint.id),
                        "phase": phase,
                        "attempt": attempt,
                    },
                ),
                user_id=None,
            )

            # Get output
            output = ""
            if result.decision and result.decision.candidate_id:
                for c in result.candidates:
                    if c.id == result.decision.candidate_id:
                        output = c.output or ""
                        break
            elif result.candidates:
                output = result.candidates[0].output or ""

            # Evaluate output
            eval_results = await cls.evaluate_phase_output(
                phase=phase,
                output=output,
                context={
                    "workspace_ref": workspace_ref,
                    "goal": sprint.goal,
                    "attempt": attempt,
                },
            )

            # Record attempt
            feedback_memory.add_attempt(
                phase_output=output,
                evaluation_results=eval_results,
                optimization_prompt=prompt if attempt > 0 else None,
            )

            # Check if passed
            all_passed = all(e.passed for e in eval_results)
            if all_passed:
                logger.info(f"Phase {phase} passed on attempt {attempt + 1}")

                # Record evaluation in tracker
                await tracker.record_event(
                    event_type="evaluation_passed",
                    phase=phase,
                    metadata={
                        "attempt": attempt + 1,
                        "evaluations": [e.model_dump() for e in eval_results],
                    },
                )

                return True, output

            # Log failed evaluation
            failed_evals = [e for e in eval_results if not e.passed]
            for eval_result in failed_evals:
                logger.warning(
                    f"Evaluation failed: {eval_result.evaluator_name} - {eval_result.feedback}"
                )

            # Record failure
            await tracker.record_event(
                event_type="evaluation_failed",
                phase=phase,
                metadata={
                    "attempt": attempt + 1,
                    "evaluations": [e.model_dump() for e in eval_results],
                    "will_retry": feedback_memory.can_retry,
                },
            )

            if not feedback_memory.can_retry:
                break

            await broadcast_fn(
                "active",
                phase,
                f"Evaluation failed on attempt {attempt + 1}. Retrying...",
            )

        # All retries exhausted
        feedback_memory.escalate(
            f"Phase {phase} failed after {cls.MAX_RETRIES} attempts"
        )

        await tracker.record_event(
            event_type="phase_escalated",
            phase=phase,
            metadata={
                "reason": feedback_memory.escalation_reason,
                "attempts": feedback_memory.to_dict(),
            },
        )

        return False, output
```

### 3.2 Updated Phase Execution Flow

```python
# Example integration in PhaseRunner.start() method

# --- Phase 2: Coding with Evaluation ---
coding_success, coding_output = await cls.run_phase_with_evaluation(
    phase="coding",
    sprint=sprint,
    workspace_ref=workspace_ref,
    agent_tdd_service=agent_tdd_service,
    tracker=tracker,
    broadcast_fn=broadcast_status,
)

if not coding_success:
    logger.error("Coding phase failed after max retries")
    await sprint_service.update(sprint_id, SprintUpdate(status=SprintStatus.FAILED))
    await broadcast_status("failed", "coding", "Coding failed after max retries")
    return

# --- Phase 3: Verification with Evaluation ---
verification_success, verification_output = await cls.run_phase_with_evaluation(
    phase="verification",
    sprint=sprint,
    workspace_ref=workspace_ref,
    agent_tdd_service=agent_tdd_service,
    tracker=tracker,
    broadcast_fn=broadcast_status,
)

if verification_success:
    logger.info("Sprint Completed Successfully")
    await sprint_service.update(sprint_id, SprintUpdate(status=SprintStatus.COMPLETED))
    await broadcast_status("completed", "verification", "Sprint completed successfully!")
else:
    logger.error("Verification phase failed")
    await sprint_service.update(sprint_id, SprintUpdate(status=SprintStatus.FAILED))
    await broadcast_status("failed", "verification", "Verification failed after max retries")
```

---

## 4. Configuration

### 4.1 Settings Additions

```python
# File: backend/app/core/config.py (additions)

class Settings(BaseSettings):
    # ... existing settings ...

    # Evaluator settings
    EVALUATOR_MODEL: str = "anthropic:claude-sonnet-4-20250514"
    EVALUATOR_MAX_RETRIES: int = 3
    EVALUATOR_RUN_DETERMINISTIC_ONLY: bool = False
    EVALUATOR_LINT_TIMEOUT: int = 30
    EVALUATOR_TEST_TIMEOUT: int = 120
    EVALUATOR_LLM_TIMEOUT: int = 60

    # Pass thresholds
    EVALUATOR_PASS_THRESHOLD: float = 0.7
    EVALUATOR_BLOCKING_THRESHOLD: float = 0.5
```

### 4.2 WebSocket Events for Evaluation

```python
# File: backend/app/core/websocket_events.py (additions)

class SprintEventType(str, Enum):
    # ... existing events ...

    # Evaluation events
    EVALUATION_STARTED = "evaluation.started"
    EVALUATION_COMPLETED = "evaluation.completed"
    EVALUATION_FAILED = "evaluation.failed"
    OPTIMIZATION_STARTED = "optimization.started"
    ESCALATION_REQUIRED = "escalation.required"


class EvaluationData(BaseModel):
    """Data about an evaluation."""

    evaluator_name: str
    category: str
    passed: bool
    score: float
    feedback: str
    suggestions: list[str] = Field(default_factory=list)


class EvaluationCompletedEvent(BaseSprintEvent):
    """Event when evaluation completes."""

    event: SprintEventType = SprintEventType.EVALUATION_COMPLETED
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        sprint_id: str | UUID,
        phase: str,
        attempt: int,
        evaluations: list[EvaluationData],
        overall_passed: bool,
        sequence: int = 0,
    ) -> "EvaluationCompletedEvent":
        return cls(
            sprint_id=str(sprint_id),
            sequence=sequence,
            data={
                "phase": phase,
                "attempt": attempt,
                "overall_passed": overall_passed,
                "evaluations": [e.model_dump() for e in evaluations],
            },
        )
```

---

## 5. File Structure

```
backend/app/runners/
├── __init__.py
├── phase_runner.py              # Updated with evaluation integration
└── evaluators/
    ├── __init__.py
    ├── protocol.py              # Evaluator protocol and EvaluationResult
    ├── feedback_memory.py       # FeedbackMemory data structure
    ├── registry.py              # EvaluatorRegistry
    ├── deterministic.py         # RuffLintEvaluator, PytestEvaluator, etc.
    └── llm_evaluator.py         # LLMCodeQualityEvaluator

backend/app/schemas/
├── evaluation.py                # Pydantic schemas for API responses
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

```python
# File: backend/tests/unit/test_evaluators.py

import pytest
from app.runners.evaluators.protocol import EvaluationResult, EvaluationCategory
from app.runners.evaluators.feedback_memory import FeedbackMemory
from uuid import uuid4


class TestEvaluationResult:
    def test_failed_criteria_filter(self):
        result = EvaluationResult(
            evaluator_name="test",
            category=EvaluationCategory.FUNCTIONALITY,
            passed=False,
            score=0.5,
            feedback="Test feedback",
            criteria=[
                CriterionResult(criterion="a", passed=True, score=1.0, message="OK"),
                CriterionResult(criterion="b", passed=False, score=0.3, message="Failed"),
            ],
        )

        assert len(result.failed_criteria) == 1
        assert result.failed_criteria[0].criterion == "b"


class TestFeedbackMemory:
    def test_optimization_context_increases_with_attempts(self):
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Test goal",
        )

        # First attempt context is minimal
        ctx1 = memory.get_optimization_context()
        assert ctx1["attempt_number"] == 1
        assert "previous_feedback" not in ctx1

        # Add attempt and check context grows
        memory.add_attempt(
            phase_output="output 1",
            evaluation_results=[
                EvaluationResult(
                    evaluator_name="test",
                    category=EvaluationCategory.FUNCTIONALITY,
                    passed=False,
                    score=0.5,
                    feedback="Fix issue X",
                ),
            ],
        )

        ctx2 = memory.get_optimization_context()
        assert ctx2["attempt_number"] == 2
        assert "previous_feedback" in ctx2

    def test_can_retry_respects_max_attempts(self):
        memory = FeedbackMemory(
            sprint_id=uuid4(),
            phase="coding",
            original_goal="Test",
            max_attempts=2,
        )

        assert memory.can_retry

        memory.add_attempt("out1", [])
        assert memory.can_retry

        memory.add_attempt("out2", [])
        assert not memory.can_retry
```

### 6.2 Integration Tests

```python
# File: backend/tests/integration/test_evaluator_integration.py

import pytest
from app.runners.evaluators.deterministic import RuffLintEvaluator
from pathlib import Path


@pytest.mark.anyio
async def test_ruff_evaluator_with_clean_code(tmp_path: Path):
    """Test Ruff evaluator passes clean code."""
    # Create clean Python file
    code_file = tmp_path / "clean.py"
    code_file.write_text('def hello() -> str:\n    return "Hello"\n')

    evaluator = RuffLintEvaluator()
    result = await evaluator.evaluate(
        phase="coding",
        output="",
        context={"workspace_ref": str(tmp_path)},
    )

    assert result.passed
    assert result.score >= 0.9


@pytest.mark.anyio
async def test_ruff_evaluator_detects_errors(tmp_path: Path):
    """Test Ruff evaluator catches lint errors."""
    # Create file with issues
    code_file = tmp_path / "bad.py"
    code_file.write_text('import os\nx=1')  # Unused import, missing whitespace

    evaluator = RuffLintEvaluator()
    result = await evaluator.evaluate(
        phase="coding",
        output="",
        context={"workspace_ref": str(tmp_path)},
    )

    assert not result.passed
    assert result.score < 1.0
    assert len(result.suggestions) > 0
```

---

## 7. Migration Path

### 7.1 Phase 1: Add Evaluation Infrastructure (Week 1)

1. Create `backend/app/runners/evaluators/` directory structure
2. Implement `protocol.py` with Evaluator protocol and EvaluationResult
3. Implement `feedback_memory.py`
4. Implement `registry.py`
5. Add unit tests

### 7.2 Phase 2: Implement Evaluators (Week 2)

1. Implement `deterministic.py` with RuffLintEvaluator and PytestEvaluator
2. Implement `llm_evaluator.py`
3. Add integration tests
4. Add configuration settings

### 7.3 Phase 3: PhaseRunner Integration (Week 3)

1. Add `evaluate_phase_output()` to PhaseRunner
2. Add `optimize_and_retry()` to PhaseRunner
3. Add `run_phase_with_evaluation()` wrapper
4. Update existing phase execution to use new methods
5. Add WebSocket events for evaluation status
6. End-to-end testing

---

## 8. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| pass@3 rate | >95% | Sprints passing within 3 attempts |
| Retry reduction | 30% | Fewer retries with optimized prompts |
| False positive rate | <5% | Evaluators incorrectly failing good code |
| Evaluation latency | <10s | Deterministic evaluators combined |
| Human escalations | <10% | Sprints requiring human intervention |

---

## 9. Related Skills

The following installed skills provide implementation guidance:

- `skills/pytest-testing` - For test evaluator patterns
- `skills/code-auditor` - For code quality assessment approaches
- `skills/clean-code` - For deterministic code quality checks

Read with: `cat skills/<skill-name>/SKILL.md`

---

## Appendix A: ADR Summary

### ADR-003: Evaluator-Optimizer Pattern for PhaseRunner

**Status:** Proposed

**Context:** Current PhaseRunner has basic retry logic but lacks structured evaluation and feedback-driven optimization. Research shows this leads to inefficient retries and missed issues.

**Decision:** Implement Evaluator-Optimizer pattern with:
- Protocol-based evaluator interface for extensibility
- Deterministic evaluators first (Ruff, pytest) for reliability
- LLM evaluators for subjective quality (optional)
- FeedbackMemory for context accumulation across retries
- Human escalation after 3 failed attempts

**Consequences:**
- (+) Structured feedback improves retry success rate
- (+) Deterministic checks catch issues before LLM evaluation
- (+) Extensible architecture allows adding new evaluators
- (-) Additional latency from evaluation steps
- (-) Complexity increase in PhaseRunner

**Alternatives Considered:**
1. Single LLM evaluator - Rejected due to cost and reliability concerns
2. No retry optimization - Rejected as inefficient
3. External evaluation service - Rejected as over-engineering for current scale
