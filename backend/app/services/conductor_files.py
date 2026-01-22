"""Conductor file mirroring service."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conductor_file import ConductorFile
from app.repositories import conductor_files as conductor_file_repo


@dataclass
class ConductorFileService:
    """Service for mirroring Conductor files into the database."""

    db: AsyncSession

    async def upsert_file(
        self,
        *,
        track_id: str,
        path: str,
        kind: str,
        content: str,
        metadata: dict | None,
    ) -> ConductorFile:
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        record = await conductor_file_repo.get_by_path(self.db, path)
        metadata = metadata or {}

        if record:
            return await conductor_file_repo.update(
                self.db,
                record=record,
                content=content,
                content_hash=content_hash,
                metadata=metadata,
            )

        return await conductor_file_repo.create(
            self.db,
            track_id=track_id,
            path=path,
            kind=kind,
            content=content,
            content_hash=content_hash,
            metadata=metadata,
        )
