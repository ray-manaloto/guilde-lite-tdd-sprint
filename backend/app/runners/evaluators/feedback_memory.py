"""Feedback memory for retry optimization.

Stores retry history and accumulated context for the optimizer,
implementing exponentially increasing detail for successive attempts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from app.runners.evaluators.protocol import EvaluationResult


@dataclass
class AttemptRecord:
    """Record of a single evaluation attempt."""

    attempt_number: int
    started_at: datetime
    completed_at: datetime | None = None
    phase_output: str = ""
    evaluation_results: list[EvaluationResult] = field(default_factory=list)
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
        return sum(e.score for e in self.evaluation_results) / len(
            self.evaluation_results
        )

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
        evaluation_results: list[EvaluationResult],
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
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
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
            context["recurring_issues"] = self.accumulated_insights.get(
                "recurring_issues", []
            )
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
            analysis_parts.append(
                f"- Recurring issues ({len(recurring)}): {', '.join(recurring[:3])}"
            )

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
            lines.append(
                "**CRITICAL: This is your FINAL attempt. Address ALL issues below.**"
            )
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
