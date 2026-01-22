"""Tests for ConductorFileService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.conductor_files import ConductorFileService


@pytest.mark.anyio
async def test_upsert_creates_new_file():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    service = ConductorFileService(db)
    record = await service.upsert_file(
        track_id="track-1",
        path="conductor/tracks/track-1/spec.md",
        kind="spec",
        content="# Spec",
        metadata={"source": "test"},
    )

    assert record.track_id == "track-1"
    assert record.path.endswith("spec.md")
    assert record.content == "# Spec"
    db.add.assert_called_once()
    db.flush.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.anyio
async def test_upsert_updates_existing_file():
    existing = MagicMock()
    existing.track_id = "track-1"
    existing.path = "conductor/tracks/track-1/spec.md"
    existing.content = "old"
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: existing))
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    service = ConductorFileService(db)
    record = await service.upsert_file(
        track_id="track-1",
        path="conductor/tracks/track-1/spec.md",
        kind="spec",
        content="# Spec updated",
        metadata=None,
    )

    assert record is existing
    assert record.content == "# Spec updated"
    db.add.assert_called_once_with(existing)
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(existing)
