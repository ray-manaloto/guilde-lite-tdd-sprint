"""Agent run repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_run import (
    AgentCandidate,
    AgentCheckpoint,
    AgentDecision,
    AgentRun,
)


async def get_run_by_id(db: AsyncSession, run_id: UUID) -> AgentRun | None:
    """Get a run by ID."""
    return await db.get(AgentRun, run_id)


async def list_runs(
    db: AsyncSession,
    user_id: UUID | None = None,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[AgentRun]:
    """List runs with pagination."""
    query = select(AgentRun)
    if user_id:
        query = query.where(AgentRun.user_id == user_id)
    query = query.order_by(AgentRun.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_runs(
    db: AsyncSession,
    user_id: UUID | None = None,
) -> int:
    """Count runs."""
    query = select(func.count(AgentRun.id))
    if user_id:
        query = query.where(AgentRun.user_id == user_id)
    result = await db.execute(query)
    return result.scalar() or 0


async def create_run(
    db: AsyncSession,
    *,
    user_id: UUID | None = None,
    status: str = "pending",
    input_payload: dict | None = None,
    model_config: dict | None = None,
    workspace_ref: str | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
) -> AgentRun:
    """Create a new run."""
    run = AgentRun(
        user_id=user_id,
        status=status,
        input_payload=input_payload or {},
        model_config=model_config or {},
        workspace_ref=workspace_ref,
        trace_id=trace_id,
        span_id=span_id,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)
    return run


async def update_run(
    db: AsyncSession,
    *,
    db_run: AgentRun,
    update_data: dict,
) -> AgentRun:
    """Update a run."""
    for field, value in update_data.items():
        setattr(db_run, field, value)
    db.add(db_run)
    await db.flush()
    await db.refresh(db_run)
    return db_run


async def create_candidate(
    db: AsyncSession,
    *,
    run_id: UUID,
    agent_name: str,
    provider: str,
    model_name: str,
    output: str | None = None,
    tool_calls: dict | None = None,
    metrics: dict | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
) -> AgentCandidate:
    """Create a subagent candidate result."""
    candidate = AgentCandidate(
        run_id=run_id,
        agent_name=agent_name,
        provider=provider,
        model_name=model_name,
        output=output,
        tool_calls=tool_calls or {},
        metrics=metrics or {},
        trace_id=trace_id,
        span_id=span_id,
    )
    db.add(candidate)
    await db.flush()
    await db.refresh(candidate)
    return candidate


async def list_candidates(
    db: AsyncSession,
    run_id: UUID,
) -> list[AgentCandidate]:
    """List candidates for a run."""
    query = select(AgentCandidate).where(AgentCandidate.run_id == run_id)
    query = query.order_by(AgentCandidate.created_at.asc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_decision_by_run(
    db: AsyncSession,
    run_id: UUID,
) -> AgentDecision | None:
    """Get judge decision for a run."""
    query = select(AgentDecision).where(AgentDecision.run_id == run_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_decision(
    db: AsyncSession,
    *,
    run_id: UUID,
    candidate_id: UUID | None = None,
    score: float | None = None,
    rationale: str | None = None,
    model_name: str | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
) -> AgentDecision:
    """Create a judge decision."""
    decision = AgentDecision(
        run_id=run_id,
        candidate_id=candidate_id,
        score=score,
        rationale=rationale,
        model_name=model_name,
        trace_id=trace_id,
        span_id=span_id,
    )
    db.add(decision)
    await db.flush()
    await db.refresh(decision)
    return decision


async def update_decision(
    db: AsyncSession,
    *,
    db_decision: AgentDecision,
    update_data: dict,
) -> AgentDecision:
    """Update a judge decision."""
    for field, value in update_data.items():
        setattr(db_decision, field, value)
    db.add(db_decision)
    await db.flush()
    await db.refresh(db_decision)
    return db_decision


async def create_checkpoint(
    db: AsyncSession,
    *,
    run_id: UUID,
    sequence: int = 0,
    label: str | None = None,
    state: dict | None = None,
    workspace_ref: str | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
) -> AgentCheckpoint:
    """Create a checkpoint."""
    checkpoint = AgentCheckpoint(
        run_id=run_id,
        sequence=sequence,
        label=label,
        state=state or {},
        workspace_ref=workspace_ref,
        trace_id=trace_id,
        span_id=span_id,
    )
    db.add(checkpoint)
    await db.flush()
    await db.refresh(checkpoint)
    return checkpoint


async def list_checkpoints(
    db: AsyncSession,
    run_id: UUID,
) -> list[AgentCheckpoint]:
    """List checkpoints for a run."""
    query = select(AgentCheckpoint).where(AgentCheckpoint.run_id == run_id)
    query = query.order_by(AgentCheckpoint.sequence.asc(), AgentCheckpoint.created_at.asc())
    result = await db.execute(query)
    return list(result.scalars().all())
