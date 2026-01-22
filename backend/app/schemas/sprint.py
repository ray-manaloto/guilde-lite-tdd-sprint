"""Sprint schemas."""

from datetime import date
from uuid import UUID

from pydantic import Field

from app.db.models.sprint import SprintItemStatus, SprintStatus
from app.schemas.base import BaseSchema, TimestampSchema


class SprintBase(BaseSchema):
    """Base sprint schema with shared fields."""

    spec_id: UUID | None = Field(default=None, description="Linked spec ID")
    track_id: str | None = Field(default=None, description="Linked Conductor track ID")
    name: str = Field(max_length=255, description="Sprint name")
    goal: str | None = Field(default=None, description="Sprint goal")
    status: SprintStatus = Field(default=SprintStatus.PLANNED)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)


class SprintCreate(BaseSchema):
    """Schema for creating a sprint."""

    spec_id: UUID | None = Field(default=None)
    track_id: str | None = Field(default=None)
    name: str = Field(max_length=255)
    goal: str | None = Field(default=None)
    status: SprintStatus = Field(default=SprintStatus.PLANNED)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)


class SprintUpdate(BaseSchema):
    """Schema for updating a sprint."""

    spec_id: UUID | None = Field(default=None)
    track_id: str | None = Field(default=None)
    name: str | None = Field(default=None, max_length=255)
    goal: str | None = Field(default=None)
    status: SprintStatus | None = Field(default=None)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)


class SprintItemBase(BaseSchema):
    """Base sprint item schema."""

    title: str = Field(max_length=255)
    description: str | None = Field(default=None)
    status: SprintItemStatus = Field(default=SprintItemStatus.TODO)
    priority: int = Field(default=2, ge=1, le=3)
    estimate_points: int | None = Field(default=None, ge=0)


class SprintItemCreate(SprintItemBase):
    """Schema for creating a sprint item."""

    pass


class SprintItemUpdate(BaseSchema):
    """Schema for updating a sprint item."""

    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None)
    status: SprintItemStatus | None = Field(default=None)
    priority: int | None = Field(default=None, ge=1, le=3)
    estimate_points: int | None = Field(default=None, ge=0)


class SprintItemRead(SprintItemBase, TimestampSchema):
    """Schema for reading a sprint item."""

    id: UUID
    sprint_id: UUID


class SprintRead(SprintBase, TimestampSchema):
    """Schema for reading a sprint."""

    id: UUID


class SprintReadWithItems(SprintRead):
    """Schema for reading a sprint with items."""

    items: list[SprintItemRead] = Field(default_factory=list)
