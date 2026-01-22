"""Integration tests for sprint services."""

from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.db.models.sprint import SprintItemStatus, SprintStatus
from app.schemas.sprint import SprintCreate, SprintItemCreate, SprintUpdate
from app.services.sprint import SprintService

pytestmark = pytest.mark.integration


@pytest.mark.anyio
async def test_sprint_lifecycle(db_session):
    """Create, update, and delete a sprint with items."""
    service = SprintService(db_session)
    today = date.today()

    sprint = await service.create(
        SprintCreate(
            name="Integration Sprint",
            goal="Validate sprint integration flow",
            status=SprintStatus.PLANNED,
            start_date=today,
            end_date=today + timedelta(days=7),
        )
    )
    assert sprint.id is not None

    item = await service.create_item(
        sprint.id,
        SprintItemCreate(
            title="Ship sprint board",
            description="Cover sprint board end-to-end",
            status=SprintItemStatus.TODO,
            priority=1,
            estimate_points=3,
        ),
    )
    assert item.sprint_id == sprint.id

    updated = await service.update(
        sprint.id,
        SprintUpdate(status=SprintStatus.ACTIVE),
    )
    assert updated.status == SprintStatus.ACTIVE

    sprint_with_items = await service.get_with_items(sprint.id)
    assert sprint_with_items.items

    await service.delete(sprint.id)
    with pytest.raises(NotFoundError):
        await service.get_by_id(sprint.id)


@pytest.mark.anyio
async def test_sprint_create_with_missing_spec(db_session):
    """Creating a sprint with an unknown spec should fail."""
    service = SprintService(db_session)
    with pytest.raises(NotFoundError):
        await service.create(
            SprintCreate(
                name="Spec-linked sprint",
                spec_id=uuid4(),
            )
        )
