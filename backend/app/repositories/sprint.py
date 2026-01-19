"""Sprint repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.sprint import Sprint, SprintStatus


async def get_by_id(db: AsyncSession, sprint_id: UUID) -> Sprint | None:
    """Get sprint by ID."""
    return await db.get(Sprint, sprint_id)


async def get_by_id_with_items(db: AsyncSession, sprint_id: UUID) -> Sprint | None:
    """Get sprint by ID with items loaded."""
    result = await db.execute(
        select(Sprint)
        .options(selectinload(Sprint.items))
        .where(Sprint.id == sprint_id)
    )
    return result.scalars().first()


async def get_multi(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    status: SprintStatus | None = None,
) -> list[Sprint]:
    """Get multiple sprints with optional status filter."""
    query = select(Sprint).order_by(Sprint.created_at.desc())
    if status is not None:
        query = query.where(Sprint.status == status)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    name: str,
    goal: str | None = None,
    status: SprintStatus = SprintStatus.PLANNED,
    start_date=None,
    end_date=None,
) -> Sprint:
    """Create a new sprint."""
    sprint = Sprint(
        name=name,
        goal=goal,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
    db.add(sprint)
    await db.flush()
    await db.refresh(sprint)
    return sprint


async def update(
    db: AsyncSession,
    *,
    db_sprint: Sprint,
    update_data: dict,
) -> Sprint:
    """Update a sprint."""
    for field, value in update_data.items():
        setattr(db_sprint, field, value)

    db.add(db_sprint)
    await db.flush()
    await db.refresh(db_sprint)
    return db_sprint


async def delete(db: AsyncSession, sprint_id: UUID) -> Sprint | None:
    """Delete a sprint."""
    sprint = await get_by_id(db, sprint_id)
    if sprint:
        await db.delete(sprint)
        await db.flush()
    return sprint
