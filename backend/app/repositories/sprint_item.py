"""Sprint item repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.sprint import SprintItem, SprintItemStatus


async def get_by_id(db: AsyncSession, item_id: UUID) -> SprintItem | None:
    """Get sprint item by ID."""
    return await db.get(SprintItem, item_id)


async def get_by_sprint(
    db: AsyncSession,
    *,
    sprint_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[SprintItem]:
    """Get sprint items for a sprint."""
    query = (
        select(SprintItem)
        .where(SprintItem.sprint_id == sprint_id)
        .order_by(SprintItem.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    sprint_id: UUID,
    title: str,
    description: str | None,
    status: SprintItemStatus,
    priority: int,
    estimate_points: int | None,
) -> SprintItem:
    """Create a sprint item."""
    item = SprintItem(
        sprint_id=sprint_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        estimate_points=estimate_points,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def update(
    db: AsyncSession,
    *,
    db_item: SprintItem,
    update_data: dict,
) -> SprintItem:
    """Update a sprint item."""
    for field, value in update_data.items():
        setattr(db_item, field, value)

    db.add(db_item)
    await db.flush()
    await db.refresh(db_item)
    return db_item


async def delete(db: AsyncSession, item_id: UUID) -> SprintItem | None:
    """Delete a sprint item."""
    item = await get_by_id(db, item_id)
    if item:
        await db.delete(item)
        await db.flush()
    return item
