"""Workflow routes for sprint visualization."""

from uuid import UUID

from fastapi import APIRouter

from app.schemas.workflow import (
    ArtifactsListResponse,
    TimelineResponse,
    WorkflowResponse,
)
from app.services.workflow import WorkflowService

router = APIRouter()


def get_workflow_service() -> WorkflowService:
    """Create WorkflowService instance."""
    return WorkflowService()


@router.get("/{sprint_id}/workflow", response_model=WorkflowResponse)
async def get_workflow(sprint_id: UUID) -> WorkflowResponse:
    """Get full workflow state for a sprint.

    Returns the complete workflow state including:
    - Manifest metadata (status, current phase, timestamps)
    - All phase records with candidates and judge results
    - Full timeline of events
    - Aggregated token usage and cost metrics
    """
    service = get_workflow_service()
    return await service.get_workflow(sprint_id)


@router.get("/{sprint_id}/timeline", response_model=TimelineResponse)
async def get_timeline(sprint_id: UUID) -> TimelineResponse:
    """Get timeline events for a sprint.

    Returns a chronological list of all workflow events with:
    - Event type and timestamp
    - Associated phase and checkpoint
    - Trace links for debugging
    """
    service = get_workflow_service()
    return await service.get_timeline(sprint_id)


@router.get("/{sprint_id}/artifacts", response_model=ArtifactsListResponse)
async def list_artifacts(sprint_id: UUID) -> ArtifactsListResponse:
    """List all artifacts for a sprint.

    Returns information about all files in the sprint directory:
    - File paths relative to sprint directory
    - File types (json, markdown, python, etc.)
    - File sizes and creation timestamps
    """
    service = get_workflow_service()
    return await service.list_artifacts(sprint_id)
