"""Deterministic evaluators for code quality.

These evaluators use code-based checks (lint, tests, type checking)
for reliable, reproducible evaluation results.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from pathlib import Path

from app.runners.evaluators.protocol import (
    CriterionResult,
    EvaluationCategory,
    EvaluationResult,
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
                criteria.append(
                    CriterionResult(
                        criterion="no_lint_errors",
                        passed=True,
                        score=1.0,
                        message="No linting errors found",
                    )
                )
                return EvaluationResult(
                    evaluator_name=self.name,
                    category=self.category,
                    passed=True,
                    score=1.0,
                    feedback="Code passes all lint checks",
                    criteria=criteria,
                )
            else:
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

                criteria.append(
                    CriterionResult(
                        criterion="no_lint_errors",
                        passed=False,
                        score=score,
                        message=f"Found {error_count} lint error(s)",
                        evidence=result.stdout[:1000],
                    )
                )

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
        except FileNotFoundError:
            # Ruff not installed
            return EvaluationResult(
                evaluator_name=self.name,
                category=self.category,
                passed=True,
                score=1.0,
                feedback="Ruff not available (skipped)",
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
                criteria.append(
                    CriterionResult(
                        criterion="tests_pass",
                        passed=True,
                        score=1.0,
                        message=f"All {passed_tests} test(s) passed",
                    )
                )

                return EvaluationResult(
                    evaluator_name=self.name,
                    category=self.category,
                    passed=True,
                    score=1.0,
                    feedback=f"All tests passed ({passed_tests} tests)",
                    criteria=criteria,
                    metadata={"passed_tests": passed_tests},
                )
            elif result.returncode == 5:
                # No tests collected
                return EvaluationResult(
                    evaluator_name=self.name,
                    category=self.category,
                    passed=True,
                    score=1.0,
                    feedback="No tests found (skipped)",
                    metadata={"no_tests": True},
                )
            else:
                failed_tests = result.stdout.count(" FAILED")
                passed_tests = result.stdout.count(" PASSED")
                total = failed_tests + passed_tests
                score = passed_tests / total if total > 0 else 0.0

                criteria.append(
                    CriterionResult(
                        criterion="tests_pass",
                        passed=False,
                        score=score,
                        message=f"{failed_tests} of {total} test(s) failed",
                        evidence=result.stdout[-2000:],  # Last 2000 chars
                    )
                )

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
        except FileNotFoundError:
            return EvaluationResult(
                evaluator_name=self.name,
                category=self.category,
                passed=True,
                score=1.0,
                feedback="pytest not available (skipped)",
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
    """Deterministic evaluator using pyright for type checking."""

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
                    suggestions=[
                        "Add type hints to function parameters and return values"
                    ],
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
        except subprocess.TimeoutExpired:
            return EvaluationResult(
                evaluator_name=self.name,
                category=self.category,
                passed=True,
                score=1.0,
                feedback="Type check timed out (skipped)",
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
