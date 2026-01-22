"""Conductor file repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conductor_file import ConductorFile


async def get_by_path(db: AsyncSession, path: str) -> ConductorFile | None:
    result = await db.execute(select(ConductorFile).where(ConductorFile.path == path))
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    track_id: str,
    path: str,
    kind: str,
    content: str,
    content_hash: str,
    metadata: dict,
) -> ConductorFile:
    record = ConductorFile(
        track_id=track_id,
        path=path,
        kind=kind,
        content=content,
        content_hash=content_hash,
        metadata_json=metadata,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def update(
    db: AsyncSession,
    *,
    record: ConductorFile,
    content: str,
    content_hash: str,
    metadata: dict,
) -> ConductorFile:
    record.content = content
    record.content_hash = content_hash
    record.metadata_json = metadata
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record
