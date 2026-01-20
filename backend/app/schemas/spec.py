"""Spec workflow schemas."""

from typing import Any
from uuid import UUID

from pydantic import Field

from app.db.models.spec import SpecComplexity, SpecStatus
from app.schemas.base import BaseSchema, TimestampSchema


class SpecCreate(BaseSchema):
    """Schema for creating a spec."""

    title: str | None = Field(default=None, max_length=255)
    task: str = Field(min_length=1)


class SpecRead(BaseSchema, TimestampSchema):
    """Schema for reading a spec."""

    id: UUID
    user_id: UUID | None = None
    title: str
    task: str
    complexity: SpecComplexity
    status: SpecStatus
    phases: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)


class SpecPlanningQuestion(BaseSchema):
    """Planning interview question."""

    question: str
    rationale: str | None = None


class SpecPlanningAnswer(BaseSchema):
    """Planning interview answer."""

    question: str
    answer: str


class SpecPlanningRead(BaseSchema):
    """Planning interview payload stored in artifacts."""

    status: str
    questions: list[SpecPlanningQuestion] = Field(default_factory=list)
    answers: list[SpecPlanningAnswer] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SpecPlanningCreate(BaseSchema):
    """Request schema for planning interview creation."""

    title: str | None = Field(default=None, max_length=255)
    task: str = Field(min_length=1)
    max_questions: int = Field(default=5, ge=1, le=10)


class SpecPlanningAnswers(BaseSchema):
    """Request schema for planning interview answers."""

    answers: list[SpecPlanningAnswer] = Field(default_factory=list)


class SpecValidationRead(BaseSchema):
    """Schema for spec validation results."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SpecValidationResponse(BaseSchema):
    """Response schema for spec validation."""

    spec: SpecRead
    validation: SpecValidationRead


class SpecPlanningResponse(BaseSchema):
    """Response schema for planning interview endpoints."""

    spec: SpecRead
    planning: SpecPlanningRead
