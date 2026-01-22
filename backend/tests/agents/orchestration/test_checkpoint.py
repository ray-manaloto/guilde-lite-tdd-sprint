"""Unit tests for the CheckpointManager module.

Tests cover:
- TokenMetrics dataclass and arithmetic operations
- AgentCheckpointData creation and defaults
- CheckpointState serialization and token aggregation
- CheckpointManager CRUD operations
- Workflow history and restore functionality
- Status transitions (complete, fail)
- File persistence with storage_path
- Max checkpoints enforcement
"""

import pytest
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.agents.orchestration.checkpoint import (
    AgentCheckpointData,
    CheckpointManager,
    CheckpointState,
    CheckpointStatus,
    TokenMetrics,
)


# ============================================================================
# TokenMetrics Tests
# ============================================================================


class TestTokenMetrics:
    """Tests for TokenMetrics dataclass."""

    def test_default_values(self) -> None:
        """TokenMetrics has zero defaults."""
        metrics = TokenMetrics()
        assert metrics.input_tokens == 0
        assert metrics.output_tokens == 0
        assert metrics.total_tokens == 0
        assert metrics.cost_usd == 0.0

    def test_custom_values(self) -> None:
        """TokenMetrics accepts custom values."""
        metrics = TokenMetrics(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=0.0015,
        )
        assert metrics.input_tokens == 100
        assert metrics.output_tokens == 50
        assert metrics.total_tokens == 150
        assert metrics.cost_usd == 0.0015

    def test_add_combines_metrics(self) -> None:
        """Add method combines two TokenMetrics correctly."""
        metrics1 = TokenMetrics(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
        )
        metrics2 = TokenMetrics(
            input_tokens=200,
            output_tokens=100,
            total_tokens=300,
            cost_usd=0.002,
        )
        combined = metrics1.add(metrics2)

        assert combined.input_tokens == 300
        assert combined.output_tokens == 150
        assert combined.total_tokens == 450
        assert combined.cost_usd == pytest.approx(0.003)

    def test_add_with_zero_metrics(self) -> None:
        """Add with zero metrics returns original values."""
        metrics = TokenMetrics(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
        )
        zero = TokenMetrics()
        combined = metrics.add(zero)

        assert combined.input_tokens == 100
        assert combined.output_tokens == 50
        assert combined.total_tokens == 150
        assert combined.cost_usd == pytest.approx(0.001)

    def test_add_returns_new_instance(self) -> None:
        """Add returns a new TokenMetrics instance."""
        metrics1 = TokenMetrics(input_tokens=100)
        metrics2 = TokenMetrics(input_tokens=200)
        combined = metrics1.add(metrics2)

        assert combined is not metrics1
        assert combined is not metrics2
        assert metrics1.input_tokens == 100  # Original unchanged
        assert metrics2.input_tokens == 200  # Original unchanged


# ============================================================================
# AgentCheckpointData Tests
# ============================================================================


class TestAgentCheckpointData:
    """Tests for AgentCheckpointData dataclass."""

    def test_required_fields(self) -> None:
        """AgentCheckpointData requires agent_name and provider."""
        data = AgentCheckpointData(
            agent_name="test-agent",
            provider="openai",
        )
        assert data.agent_name == "test-agent"
        assert data.provider == "openai"

    def test_default_values(self) -> None:
        """AgentCheckpointData has sensible defaults."""
        data = AgentCheckpointData(
            agent_name="test-agent",
            provider="openai",
        )
        assert data.model is None
        assert data.prompt == ""
        assert data.response == ""
        assert isinstance(data.token_metrics, TokenMetrics)
        assert data.tool_calls == []
        assert data.metadata == {}

    def test_full_initialization(self) -> None:
        """AgentCheckpointData accepts all fields."""
        token_metrics = TokenMetrics(input_tokens=100, output_tokens=50)
        data = AgentCheckpointData(
            agent_name="gpt-4o",
            provider="openai",
            model="gpt-4o-2024-01-01",
            prompt="What is Python?",
            response="Python is a programming language.",
            token_metrics=token_metrics,
            tool_calls=[{"name": "search", "args": {"query": "Python"}}],
            metadata={"temperature": 0.7},
        )

        assert data.agent_name == "gpt-4o"
        assert data.provider == "openai"
        assert data.model == "gpt-4o-2024-01-01"
        assert data.prompt == "What is Python?"
        assert data.response == "Python is a programming language."
        assert data.token_metrics.input_tokens == 100
        assert len(data.tool_calls) == 1
        assert data.metadata["temperature"] == 0.7


