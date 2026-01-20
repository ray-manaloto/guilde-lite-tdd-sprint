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


class SpecValidationRead(BaseSchema):
    """Schema for spec validation results."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SpecValidationResponse(BaseSchema):
    """Response schema for spec validation."""

    spec: SpecRead
    validation: SpecValidationRead
