"""Sprint service (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.db.models.sprint import Sprint, SprintItem
from app.repositories import spec_repo, sprint_repo, sprint_item_repo
from app.schemas.sprint import (
    SprintCreate,
    SprintItemCreate,
    SprintItemUpdate,
    SprintUpdate,
)


class SprintService:
    """Service for sprint-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _validate_dates(self, start_date, end_date) -> None:
        if start_date and end_date and start_date > end_date:
            raise ValidationError(
                message="Sprint start_date must be before end_date",
                details={"start_date": str(start_date), "end_date": str(end_date)},
            )

    async def get_by_id(self, sprint_id: UUID) -> Sprint:
        """Get sprint by ID.

        Raises:
            NotFoundError: If sprint does not exist.
        """
        sprint = await sprint_repo.get_by_id(self.db, sprint_id)
        if not sprint:
            raise NotFoundError(message="Sprint not found", details={"sprint_id": str(sprint_id)})
        return sprint

    async def get_with_items(self, sprint_id: UUID) -> Sprint:
        """Get sprint by ID with items.

        Raises:
            NotFoundError: If sprint does not exist.
        """
        sprint = await sprint_repo.get_by_id_with_items(self.db, sprint_id)
        if not sprint:
            raise NotFoundError(message="Sprint not found", details={"sprint_id": str(sprint_id)})
        return sprint

    async def get_multi(self, *, skip: int = 0, limit: int = 100, status=None) -> list[Sprint]:
        """Get multiple sprints."""
        return await sprint_repo.get_multi(self.db, skip=skip, limit=limit, status=status)

    async def create(self, sprint_in: SprintCreate) -> Sprint:
        """Create a new sprint."""
        self._validate_dates(sprint_in.start_date, sprint_in.end_date)
        if sprint_in.spec_id:
            spec = await spec_repo.get_by_id(self.db, sprint_in.spec_id)
            if not spec:
                raise NotFoundError(message="Spec not found", details={"spec_id": str(sprint_in.spec_id)})
        return await sprint_repo.create(
            self.db,
            spec_id=sprint_in.spec_id,
            name=sprint_in.name,
            goal=sprint_in.goal,
            status=sprint_in.status,
            start_date=sprint_in.start_date,
            end_date=sprint_in.end_date,
        )

    async def update(self, sprint_id: UUID, sprint_in: SprintUpdate) -> Sprint:
        """Update a sprint.

        Raises:
            NotFoundError: If sprint does not exist.
        """
        sprint = await self.get_by_id(sprint_id)
        update_data = sprint_in.model_dump(exclude_unset=True)
        spec_id = update_data.get("spec_id")
        if spec_id:
            spec = await spec_repo.get_by_id(self.db, spec_id)
            if not spec:
                raise NotFoundError(message="Spec not found", details={"spec_id": str(spec_id)})
        start_date = update_data.get("start_date", sprint.start_date)
        end_date = update_data.get("end_date", sprint.end_date)
        self._validate_dates(start_date, end_date)
        return await sprint_repo.update(self.db, db_sprint=sprint, update_data=update_data)

    async def delete(self, sprint_id: UUID) -> Sprint:
        """Delete a sprint.

        Raises:
            NotFoundError: If sprint does not exist.
        """
        sprint = await sprint_repo.delete(self.db, sprint_id)
        if not sprint:
            raise NotFoundError(message="Sprint not found", details={"sprint_id": str(sprint_id)})
        return sprint

    async def list_items(self, sprint_id: UUID, *, skip: int = 0, limit: int = 100) -> list[SprintItem]:
        """List items for a sprint."""
        await self.get_by_id(sprint_id)
        return await sprint_item_repo.get_by_sprint(self.db, sprint_id=sprint_id, skip=skip, limit=limit)

    async def create_item(self, sprint_id: UUID, item_in: SprintItemCreate) -> SprintItem:
        """Create a sprint item."""
        await self.get_by_id(sprint_id)
        return await sprint_item_repo.create(
            self.db,
            sprint_id=sprint_id,
            title=item_in.title,
            description=item_in.description,
            status=item_in.status,
            priority=item_in.priority,
            estimate_points=item_in.estimate_points,
        )

    async def update_item(
        self,
        sprint_id: UUID,
        item_id: UUID,
        item_in: SprintItemUpdate,
    ) -> SprintItem:
        """Update a sprint item.

        Raises:
            NotFoundError: If sprint item does not exist.
        """
        await self.get_by_id(sprint_id)
        item = await sprint_item_repo.get_by_id(self.db, item_id)
        if not item or item.sprint_id != sprint_id:
            raise NotFoundError(message="Sprint item not found", details={"item_id": str(item_id)})
        update_data = item_in.model_dump(exclude_unset=True)
        return await sprint_item_repo.update(self.db, db_item=item, update_data=update_data)

    async def delete_item(self, sprint_id: UUID, item_id: UUID) -> SprintItem:
        """Delete a sprint item.

        Raises:
            NotFoundError: If sprint item does not exist.
        """
        await self.get_by_id(sprint_id)
        item = await sprint_item_repo.get_by_id(self.db, item_id)
        if not item or item.sprint_id != sprint_id:
            raise NotFoundError(message="Sprint item not found", details={"item_id": str(item_id)})
        await sprint_item_repo.delete(self.db, item_id)
        return item