# ============================================================================
# CheckpointState Tests
# ============================================================================


class TestCheckpointState:
    """Tests for CheckpointState dataclass."""

    def test_default_values(self) -> None:
        """CheckpointState generates UUID and has sensible defaults."""
        state = CheckpointState()

        assert isinstance(state.id, UUID)
        assert state.parent_id is None
        assert state.workflow_id is None
        assert state.phase == ""
        assert state.status == CheckpointStatus.ACTIVE
        assert state.agent_data == {}
        assert state.context == {}
        assert isinstance(state.created_at, datetime)
        assert state.metadata == {}

    def test_custom_initialization(self) -> None:
        """CheckpointState accepts custom values."""
        checkpoint_id = uuid4()
        parent_id = uuid4()
        workflow_id = uuid4()

        state = CheckpointState(
            id=checkpoint_id,
            parent_id=parent_id,
            workflow_id=workflow_id,
            phase="planning",
            status=CheckpointStatus.COMPLETED,
        )

        assert state.id == checkpoint_id
        assert state.parent_id == parent_id
        assert state.workflow_id == workflow_id
        assert state.phase == "planning"
        assert state.status == CheckpointStatus.COMPLETED

    def test_get_total_tokens_empty(self) -> None:
        """get_total_tokens returns zero for empty agent_data."""
        state = CheckpointState()
        total = state.get_total_tokens()

        assert total.input_tokens == 0
        assert total.output_tokens == 0
        assert total.total_tokens == 0

    def test_get_total_tokens_single_agent(self) -> None:
        """get_total_tokens returns metrics from single agent."""
        state = CheckpointState(
            agent_data={
                "agent-1": AgentCheckpointData(
                    agent_name="agent-1",
                    provider="openai",
                    token_metrics=TokenMetrics(
                        input_tokens=100,
                        output_tokens=50,
                        total_tokens=150,
                    ),
                ),
            }
        )
        total = state.get_total_tokens()

        assert total.input_tokens == 100
        assert total.output_tokens == 50
        assert total.total_tokens == 150

    def test_get_total_tokens_multiple_agents(self) -> None:
        """get_total_tokens aggregates across all agents."""
        state = CheckpointState(
            agent_data={
                "agent-1": AgentCheckpointData(
                    agent_name="agent-1",
                    provider="openai",
                    token_metrics=TokenMetrics(
                        input_tokens=100,
                        output_tokens=50,
                        total_tokens=150,
                        cost_usd=0.001,
                    ),
                ),
                "agent-2": AgentCheckpointData(
                    agent_name="agent-2",
                    provider="anthropic",
                    token_metrics=TokenMetrics(
                        input_tokens=200,
                        output_tokens=100,
                        total_tokens=300,
                        cost_usd=0.002,
                    ),
                ),
            }
        )
        total = state.get_total_tokens()

        assert total.input_tokens == 300
        assert total.output_tokens == 150
        assert total.total_tokens == 450
        assert total.cost_usd == pytest.approx(0.003)

    def test_to_dict_serialization(self) -> None:
        """to_dict serializes state correctly."""
        workflow_id = uuid4()
        state = CheckpointState(
            workflow_id=workflow_id,
            phase="execution",
            status=CheckpointStatus.ACTIVE,
            context={"key": "value"},
        )

        data = state.to_dict()

        assert data["id"] == str(state.id)
        assert data["workflow_id"] == str(workflow_id)
        assert data["phase"] == "execution"
        assert data["status"] == "active"
        assert data["context"] == {"key": "value"}
        assert "created_at" in data

    def test_to_dict_with_agent_data(self) -> None:
        """to_dict serializes agent_data correctly."""
        state = CheckpointState(
            agent_data={
                "test-agent": AgentCheckpointData(
                    agent_name="test-agent",
                    provider="openai",
                    model="gpt-4o",
                    prompt="Hello",
                    response="Hi there!",
                ),
            }
        )

        data = state.to_dict()
        agent_data = data["agent_data"]["test-agent"]

        assert agent_data["agent_name"] == "test-agent"
        assert agent_data["provider"] == "openai"
        assert agent_data["model"] == "gpt-4o"
        assert agent_data["prompt"] == "Hello"
        assert agent_data["response"] == "Hi there!"

    def test_from_dict_deserialization(self) -> None:
        """from_dict deserializes state correctly."""
        checkpoint_id = uuid4()
        workflow_id = uuid4()
        created_at = datetime.now(UTC)

        data = {
            "id": str(checkpoint_id),
            "parent_id": None,
            "workflow_id": str(workflow_id),
            "phase": "planning",
            "status": "completed",
            "agent_data": {},
            "context": {"test": True},
            "created_at": created_at.isoformat(),
            "metadata": {},
        }

        state = CheckpointState.from_dict(data)

        assert state.id == checkpoint_id
        assert state.workflow_id == workflow_id
        assert state.phase == "planning"
        assert state.status == CheckpointStatus.COMPLETED
        assert state.context == {"test": True}

    def test_from_dict_with_agent_data(self) -> None:
        """from_dict deserializes agent_data correctly."""
        data = {
            "id": str(uuid4()),
            "parent_id": None,
            "workflow_id": None,
            "phase": "",
            "status": "active",
            "agent_data": {
                "test-agent": {
                    "agent_name": "test-agent",
                    "provider": "openai",
                    "model": "gpt-4o",
                    "prompt": "Hello",
                    "response": "Hi",
                    "token_metrics": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "total_tokens": 15,
                        "cost_usd": 0.0001,
                    },
                    "tool_calls": [],
                    "metadata": {},
                }
            },
            "context": {},
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {},
        }

        state = CheckpointState.from_dict(data)

        assert "test-agent" in state.agent_data
        agent = state.agent_data["test-agent"]
        assert agent.agent_name == "test-agent"
        assert agent.provider == "openai"
        assert agent.token_metrics.input_tokens == 10

    def test_roundtrip_serialization(self) -> None:
        """to_dict and from_dict are inverse operations."""
        original = CheckpointState(
            workflow_id=uuid4(),
            phase="testing",
            status=CheckpointStatus.ACTIVE,
            agent_data={
                "agent": AgentCheckpointData(
                    agent_name="agent",
                    provider="openai",
                    token_metrics=TokenMetrics(input_tokens=50),
                ),
            },
            context={"key": "value"},
            metadata={"version": "1.0"},
        )

        data = original.to_dict()
        restored = CheckpointState.from_dict(data)

        assert restored.id == original.id
        assert restored.workflow_id == original.workflow_id
        assert restored.phase == original.phase
        assert restored.status == original.status
        assert restored.context == original.context
        assert "agent" in restored.agent_data


