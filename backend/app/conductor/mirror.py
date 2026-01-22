"""Helpers for mirroring Conductor files into the database."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.conductor_files import ConductorFileService


async def mirror_file(
    db: AsyncSession,
    *,
    track_id: str,
    path: str,
    kind: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> Any:
    """Persist a Conductor file snapshot using the service layer."""
    service = ConductorFileService(db)
    return await service.upsert_file(
        track_id=track_id,
        path=path,
        kind=kind,
        content=content,
        metadata=metadata,
    )
