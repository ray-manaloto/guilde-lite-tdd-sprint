"""Checkpoint manager for time-travel functionality.

Provides snapshot/restore capabilities for agent execution state,
enabling rollback to previous points in a multi-agent workflow.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import orjson


class CheckpointStatus(str, Enum):
    """Status of a checkpoint."""

    ACTIVE = "active"  # Current active checkpoint
    COMPLETED = "completed"  # Successfully completed
    ROLLED_BACK = "rolled_back"  # Rolled back to previous state
    FAILED = "failed"  # Failed during execution


@dataclass
class TokenMetrics:
    """Token usage metrics for an agent execution.

    Attributes:
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens
        total_tokens: Total tokens used
        cost_usd: Estimated cost in USD
    """

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    def add(self, other: "TokenMetrics") -> "TokenMetrics":
        """Add another TokenMetrics to this one."""
        return TokenMetrics(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cost_usd=self.cost_usd + other.cost_usd,
        )


@dataclass
class AgentCheckpointData:
    """Checkpoint data for a single agent.

    Attributes:
        agent_name: Name of the agent
        provider: Provider name
        model: Model used
        prompt: Input prompt
        response: Agent response content
        token_metrics: Token usage for this execution
        tool_calls: List of tool calls made
        metadata: Additional agent-specific data
    """

    agent_name: str
    provider: str
    model: str | None = None
    prompt: str = ""
    response: str = ""
    token_metrics: TokenMetrics = field(default_factory=TokenMetrics)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckpointState:
    """Complete checkpoint state for a workflow execution point.

    Attributes:
        id: Unique checkpoint identifier
        parent_id: ID of parent checkpoint (for branching)
        workflow_id: ID of the workflow this belongs to
        phase: Current workflow phase name
        status: Checkpoint status
        agent_data: Data from each agent at this point
        context: Shared workflow context
        created_at: When checkpoint was created
        metadata: Additional checkpoint metadata
    """

    id: UUID = field(default_factory=uuid4)
    parent_id: UUID | None = None
    workflow_id: UUID | None = None
    phase: str = ""
    status: CheckpointStatus = CheckpointStatus.ACTIVE
    agent_data: dict[str, AgentCheckpointData] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_total_tokens(self) -> TokenMetrics:
        """Calculate total token usage across all agents."""
        total = TokenMetrics()
        for agent_data in self.agent_data.values():
            total = total.add(agent_data.token_metrics)
        return total

    def to_dict(self) -> dict[str, Any]:
        """Convert checkpoint to dictionary for serialization."""
        return {
            "id": str(self.id),
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "phase": self.phase,
            "status": self.status.value,
            "agent_data": {
                name: {
                    "agent_name": data.agent_name,
                    "provider": data.provider,
                    "model": data.model,
                    "prompt": data.prompt,
                    "response": data.response,
                    "token_metrics": {
                        "input_tokens": data.token_metrics.input_tokens,
                        "output_tokens": data.token_metrics.output_tokens,
                        "total_tokens": data.token_metrics.total_tokens,
                        "cost_usd": data.token_metrics.cost_usd,
                    },
                    "tool_calls": data.tool_calls,
                    "metadata": data.metadata,
                }
                for name, data in self.agent_data.items()
            },
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CheckpointState":
        """Create checkpoint from dictionary."""
        agent_data = {}
        for name, ad in data.get("agent_data", {}).items():
            tm = ad.get("token_metrics", {})
            agent_data[name] = AgentCheckpointData(
                agent_name=ad["agent_name"],
                provider=ad["provider"],
                model=ad.get("model"),
                prompt=ad.get("prompt", ""),
                response=ad.get("response", ""),
                token_metrics=TokenMetrics(
                    input_tokens=tm.get("input_tokens", 0),
                    output_tokens=tm.get("output_tokens", 0),
                    total_tokens=tm.get("total_tokens", 0),
                    cost_usd=tm.get("cost_usd", 0.0),
                ),
                tool_calls=ad.get("tool_calls", []),
                metadata=ad.get("metadata", {}),
            )

        return cls(
            id=UUID(data["id"]),
            parent_id=UUID(data["parent_id"]) if data.get("parent_id") else None,
            workflow_id=UUID(data["workflow_id"]) if data.get("workflow_id") else None,
            phase=data.get("phase", ""),
            status=CheckpointStatus(data.get("status", "active")),
            agent_data=agent_data,
            context=data.get("context", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata", {}),
        )


class CheckpointManager:
    """Manages checkpoints for time-travel functionality.

    Supports creating snapshots, restoring to previous states,
    and maintaining checkpoint history with parent-child relationships.

    Example:
        >>> manager = CheckpointManager(storage_path=Path("./checkpoints"))
        >>> checkpoint = await manager.create_checkpoint(
        ...     workflow_id=workflow_id,
        ...     phase="planning",
        ...     agent_data={"planner": planner_data},
        ...     context={"task": "implement feature"}
        ... )
        >>> # Later, rollback to this checkpoint
        >>> restored = await manager.restore(checkpoint.id)
    """

    def __init__(
        self,
        storage_path: Path | None = None,
        max_checkpoints: int = 100,
    ) -> None:
        """Initialize checkpoint manager.

        Args:
            storage_path: Directory for persistent storage (None = memory only)
            max_checkpoints: Maximum checkpoints to retain per workflow
        """
        self.storage_path = storage_path
        self.max_checkpoints = max_checkpoints
        self._checkpoints: dict[UUID, CheckpointState] = {}
        self._workflow_checkpoints: dict[UUID, list[UUID]] = {}

        if storage_path:
            storage_path.mkdir(parents=True, exist_ok=True)

    async def create_checkpoint(
        self,
        workflow_id: UUID,
        phase: str,
        agent_data: dict[str, AgentCheckpointData],
        context: dict[str, Any] | None = None,
        parent_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CheckpointState:
        """Create a new checkpoint.

        Args:
            workflow_id: ID of the workflow
            phase: Current phase name
            agent_data: Data from each agent
            context: Shared workflow context
            parent_id: Parent checkpoint ID (auto-detected if None)
            metadata: Additional metadata

        Returns:
            Created checkpoint state
        """
        # Auto-detect parent if not specified
        if parent_id is None and workflow_id in self._workflow_checkpoints:
            checkpoints = self._workflow_checkpoints[workflow_id]
            if checkpoints:
                parent_id = checkpoints[-1]

        checkpoint = CheckpointState(
            workflow_id=workflow_id,
            phase=phase,
            agent_data=agent_data,
            context=context or {},
            parent_id=parent_id,
            metadata=metadata or {},
        )

        # Store in memory
        self._checkpoints[checkpoint.id] = checkpoint

        # Track workflow checkpoints
        if workflow_id not in self._workflow_checkpoints:
            self._workflow_checkpoints[workflow_id] = []
        self._workflow_checkpoints[workflow_id].append(checkpoint.id)

        # Enforce max checkpoints
        await self._enforce_limit(workflow_id)

        # Persist if storage configured
        if self.storage_path:
            await self._persist_checkpoint(checkpoint)

        return checkpoint

    async def restore(self, checkpoint_id: UUID) -> CheckpointState | None:
        """Restore to a specific checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to restore

        Returns:
            Restored checkpoint state or None if not found
        """
        checkpoint = await self.get(checkpoint_id)
        if not checkpoint:
            return None

        # Mark current active checkpoint as rolled back
        if checkpoint.workflow_id:
            for cp_id in self._workflow_checkpoints.get(checkpoint.workflow_id, []):
                cp = self._checkpoints.get(cp_id)
                if cp and cp.status == CheckpointStatus.ACTIVE:
                    cp.status = CheckpointStatus.ROLLED_BACK
                    if self.storage_path:
                        await self._persist_checkpoint(cp)

        # Create new checkpoint branching from restored one
        new_checkpoint = CheckpointState(
            workflow_id=checkpoint.workflow_id,
            phase=checkpoint.phase,
            agent_data=checkpoint.agent_data.copy(),
            context=checkpoint.context.copy(),
            parent_id=checkpoint.id,
            metadata={"restored_from": str(checkpoint_id)},
        )

        self._checkpoints[new_checkpoint.id] = new_checkpoint
        if checkpoint.workflow_id:
            self._workflow_checkpoints[checkpoint.workflow_id].append(new_checkpoint.id)

        # Persist new checkpoint if storage configured
        if self.storage_path:
            await self._persist_checkpoint(new_checkpoint)

        return new_checkpoint

    async def get(self, checkpoint_id: UUID) -> CheckpointState | None:
        """Get a checkpoint by ID.

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            Checkpoint state or None if not found
        """
        # Check memory first
        if checkpoint_id in self._checkpoints:
            return self._checkpoints[checkpoint_id]

        # Try loading from storage
        if self.storage_path:
            return await self._load_checkpoint(checkpoint_id)

        return None

    async def get_workflow_history(
        self,
        workflow_id: UUID,
    ) -> list[CheckpointState]:
        """Get all checkpoints for a workflow in chronological order.

        Args:
            workflow_id: Workflow ID

        Returns:
            List of checkpoints ordered by creation time
        """
        checkpoint_ids = self._workflow_checkpoints.get(workflow_id, [])
        checkpoints = []
        for cp_id in checkpoint_ids:
            cp = await self.get(cp_id)
            if cp:
                checkpoints.append(cp)
        return sorted(checkpoints, key=lambda x: x.created_at)

    async def get_latest(self, workflow_id: UUID) -> CheckpointState | None:
        """Get the most recent checkpoint for a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            Latest checkpoint or None if no checkpoints exist
        """
        history = await self.get_workflow_history(workflow_id)
        return history[-1] if history else None

    async def complete(self, checkpoint_id: UUID) -> None:
        """Mark a checkpoint as completed.

        Args:
            checkpoint_id: Checkpoint ID
        """
        checkpoint = await self.get(checkpoint_id)
        if checkpoint:
            checkpoint.status = CheckpointStatus.COMPLETED
            if self.storage_path:
                await self._persist_checkpoint(checkpoint)

    async def fail(self, checkpoint_id: UUID, error: str | None = None) -> None:
        """Mark a checkpoint as failed.

        Args:
            checkpoint_id: Checkpoint ID
            error: Optional error message
        """
        checkpoint = await self.get(checkpoint_id)
        if checkpoint:
            checkpoint.status = CheckpointStatus.FAILED
            if error:
                checkpoint.metadata["error"] = error
            if self.storage_path:
                await self._persist_checkpoint(checkpoint)

    async def delete(self, checkpoint_id: UUID) -> bool:
        """Delete a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            True if deleted, False if not found
        """
        if checkpoint_id not in self._checkpoints:
            return False

        checkpoint = self._checkpoints.pop(checkpoint_id)

        # Remove from workflow tracking
        if checkpoint.workflow_id:
            workflow_cps = self._workflow_checkpoints.get(checkpoint.workflow_id, [])
            if checkpoint_id in workflow_cps:
                workflow_cps.remove(checkpoint_id)

        # Delete from storage
        if self.storage_path:
            file_path = self.storage_path / f"{checkpoint_id}.json"
            if file_path.exists():
                file_path.unlink()

        return True

    async def _enforce_limit(self, workflow_id: UUID) -> None:
        """Remove oldest checkpoints if over limit."""
        checkpoint_ids = self._workflow_checkpoints.get(workflow_id, [])
        while len(checkpoint_ids) > self.max_checkpoints:
            oldest_id = checkpoint_ids.pop(0)
            await self.delete(oldest_id)

    async def _persist_checkpoint(self, checkpoint: CheckpointState) -> None:
        """Save checkpoint to storage."""
        if not self.storage_path:
            return

        file_path = self.storage_path / f"{checkpoint.id}.json"
        data = orjson.dumps(checkpoint.to_dict())
        file_path.write_bytes(data)

    async def _load_checkpoint(self, checkpoint_id: UUID) -> CheckpointState | None:
        """Load checkpoint from storage."""
        if not self.storage_path:
            return None

        file_path = self.storage_path / f"{checkpoint_id}.json"
        if not file_path.exists():
            return None

        data = orjson.loads(file_path.read_bytes())
        checkpoint = CheckpointState.from_dict(data)
        self._checkpoints[checkpoint_id] = checkpoint
        return checkpoint
