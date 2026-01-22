"""Evaluator registry for managing evaluators by phase.

This module provides a registry for organizing evaluators
by the phases they apply to.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runners.evaluators.protocol import Evaluator


class EvaluatorRegistry:
    """Registry for managing evaluators by phase and category."""

    def __init__(self) -> None:
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

    registry = EvaluatorRegistry()

    # Global evaluators (all phases)
    registry.register(RuffLintEvaluator())

    # Phase-specific evaluators
    registry.register(PytestEvaluator(), phases=["verification", "coding"])
    registry.register(TypeCheckEvaluator(), phases=["coding"])

    return registry
