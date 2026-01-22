"""Tests for Conductor mirror helpers."""

from unittest.mock import AsyncMock

import pytest

from app.conductor.mirror import mirror_file


class FakeService:
    def __init__(self, db):
        self.db = db
        self.calls = []

    async def upsert_file(self, *, track_id: str, path: str, kind: str, content: str, metadata):
        self.calls.append(
            {
                "track_id": track_id,
                "path": path,
                "kind": kind,
                "content": content,
                "metadata": metadata,
            }
        )
        return "ok"


@pytest.mark.anyio
async def test_mirror_file_uses_service(monkeypatch):
    db = AsyncMock()
    service = FakeService(db)

    monkeypatch.setattr(
        "app.conductor.mirror.ConductorFileService",
        lambda db_session: service,
    )

    result = await mirror_file(
        db,
        track_id="track-1",
        path="conductor/tracks/track-1/spec.md",
        kind="spec",
        content="# Spec",
        metadata={"source": "test"},
    )

    assert result == "ok"
    assert service.calls
    assert service.calls[0]["track_id"] == "track-1"