# ============================================================================
# CheckpointStatus Enum Tests
# ============================================================================


class TestCheckpointStatusEnum:
    """Tests for CheckpointStatus enumeration."""

    def test_status_values(self) -> None:
        """CheckpointStatus has expected values."""
        assert CheckpointStatus.ACTIVE.value == "active"
        assert CheckpointStatus.COMPLETED.value == "completed"
        assert CheckpointStatus.ROLLED_BACK.value == "rolled_back"
        assert CheckpointStatus.FAILED.value == "failed"

    def test_status_from_string(self) -> None:
        """Can create CheckpointStatus from string."""
        assert CheckpointStatus("active") == CheckpointStatus.ACTIVE
        assert CheckpointStatus("completed") == CheckpointStatus.COMPLETED
        assert CheckpointStatus("rolled_back") == CheckpointStatus.ROLLED_BACK
        assert CheckpointStatus("failed") == CheckpointStatus.FAILED

    def test_invalid_status_raises(self) -> None:
        """Invalid status string raises ValueError."""
        with pytest.raises(ValueError):
            CheckpointStatus("invalid")


# ============================================================================
# CheckpointManager Creation Tests
# ============================================================================


class TestCheckpointManagerCreation:
    """Tests for CheckpointManager checkpoint creation."""

    @pytest.fixture
    def manager(self) -> CheckpointManager:
        """Create a CheckpointManager without persistence."""
        return CheckpointManager(storage_path=None)

    async def test_create_checkpoint(self, manager: CheckpointManager) -> None:
        """Can create a checkpoint."""
        workflow_id = uuid4()
        agent_data = {
            "agent-1": AgentCheckpointData(
                agent_name="agent-1",
                provider="openai",
            ),
        }

        checkpoint = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="planning",
            agent_data=agent_data,
        )

        assert isinstance(checkpoint.id, UUID)
        assert checkpoint.workflow_id == workflow_id
        assert checkpoint.phase == "planning"
        assert checkpoint.status == CheckpointStatus.ACTIVE
        assert "agent-1" in checkpoint.agent_data

    async def test_create_checkpoint_with_context(
        self, manager: CheckpointManager
    ) -> None:
        """Checkpoint can include context."""
        workflow_id = uuid4()

        checkpoint = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="execution",
            agent_data={},
            context={"user_input": "test", "iteration": 1},
        )

        assert checkpoint.context["user_input"] == "test"
        assert checkpoint.context["iteration"] == 1

    async def test_create_checkpoint_with_parent(
        self, manager: CheckpointManager
    ) -> None:
        """Checkpoint can have explicit parent."""
        workflow_id = uuid4()

        parent = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="phase-1",
            agent_data={},
        )

        child = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="phase-2",
            agent_data={},
            parent_id=parent.id,
        )

        assert child.parent_id == parent.id

    async def test_create_checkpoint_auto_parent(
        self, manager: CheckpointManager
    ) -> None:
        """Without explicit parent, uses latest checkpoint."""
        workflow_id = uuid4()

        first = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="phase-1",
            agent_data={},
        )

        second = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="phase-2",
            agent_data={},
        )

        assert second.parent_id == first.id

    async def test_create_checkpoint_with_metadata(
        self, manager: CheckpointManager
    ) -> None:
        """Checkpoint can include metadata."""
        workflow_id = uuid4()

        checkpoint = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="test",
            agent_data={},
            metadata={"version": "1.0", "author": "test"},
        )

        assert checkpoint.metadata["version"] == "1.0"
        assert checkpoint.metadata["author"] == "test"


