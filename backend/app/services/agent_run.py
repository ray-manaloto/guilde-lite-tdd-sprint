"""Agent run service (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.telemetry import telemetry_span
from app.db.models.agent_run import AgentCandidate, AgentCheckpoint, AgentDecision, AgentRun
from app.repositories import agent_run_repo
from app.schemas.agent_run import (
    AgentCandidateCreate,
    AgentCheckpointCreate,
    AgentDecisionCreate,
    AgentRunCreate,
    AgentRunForkCreate,
    AgentRunUpdate,
)


class AgentRunService:
    """Service for agent run checkpointing and replay metadata."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _default_model_config() -> dict:
        return {
            "provider": settings.LLM_PROVIDER,
            "model": settings.LLM_MODEL,
            "temperature": settings.AI_TEMPERATURE,
        }

    async def get_run(self, run_id: UUID) -> AgentRun:
        run = await agent_run_repo.get_run_by_id(self.db, run_id)
        if not run:
            raise NotFoundError(message="Agent run not found", details={"run_id": str(run_id)})
        return run

    async def list_runs(
        self,
        user_id: UUID | None = None,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AgentRun], int]:
        items = await agent_run_repo.list_runs(
            self.db,
            user_id=user_id,
            skip=skip,
            limit=limit,
        )
        total = await agent_run_repo.count_runs(
            self.db,
            user_id=user_id,
        )
        return items, total

    async def create_run(
        self,
        data: AgentRunCreate,
    ) -> AgentRun:
        model_config = data.model_config_data or self._default_model_config()
        input_payload = data.input_payload or {}
        with telemetry_span("agent_run.create", status=data.status) as (trace_id, span_id):
            return await agent_run_repo.create_run(
                self.db,
                user_id=data.user_id,
                status=data.status,
                input_payload=input_payload,
                model_config=model_config,
                workspace_ref=data.workspace_ref,
                parent_run_id=data.parent_run_id,
                parent_checkpoint_id=data.parent_checkpoint_id,
                fork_label=data.fork_label,
                fork_reason=data.fork_reason,
                trace_id=trace_id,
                span_id=span_id,
            )

    async def fork_run(
        self,
        run_id: UUID,
        data: AgentRunForkCreate,
    ) -> AgentRun:
        parent_run = await self.get_run(run_id)
        checkpoint_state: dict = {}
        parent_checkpoint_id = data.checkpoint_id
        if data.checkpoint_id:
            checkpoint = await agent_run_repo.get_checkpoint_by_id(self.db, data.checkpoint_id)
            if not checkpoint or checkpoint.run_id != run_id:
                raise NotFoundError(
                    message="Checkpoint not found for run",
                    details={"run_id": str(run_id), "checkpoint_id": str(data.checkpoint_id)},
                )
            checkpoint_state = checkpoint.state or {}

        input_payload = (
            data.input_payload or checkpoint_state.get("input_payload") or parent_run.input_payload
        )
        model_config = (
            data.model_config_data
            or checkpoint_state.get("model_config")
            or parent_run.model_config
            or self._default_model_config()
        )
        workspace_ref = data.workspace_ref or parent_run.workspace_ref

        with telemetry_span(
            "agent_run.fork",
            parent_run_id=str(run_id),
            parent_checkpoint_id=str(parent_checkpoint_id) if parent_checkpoint_id else None,
        ) as (trace_id, span_id):
            return await agent_run_repo.create_run(
                self.db,
                user_id=parent_run.user_id,
                status=data.status,
                input_payload=input_payload,
                model_config=model_config,
                workspace_ref=workspace_ref,
                parent_run_id=run_id,
                parent_checkpoint_id=parent_checkpoint_id,
                fork_label=data.fork_label,
                fork_reason=data.fork_reason,
                trace_id=trace_id,
                span_id=span_id,
            )

    async def update_run(self, run_id: UUID, data: AgentRunUpdate) -> AgentRun:
        run = await self.get_run(run_id)
        update_data = data.model_dump(exclude_unset=True)
        return await agent_run_repo.update_run(self.db, db_run=run, update_data=update_data)

    async def add_candidate(
        self,
        run_id: UUID,
        data: AgentCandidateCreate,
    ) -> AgentCandidate:
        await self.get_run(run_id)
        provider = data.provider or settings.LLM_PROVIDER
        model_name = data.model_name or settings.LLM_MODEL
        with telemetry_span(
            "agent_run.candidate",
            run_id=str(run_id),
            agent_name=data.agent_name,
            provider=provider,
            model_name=model_name,
        ) as (trace_id, span_id):
            return await agent_run_repo.create_candidate(
                self.db,
                run_id=run_id,
                agent_name=data.agent_name,
                provider=provider,
                model_name=model_name,
                output=data.output,
                tool_calls=data.tool_calls,
                metrics=data.metrics,
                trace_id=trace_id,
                span_id=span_id,
            )

    async def list_candidates(self, run_id: UUID) -> tuple[list[AgentCandidate], int]:
        await self.get_run(run_id)
        items = await agent_run_repo.list_candidates(self.db, run_id)
        return items, len(items)

    async def set_decision(
        self,
        run_id: UUID,
        data: AgentDecisionCreate,
    ) -> AgentDecision:
        await self.get_run(run_id)
        model_name = data.model_name or settings.JUDGE_LLM_MODEL
        with telemetry_span("agent_run.decision", run_id=str(run_id)) as (trace_id, span_id):
            existing = await agent_run_repo.get_decision_by_run(self.db, run_id)
            if existing:
                update_data = data.model_dump(exclude_unset=True)
                update_data["model_name"] = model_name
                update_data["trace_id"] = trace_id
                update_data["span_id"] = span_id
                return await agent_run_repo.update_decision(
                    self.db, db_decision=existing, update_data=update_data
                )
            return await agent_run_repo.create_decision(
                self.db,
                run_id=run_id,
                candidate_id=data.candidate_id,
                score=data.score,
                rationale=data.rationale,
                model_name=model_name,
                trace_id=trace_id,
                span_id=span_id,
            )

    async def get_decision(self, run_id: UUID) -> AgentDecision | None:
        await self.get_run(run_id)
        return await agent_run_repo.get_decision_by_run(self.db, run_id)

    async def add_checkpoint(
        self,
        run_id: UUID,
        data: AgentCheckpointCreate,
    ) -> AgentCheckpoint:
        run = await self.get_run(run_id)
        state = data.state or {}
        state.setdefault("input_payload", run.input_payload)
        state.setdefault("model_config", run.model_config or self._default_model_config())
        with telemetry_span("agent_run.checkpoint", run_id=str(run_id)) as (trace_id, span_id):
            return await agent_run_repo.create_checkpoint(
                self.db,
                run_id=run_id,
                sequence=data.sequence,
                label=data.label,
                state=state,
                workspace_ref=data.workspace_ref or run.workspace_ref,
                trace_id=trace_id,
                span_id=span_id,
            )

    async def list_checkpoints(self, run_id: UUID) -> tuple[list[AgentCheckpoint], int]:
        await self.get_run(run_id)
        items = await agent_run_repo.list_checkpoints(self.db, run_id)
        return items, len(items)

    async def get_checkpoint(self, checkpoint_id: UUID) -> AgentCheckpoint:
        checkpoint = await agent_run_repo.get_checkpoint_by_id(self.db, checkpoint_id)
        if not checkpoint:
            raise NotFoundError(
                message="Agent checkpoint not found",
                details={"checkpoint_id": str(checkpoint_id)},
            )
        return checkpoint
