"""Schemas for TDD-style multi-agent runs."""

from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from app.schemas.agent_run import (
    AgentCheckpointRead,
    AgentDecisionRead,
    AgentRunForkCreate,
    AgentRunRead,
)
from app.schemas.agent_run import AgentCandidateRead
from app.schemas.base import BaseSchema


class AgentTddSubagentConfig(BaseSchema):
    """Configuration for a subagent run."""

    name: str = Field(max_length=100)
    provider: Literal["openai", "anthropic", "openrouter"] = "openai"
    model_name: str | None = Field(default=None, max_length=100)
    temperature: float | None = None
    system_prompt: str | None = None


class AgentTddJudgeConfig(BaseSchema):
    """Configuration for the judge model."""

    provider: Literal["openai", "anthropic", "openrouter"] | None = None
    model_name: str | None = Field(default=None, max_length=100)
    temperature: float | None = None
    system_prompt: str | None = None


class AgentTddSubagentError(BaseSchema):
    """Error information for a failed subagent."""

    agent_name: str
    provider: str
    model_name: str | None = None
    error: str


class AgentTddRunCreate(BaseSchema):
    """Request payload for a TDD run."""

    message: str
    history: list[dict[str, str]] = Field(default_factory=list)
    run_id: UUID | None = None
    checkpoint_id: UUID | None = None
    subagents: list[AgentTddSubagentConfig] = Field(default_factory=list)
    judge: AgentTddJudgeConfig | None = None
    workspace_ref: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)
    fork_label: str | None = Field(default=None, max_length=100)
    fork_reason: str | None = None

    def to_fork_create(self) -> AgentRunForkCreate:
        """Convert to fork request payload."""
        return AgentRunForkCreate(
            checkpoint_id=self.checkpoint_id,
            status="pending",
            input_payload={
                "message": self.message,
                "history": self.history,
                "metadata": self.metadata,
            },
            workspace_ref=self.workspace_ref,
            fork_label=self.fork_label,
            fork_reason=self.fork_reason,
        )

    def default_judge_config(self) -> AgentTddJudgeConfig:
        """Provide a default judge configuration."""
        return AgentTddJudgeConfig()


class AgentTddRunResult(BaseSchema):
    """Result payload for a TDD run."""

    run: AgentRunRead
    candidates: list[AgentCandidateRead]
    decision: AgentDecisionRead | None = None
    checkpoints: list[AgentCheckpointRead] = Field(default_factory=list)
    errors: list[AgentTddSubagentError] = Field(default_factory=list)
