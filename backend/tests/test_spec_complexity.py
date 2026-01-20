"""Tests for spec complexity assessment."""

from unittest.mock import AsyncMock

from app.db.models.spec import SpecComplexity
from app.services.spec import SpecService


def test_assess_complexity_simple():
    service = SpecService(AsyncMock())
    assessment = service.assess_complexity("Fix button label typo in header.")
    assert assessment.complexity == SpecComplexity.SIMPLE
    assert "spec" in assessment.phases


def test_assess_complexity_complex():
    service = SpecService(AsyncMock())
    assessment = service.assess_complexity(
        "Integrate OAuth authentication and add database migration for tokens."
    )
    assert assessment.complexity == SpecComplexity.COMPLEX
    assert "planning" in assessment.phases


def test_assess_complexity_standard():
    service = SpecService(AsyncMock())
    assessment = service.assess_complexity("Add a sprint summary to the dashboard.")
    assert assessment.complexity == SpecComplexity.STANDARD