# ============================================================================
# CheckpointManager Retrieval Tests
# ============================================================================


class TestCheckpointManagerRetrieval:
    """Tests for CheckpointManager retrieval operations."""

    @pytest.fixture
    def manager(self) -> CheckpointManager:
        """Create a CheckpointManager without persistence."""
        return CheckpointManager(storage_path=None)

    async def test_get_existing_checkpoint(
        self, manager: CheckpointManager
    ) -> None:
        """Can retrieve a checkpoint by ID."""
        workflow_id = uuid4()
        created = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="test",
            agent_data={},
        )

        retrieved = await manager.get(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.workflow_id == workflow_id

    async def test_get_nonexistent_checkpoint(
        self, manager: CheckpointManager
    ) -> None:
        """Getting non-existent checkpoint returns None."""
        result = await manager.get(uuid4())
        assert result is None

    async def test_get_workflow_history(
        self, manager: CheckpointManager
    ) -> None:
        """Can retrieve full workflow history."""
        workflow_id = uuid4()

        for i in range(3):
            await manager.create_checkpoint(
                workflow_id=workflow_id,
                phase=f"phase-{i}",
                agent_data={},
            )

        history = await manager.get_workflow_history(workflow_id)

        assert len(history) == 3
        # Should be in chronological order
        assert history[0].phase == "phase-0"
        assert history[1].phase == "phase-1"
        assert history[2].phase == "phase-2"

    async def test_get_workflow_history_empty(
        self, manager: CheckpointManager
    ) -> None:
        """Empty workflow history returns empty list."""
        history = await manager.get_workflow_history(uuid4())
        assert history == []

    async def test_get_workflow_history_isolation(
        self, manager: CheckpointManager
    ) -> None:
        """Workflow histories are isolated."""
        workflow_1 = uuid4()
        workflow_2 = uuid4()

        await manager.create_checkpoint(
            workflow_id=workflow_1,
            phase="w1-phase",
            agent_data={},
        )
        await manager.create_checkpoint(
            workflow_id=workflow_2,
            phase="w2-phase",
            agent_data={},
        )

        history_1 = await manager.get_workflow_history(workflow_1)
        history_2 = await manager.get_workflow_history(workflow_2)

        assert len(history_1) == 1
        assert len(history_2) == 1
        assert history_1[0].phase == "w1-phase"
        assert history_2[0].phase == "w2-phase"

    async def test_get_latest(self, manager: CheckpointManager) -> None:
        """Can get latest checkpoint for workflow."""
        workflow_id = uuid4()

        await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="first",
            agent_data={},
        )
        await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="second",
            agent_data={},
        )
        await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="third",
            agent_data={},
        )

        latest = await manager.get_latest(workflow_id)

        assert latest is not None
        assert latest.phase == "third"

    async def test_get_latest_empty_workflow(
        self, manager: CheckpointManager
    ) -> None:
        """get_latest returns None for empty workflow."""
        result = await manager.get_latest(uuid4())
        assert result is None


