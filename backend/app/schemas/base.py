"""Base Pydantic schemas."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, field_serializer


def serialize_datetime(dt: datetime) -> str:
    """Serialize datetime to ISO format with timezone.

    Ensures all datetimes have explicit timezone (defaults to UTC).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.isoformat()


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    @field_serializer("*", when_used="json")
    def _serialize_fields(self, value: Any):
        if isinstance(value, datetime):
            return serialize_datetime(value)
        return value

    def serializable_dict(self, **kwargs: Any) -> dict[str, Any]:
        """Return a dict with only JSON-serializable fields."""
        return self.model_dump(mode="json", **kwargs)


class TimestampSchema(BaseModel):
    """Schema with timestamp fields."""

    created_at: datetime
    updated_at: datetime | None = None


class BaseResponse(BaseModel):
    """Standard API response."""

    success: bool = True
    message: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = False
    error: str
    detail: str | None = None
    code: str | None = None
