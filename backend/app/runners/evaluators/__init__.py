"""Evaluator system for PhaseRunner.

This module provides the evaluator-optimizer pattern for structured
evaluation of phase outputs with feedback-driven retry loops.
"""

from app.runners.evaluators.feedback_memory import AttemptRecord, FeedbackMemory
from app.runners.evaluators.protocol import (
    CriterionResult,
    EvaluationCategory,
    EvaluationResult,
    Evaluator,
)
from app.runners.evaluators.registry import EvaluatorRegistry, create_default_registry

__all__ = [
    "AttemptRecord",
    "CriterionResult",
    "EvaluationCategory",
    "EvaluationResult",
    "Evaluator",
    "EvaluatorRegistry",
    "FeedbackMemory",
    "create_default_registry",
]