# ============================================================================
# CheckpointManager Restore Tests
# ============================================================================


class TestCheckpointManagerRestore:
    """Tests for CheckpointManager restore functionality."""

    @pytest.fixture
    def manager(self) -> CheckpointManager:
        """Create a CheckpointManager without persistence."""
        return CheckpointManager(storage_path=None)

    async def test_restore_creates_branch(
        self, manager: CheckpointManager
    ) -> None:
        """Restoring creates a new branch from checkpoint."""
        workflow_id = uuid4()

        original = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="original",
            agent_data={
                "agent": AgentCheckpointData(
                    agent_name="agent",
                    provider="openai",
                    response="original response",
                ),
            },
        )

        restored = await manager.restore(original.id)

        assert restored is not None
        assert restored.id != original.id  # New checkpoint
        assert restored.parent_id == original.id  # Branched from original
        assert restored.phase == original.phase
        assert "agent" in restored.agent_data

    async def test_restore_marks_original_rolled_back(
        self, manager: CheckpointManager
    ) -> None:
        """Restoring marks original checkpoint as rolled back."""
        workflow_id = uuid4()

        original = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="original",
            agent_data={},
        )

        await manager.restore(original.id)

        # Check original status
        original_after = await manager.get(original.id)
        assert original_after is not None
        assert original_after.status == CheckpointStatus.ROLLED_BACK

    async def test_restore_nonexistent_returns_none(
        self, manager: CheckpointManager
    ) -> None:
        """Restoring non-existent checkpoint returns None."""
        result = await manager.restore(uuid4())
        assert result is None

    async def test_restore_preserves_data(
        self, manager: CheckpointManager
    ) -> None:
        """Restored checkpoint preserves agent data and context."""
        workflow_id = uuid4()

        original = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="test",
            agent_data={
                "agent": AgentCheckpointData(
                    agent_name="agent",
                    provider="openai",
                    prompt="test prompt",
                    response="test response",
                    token_metrics=TokenMetrics(input_tokens=100),
                ),
            },
            context={"key": "value"},
        )

        restored = await manager.restore(original.id)

        assert restored is not None
        assert restored.context == {"key": "value"}
        assert "agent" in restored.agent_data
        agent = restored.agent_data["agent"]
        assert agent.prompt == "test prompt"
        assert agent.response == "test response"
        assert agent.token_metrics.input_tokens == 100


