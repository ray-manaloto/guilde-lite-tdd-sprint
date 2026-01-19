"""Agent run API routes for checkpointing and replay."""

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import AgentRunSvc, CurrentUser
from app.schemas.agent_run import (
    AgentCandidateCreate,
    AgentCandidateList,
    AgentCandidateRead,
    AgentCheckpointCreate,
    AgentCheckpointList,
    AgentCheckpointRead,
    AgentDecisionCreate,
    AgentDecisionRead,
    AgentRunCreate,
    AgentRunForkCreate,
    AgentRunList,
    AgentRunRead,
    AgentRunUpdate,
)

router = APIRouter()


@router.get("", response_model=AgentRunList)
async def list_runs(
    agent_run_service: AgentRunSvc,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    items, total = await agent_run_service.list_runs(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return AgentRunList(items=items, total=total)


@router.post("", response_model=AgentRunRead, status_code=status.HTTP_201_CREATED)
async def create_run(
    data: AgentRunCreate,
    agent_run_service: AgentRunSvc,
    current_user: CurrentUser,
):
    data.user_id = current_user.id
    return await agent_run_service.create_run(data)


@router.get("/{run_id}", response_model=AgentRunRead)
async def get_run(
    run_id: UUID,
    agent_run_service: AgentRunSvc,
    current_user: CurrentUser,
):
    return await agent_run_service.get_run(run_id)


@router.patch("/{run_id}", response_model=AgentRunRead)
async def update_run(
    run_id: UUID,
    data: AgentRunUpdate,
    agent_run_service: AgentRunSvc,
    current_user: CurrentUser,
):
    return await agent_run_service.update_run(run_id, data)


@router.post(
    "/{run_id}/forks",
    response_model=AgentRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def fork_run(
    run_id: UUID,
    data: AgentRunForkCreate,
    agent_run_service: AgentRunSvc,
    current_user: CurrentUser,
):
    return await agent_run_service.fork_run(run_id, data)


@router.post(
    "/{run_id}/candidates",
    response_model=AgentCandidateRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_candidate(
    run_id: UUID,
    data: AgentCandidateCreate,
    agent_run_service: AgentRunSvc,
    current_user: CurrentUser,
):
    return await agent_run_service.add_candidate(run_id, data)


@router.get("/{run_id}/candidates", response_model=AgentCandidateList)
async def list_candidates(
    run_id: UUID,
    agent_run_service: AgentRunSvc,
    current_user: CurrentUser,
):
    items, total = await agent_run_service.list_candidates(run_id)
    return AgentCandidateList(items=items, total=total)


@router.post(
    "/{run_id}/decision",
    response_model=AgentDecisionRead,
    status_code=status.HTTP_201_CREATED,
)
async def set_decision(
    run_id: UUID,
    data: AgentDecisionCreate,
    agent_run_service: AgentRunSvc,
    current_user: CurrentUser,
):
    return await agent_run_service.set_decision(run_id, data)


@router.get("/{run_id}/decision", response_model=AgentDecisionRead | None)
async def get_decision(
    run_id: UUID,
    agent_run_service: AgentRunSvc,
    current_user: CurrentUser,
):
    return await agent_run_service.get_decision(run_id)


@router.post(
    "/{run_id}/checkpoints",
    response_model=AgentCheckpointRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_checkpoint(
    run_id: UUID,
    data: AgentCheckpointCreate,
    agent_run_service: AgentRunSvc,
    current_user: CurrentUser,
):
    return await agent_run_service.add_checkpoint(run_id, data)


@router.get("/{run_id}/checkpoints", response_model=AgentCheckpointList)
async def list_checkpoints(
    run_id: UUID,
    agent_run_service: AgentRunSvc,
    current_user: CurrentUser,
):
    items, total = await agent_run_service.list_checkpoints(run_id)
    return AgentCheckpointList(items=items, total=total)
