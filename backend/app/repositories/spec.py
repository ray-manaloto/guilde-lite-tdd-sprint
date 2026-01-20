"""Spec repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.spec import Spec, SpecStatus


async def get_by_id(db: AsyncSession, spec_id: UUID) -> Spec | None:
    """Get spec by ID."""
    return await db.get(Spec, spec_id)


async def get_multi(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    status: SpecStatus | None = None,
) -> list[Spec]:
    """Get multiple specs with optional status filter."""
    query = select(Spec).order_by(Spec.created_at.desc())
    if status is not None:
        query = query.where(Spec.status == status)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    title: str,
    task: str,
    complexity,
    status,
    phases: list[str],
    artifacts: dict,
    user_id: UUID | None = None,
) -> Spec:
    """Create a new spec."""
    spec = Spec(
        user_id=user_id,
        title=title,
        task=task,
        complexity=complexity,
        status=status,
        phases=phases,
        artifacts=artifacts,
    )
    db.add(spec)
    await db.flush()
    await db.refresh(spec)
    return spec


async def update(
    db: AsyncSession,
    *,
    db_spec: Spec,
    update_data: dict,
) -> Spec:
    """Update a spec."""
    for field, value in update_data.items():
        setattr(db_spec, field, value)
    db.add(db_spec)
    await db.flush()
    await db.refresh(db_spec)
    return db_spec
