"""TDD run API routes for multi-provider subagents."""

from fastapi import APIRouter, status

from app.api.deps import AgentTddSvc, CurrentUser
from app.schemas.agent_tdd import AgentTddRunCreate, AgentTddRunResult

router = APIRouter()


@router.post("", response_model=AgentTddRunResult, status_code=status.HTTP_201_CREATED)
async def execute_tdd_run(
    data: AgentTddRunCreate,
    agent_tdd_service: AgentTddSvc,
    current_user: CurrentUser,
):
    return await agent_tdd_service.execute(data, user_id=current_user.id)
