"""Multi-agent orchestration module.

Provides components for managing multiple AI agents with different integration
methods (SDK, CLI, HTTP), parallel prompt execution, checkpointing, and telemetry.
"""

from app.agents.orchestration.checkpoint import (
    AgentCheckpointData,
    CheckpointManager,
    CheckpointState,
    CheckpointStatus,
    TokenMetrics,
)
from app.agents.orchestration.dispatcher import AgentResponse, PromptDispatcher
from app.agents.orchestration.formatter import ResponseFormatter
from app.agents.orchestration.registry import AgentConfig, AgentRegistry, AgentType
from app.agents.orchestration.telemetry import TelemetryCollector, TelemetryEvent

__all__ = [
    # Registry
    "AgentType",
    "AgentConfig",
    "AgentRegistry",
    # Dispatcher
    "AgentResponse",
    "PromptDispatcher",
    # Checkpoint
    "CheckpointState",
    "CheckpointStatus",
    "TokenMetrics",
    "AgentCheckpointData",
    "CheckpointManager",
    # Telemetry
    "TelemetryEvent",
    "TelemetryCollector",
    # Formatter
    "ResponseFormatter",
]
