"""Evaluator protocol and result types.

This module defines the interface for all evaluation functions,
supporting both deterministic (code-based) and LLM-based evaluators.
"""

from __future__ import annotations

from abc import abstractmethod
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class EvaluationCategory(StrEnum):
    """Categories for evaluation criteria."""

    FUNCTIONALITY = "functionality"
    CORRECTNESS = "correctness"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    COMPLIANCE = "compliance"
    TEST_COVERAGE = "test_coverage"


class CriterionResult(BaseModel):
    """Result for a single evaluation criterion."""

    criterion: str = Field(..., description="Name of the criterion evaluated")
    passed: bool = Field(..., description="Whether this criterion passed")
    score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score from 0.0 to 1.0",
    )
    message: str = Field(default="", description="Explanation of the result")
    evidence: str | None = Field(
        default=None,
        description="Supporting evidence (e.g., test output, lint errors)",
    )


class EvaluationResult(BaseModel):
    """Standardized output from any evaluator."""

    evaluator_name: str = Field(
        ..., description="Name of the evaluator that produced this result"
    )
    category: EvaluationCategory = Field(..., description="Category of evaluation")
    passed: bool = Field(..., description="Overall pass/fail status")
    score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Aggregate score from 0.0 (fail) to 1.0 (perfect)",
    )
    feedback: str = Field(..., description="Human-readable feedback for the agent")
    criteria: list[CriterionResult] = Field(
        default_factory=list,
        description="Individual criterion results",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Specific suggestions for improvement",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional evaluator-specific metadata",
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