# ============================================================================
# CheckpointManager Status Transitions Tests
# ============================================================================


class TestCheckpointManagerStatusTransitions:
    """Tests for CheckpointManager status transition operations."""

    @pytest.fixture
    def manager(self) -> CheckpointManager:
        """Create a CheckpointManager without persistence."""
        return CheckpointManager(storage_path=None)

    async def test_complete_checkpoint(
        self, manager: CheckpointManager
    ) -> None:
        """Can mark checkpoint as completed."""
        workflow_id = uuid4()

        checkpoint = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="test",
            agent_data={},
        )
        assert checkpoint.status == CheckpointStatus.ACTIVE

        await manager.complete(checkpoint.id)

        updated = await manager.get(checkpoint.id)
        assert updated is not None
        assert updated.status == CheckpointStatus.COMPLETED

    async def test_complete_nonexistent_no_error(
        self, manager: CheckpointManager
    ) -> None:
        """Completing non-existent checkpoint doesn't raise."""
        await manager.complete(uuid4())  # Should not raise

    async def test_fail_checkpoint(self, manager: CheckpointManager) -> None:
        """Can mark checkpoint as failed."""
        workflow_id = uuid4()

        checkpoint = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="test",
            agent_data={},
        )

        await manager.fail(checkpoint.id, error="Something went wrong")

        updated = await manager.get(checkpoint.id)
        assert updated is not None
        assert updated.status == CheckpointStatus.FAILED
        assert updated.metadata.get("error") == "Something went wrong"

    async def test_fail_without_error_message(
        self, manager: CheckpointManager
    ) -> None:
        """Can fail checkpoint without error message."""
        workflow_id = uuid4()

        checkpoint = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="test",
            agent_data={},
        )

        await manager.fail(checkpoint.id)

        updated = await manager.get(checkpoint.id)
        assert updated is not None
        assert updated.status == CheckpointStatus.FAILED


# ============================================================================
# CheckpointManager Delete Tests
# ============================================================================


class TestCheckpointManagerDelete:
    """Tests for CheckpointManager delete operations."""

    @pytest.fixture
    def manager(self) -> CheckpointManager:
        """Create a CheckpointManager without persistence."""
        return CheckpointManager(storage_path=None)

    async def test_delete_existing_checkpoint(
        self, manager: CheckpointManager
    ) -> None:
        """Can delete an existing checkpoint."""
        workflow_id = uuid4()

        checkpoint = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="test",
            agent_data={},
        )

        result = await manager.delete(checkpoint.id)

        assert result is True
        assert await manager.get(checkpoint.id) is None

    async def test_delete_nonexistent_checkpoint(
        self, manager: CheckpointManager
    ) -> None:
        """Deleting non-existent checkpoint returns False."""
        result = await manager.delete(uuid4())
        assert result is False

    async def test_delete_removes_from_workflow_history(
        self, manager: CheckpointManager
    ) -> None:
        """Deleted checkpoint is removed from workflow history."""
        workflow_id = uuid4()

        checkpoint = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="test",
            agent_data={},
        )

        await manager.delete(checkpoint.id)

        history = await manager.get_workflow_history(workflow_id)
        assert len(history) == 0


# ============================================================================
# CheckpointManager Max Checkpoints Tests
# ============================================================================


class TestCheckpointManagerLimit:
    """Tests for CheckpointManager max_checkpoints enforcement."""

    async def test_enforces_max_checkpoints(self) -> None:
        """Manager enforces max_checkpoints limit."""
        manager = CheckpointManager(storage_path=None, max_checkpoints=3)
        workflow_id = uuid4()

        # Create 5 checkpoints
        for i in range(5):
            await manager.create_checkpoint(
                workflow_id=workflow_id,
                phase=f"phase-{i}",
                agent_data={},
            )

        history = await manager.get_workflow_history(workflow_id)

        # Should only keep max_checkpoints
        assert len(history) == 3
        # Oldest should be removed, newest kept
        phases = [c.phase for c in history]
        assert "phase-0" not in phases
        assert "phase-1" not in phases
        assert "phase-4" in phases

    async def test_default_max_checkpoints(self) -> None:
        """Default max_checkpoints is 100."""
        manager = CheckpointManager(storage_path=None)
        assert manager.max_checkpoints == 100


