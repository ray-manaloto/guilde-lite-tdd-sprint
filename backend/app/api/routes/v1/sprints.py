# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
"""Sprint routes."""

import logging

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select

from app.api.deps import DBSession, SprintSvc
from app.core.config import settings
from app.db.models.sprint import Sprint, SprintStatus
from app.schemas.sprint import (
    SprintCreate,
    SprintItemCreate,
    SprintItemRead,
    SprintItemUpdate,
    SprintRead,
    SprintReadWithItems,
    SprintUpdate,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=Page[SprintRead])
async def list_sprints(
    db: DBSession,
    status: SprintStatus | None = None,
):
    """List sprints with optional status filter."""
    query = select(Sprint).order_by(Sprint.created_at.desc())
    if status is not None:
        query = query.where(Sprint.status == status)
    return await paginate(db, query)


from app.runners.phase_runner import PhaseRunner


@router.post("", response_model=SprintRead, status_code=status.HTTP_201_CREATED)
async def create_sprint(
    sprint_in: SprintCreate,
    sprint_service: SprintSvc,
    background_tasks: BackgroundTasks,
):
    """Create a sprint."""
    sprint = await sprint_service.create(sprint_in)
    await sprint_service.db.commit() # Force commit so background task can see it
    return sprint


@router.post("/{sprint_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_sprint(
    sprint_id: UUID,
    sprint_service: SprintSvc,
    background_tasks: BackgroundTasks,
    mode: str | None = None,
):
    """Run the phase runner for a sprint."""
    await sprint_service.get_by_id(sprint_id)
    run_mode = (mode or settings.PHASE_RUNNER_MODE).lower()
    if run_mode == "sync":
        await PhaseRunner.start(sprint_id)
        return {"status": "completed", "mode": run_mode}
    background_tasks.add_task(PhaseRunner.start, sprint_id)
    return {"status": "started", "mode": run_mode}


@router.get("/{sprint_id}", response_model=SprintReadWithItems)
async def get_sprint(
    sprint_id: UUID,
    sprint_service: SprintSvc,
):
    """Get sprint by ID, including items."""
    return await sprint_service.get_with_items(sprint_id)


@router.patch("/{sprint_id}", response_model=SprintRead)
async def update_sprint(
    sprint_id: UUID,
    sprint_in: SprintUpdate,
    sprint_service: SprintSvc,
):
    """Update a sprint."""
    return await sprint_service.update(sprint_id, sprint_in)


@router.delete("/{sprint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sprint(
    sprint_id: UUID,
    sprint_service: SprintSvc,
):
    """Delete a sprint."""
    await sprint_service.delete(sprint_id)


@router.get("/{sprint_id}/items", response_model=Page[SprintItemRead])
async def list_sprint_items(
    sprint_id: UUID,
    sprint_service: SprintSvc,
):
    """List sprint items for a sprint."""
    items = await sprint_service.list_items(sprint_id)
    return paginate(items)


@router.post(
    "/{sprint_id}/items",
    response_model=SprintItemRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_sprint_item(
    sprint_id: UUID,
    item_in: SprintItemCreate,
    sprint_service: SprintSvc,
):
    """Create a sprint item."""
    return await sprint_service.create_item(sprint_id, item_in)


@router.patch("/{sprint_id}/items/{item_id}", response_model=SprintItemRead)
async def update_sprint_item(
    sprint_id: UUID,
    item_id: UUID,
    item_in: SprintItemUpdate,
    sprint_service: SprintSvc,
):
    """Update a sprint item."""
    return await sprint_service.update_item(sprint_id, item_id, item_in)


@router.delete("/{sprint_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sprint_item(
    sprint_id: UUID,
    item_id: UUID,
    sprint_service: SprintSvc,
):
    """Delete a sprint item."""
    await sprint_service.delete_item(sprint_id, item_id)