# ============================================================================
# CheckpointManager Persistence Tests
# ============================================================================


class TestCheckpointManagerPersistence:
    """Tests for CheckpointManager file persistence."""

    async def test_persist_and_load(self, tmp_path: Path) -> None:
        """Can persist checkpoint to disk and load it."""
        manager = CheckpointManager(storage_path=tmp_path)
        workflow_id = uuid4()

        created = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="persistent",
            agent_data={
                "agent": AgentCheckpointData(
                    agent_name="agent",
                    provider="openai",
                    prompt="test",
                ),
            },
            context={"saved": True},
        )

        # Check file was created
        checkpoint_file = tmp_path / f"{created.id}.json"
        assert checkpoint_file.exists()

        # Create new manager and load
        manager2 = CheckpointManager(storage_path=tmp_path)
        loaded = await manager2.get(created.id)

        assert loaded is not None
        assert loaded.id == created.id
        assert loaded.phase == "persistent"
        assert loaded.context == {"saved": True}
        assert "agent" in loaded.agent_data

    async def test_delete_removes_file(self, tmp_path: Path) -> None:
        """Deleting checkpoint removes file."""
        manager = CheckpointManager(storage_path=tmp_path)
        workflow_id = uuid4()

        checkpoint = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="test",
            agent_data={},
        )

        checkpoint_file = tmp_path / f"{checkpoint.id}.json"
        assert checkpoint_file.exists()

        await manager.delete(checkpoint.id)
        assert not checkpoint_file.exists()

    async def test_creates_storage_directory(self, tmp_path: Path) -> None:
        """Manager creates storage directory if it doesn't exist."""
        storage = tmp_path / "nested" / "checkpoint" / "dir"
        assert not storage.exists()

        manager = CheckpointManager(storage_path=storage)
        workflow_id = uuid4()

        await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="test",
            agent_data={},
        )

        assert storage.exists()

    async def test_persistence_updates_on_status_change(
        self, tmp_path: Path
    ) -> None:
        """Status changes are persisted to disk."""
        manager = CheckpointManager(storage_path=tmp_path)
        workflow_id = uuid4()

        checkpoint = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="test",
            agent_data={},
        )

        await manager.complete(checkpoint.id)

        # Load from new manager
        manager2 = CheckpointManager(storage_path=tmp_path)
        loaded = await manager2.get(checkpoint.id)

        assert loaded is not None
        assert loaded.status == CheckpointStatus.COMPLETED

    async def test_restore_persists_both_checkpoints(
        self, tmp_path: Path
    ) -> None:
        """Restore persists both original (rolled back) and new checkpoint."""
        manager = CheckpointManager(storage_path=tmp_path)
        workflow_id = uuid4()

        original = await manager.create_checkpoint(
            workflow_id=workflow_id,
            phase="original",
            agent_data={},
        )

        restored = await manager.restore(original.id)
        assert restored is not None

        # Verify both files exist
        original_file = tmp_path / f"{original.id}.json"
        restored_file = tmp_path / f"{restored.id}.json"
        assert original_file.exists()
        assert restored_file.exists()

        # Verify statuses from fresh manager
        manager2 = CheckpointManager(storage_path=tmp_path)
        loaded_original = await manager2.get(original.id)
        loaded_restored = await manager2.get(restored.id)

        assert loaded_original is not None
        assert loaded_original.status == CheckpointStatus.ROLLED_BACK
        assert loaded_restored is not None
        assert loaded_restored.status == CheckpointStatus.ACTIVE
