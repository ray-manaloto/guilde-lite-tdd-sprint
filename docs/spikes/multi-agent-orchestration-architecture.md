# Multi-Agent AI Orchestration Architecture

**Status:** Architectural Review
**Date:** 2026-01-21
**Author:** Architecture Review

## Executive Summary

This document provides a comprehensive architectural review for implementing a sophisticated multi-agent AI orchestration system into the `guilde-lite-tdd-sprint` brownfield project. The review maps the user's vision to existing codebase patterns and proposes extension strategies.

---

## 1. Current State Analysis

### 1.1 Existing Infrastructure Strengths

The codebase already contains significant infrastructure that can be extended:

| Component | Location | Capability |
|-----------|----------|------------|
| Dual-Subagent Pattern | `app/agents/ralph_planner.py` | 2-agent parallel execution with judge |
| Provider Abstraction | `app/core/config.py` | OpenAI, Anthropic, OpenRouter support |
| CLI Agent Integration | `app/agents/tools/agent_integration.py` | Subprocess-based external CLI invocation |
| Telemetry | `logfire` spans | trace_id, trace_url, attributes |
| Session Filesystem | `app/agents/tools/filesystem.py` | Session-scoped artifact storage |
| Click CLI Framework | `cli/commands.py` | Django-style command discovery |

### 1.2 Key Existing Patterns

**Dual-Subagent with Judge (ralph_planner.py:150-200)**
```python
candidate_specs = [
    ("openai", settings.model_for_provider("openai")),
    ("anthropic", settings.model_for_provider("anthropic")),
]
candidates: list[dict[str, Any]] = []
for provider, model_name in candidate_specs:
    questions, telemetry = await _run_planning_agent(...)
    candidates.append({
        "provider": telemetry.get("provider"),
        "model_name": telemetry.get("model_name"),
        "questions": questions,
        "trace_id": telemetry.get("trace_id"),
    })
# Judge evaluation follows
```

**Provider Abstraction (config.py:227-243)**
```python
def model_for_provider(self, provider: str) -> str:
    provider = provider.lower()
    if provider == "anthropic":
        return self.ANTHROPIC_MODEL or self.AI_MODEL
    if provider == "openrouter":
        return self.OPENROUTER_MODEL or self.AI_MODEL
    return self.OPENAI_MODEL or self.AI_MODEL
```

---

## 2. Multi-Agent Orchestration Design

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR LAYER                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Prompt      │  │ Checkpoint  │  │ Telemetry   │            │
│  │ Dispatcher  │  │ Manager     │  │ Collector   │            │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
└─────────┼────────────────┼────────────────┼────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT EXECUTION LAYER                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ Claude  │ │ OpenAI  │ │ Codex   │ │ Gemini  │ │ Custom  │  │
│  │ SDK     │ │ SDK     │ │ CLI     │ │ SDK     │ │ CLI     │  │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘  │
└───────┼──────────┼──────────┼──────────┼──────────┼──────────┘
        │          │          │          │          │
        ▼          ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RESPONSE STORAGE LAYER                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Session Directory (Markdown + Metadata JSONL)          │   │
│  │  /{session_id}/checkpoints/{checkpoint_id}/             │   │
│  │  ├── agent_responses/                                   │   │
│  │  │   ├── claude_response.md                             │   │
│  │  │   ├── openai_response.md                             │   │
│  │  │   └── _metadata.jsonl                                │   │
│  │  ├── checkpoint_state.json                              │   │
│  │  └── telemetry.jsonl                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Core Components

#### 2.2.1 Multi-Agent Registry

**Location:** `app/agents/registry.py` (new)

```python
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any

class AgentType(Enum):
    SDK = "sdk"        # Direct SDK integration (OpenAI, Anthropic)
    CLI = "cli"        # External CLI tool (Claude Code, Codex)
    HTTP = "http"      # HTTP API endpoint

@dataclass
class AgentConfig:
    """Configuration for a registered AI agent."""
    name: str
    agent_type: AgentType
    provider: str  # openai, anthropic, openrouter, claude-cli, codex-cli
    model: str | None = None
    timeout_seconds: int = 120
    enabled: bool = True

    # For CLI agents
    cli_command: list[str] | None = None

    # For SDK agents
    sdk_client_factory: Callable[[], Any] | None = None

    # Metadata tracking
    track_tokens: bool = True
    track_tools: bool = True

class AgentRegistry:
    """Central registry for all AI agents."""

    _agents: dict[str, AgentConfig] = {}

    @classmethod
    def register(cls, config: AgentConfig) -> None:
        cls._agents[config.name] = config

    @classmethod
    def get_enabled_agents(cls) -> list[AgentConfig]:
        return [a for a in cls._agents.values() if a.enabled]

    @classmethod
    def get_by_provider(cls, provider: str) -> list[AgentConfig]:
        return [a for a in cls._agents.values() if a.provider == provider]
```

#### 2.2.2 Parallel Prompt Dispatcher

**Location:** `app/agents/orchestration/dispatcher.py` (new)

```python
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass
class AgentResponse:
    """Response from a single AI agent."""
    agent_name: str
    provider: str
    model: str
    response_content: str

    # Telemetry
    trace_id: str
    trace_url: str | None

    # Token tracking
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None

    # Tool/skill tracking
    tools_used: list[str]

    # Timing
    started_at: datetime
    completed_at: datetime
    duration_ms: int

    # Status
    success: bool
    error: str | None = None

class PromptDispatcher:
    """Dispatches prompts to all registered agents simultaneously."""

    async def dispatch_to_all(
        self,
        prompt: str,
        *,
        checkpoint_id: str,
        session_dir: Path,
        timeout_seconds: int = 120,
    ) -> list[AgentResponse]:
        """Send prompt to ALL enabled agents concurrently."""
        agents = AgentRegistry.get_enabled_agents()

        tasks = [
            self._execute_agent(agent, prompt, checkpoint_id, session_dir)
            for agent in agents
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            r if isinstance(r, AgentResponse)
            else self._error_response(agents[i], r)
            for i, r in enumerate(responses)
        ]

    async def _execute_agent(
        self,
        agent: AgentConfig,
        prompt: str,
        checkpoint_id: str,
        session_dir: Path,
    ) -> AgentResponse:
        """Execute a single agent and capture full telemetry."""
        with logfire.span(
            f"agent_execution_{agent.name}",
            agent_name=agent.name,
            provider=agent.provider,
            checkpoint_id=checkpoint_id,
        ) as span:
            started_at = datetime.utcnow()

            if agent.agent_type == AgentType.SDK:
                result = await self._execute_sdk_agent(agent, prompt)
            elif agent.agent_type == AgentType.CLI:
                result = await self._execute_cli_agent(agent, prompt)
            else:
                result = await self._execute_http_agent(agent, prompt)

            completed_at = datetime.utcnow()

            response = AgentResponse(
                agent_name=agent.name,
                provider=agent.provider,
                model=result.get("model", agent.model),
                response_content=result["content"],
                trace_id=span.trace_id,
                trace_url=self._build_trace_url(span),
                input_tokens=result.get("input_tokens"),
                output_tokens=result.get("output_tokens"),
                total_tokens=result.get("total_tokens"),
                tools_used=result.get("tools_used", []),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=int((completed_at - started_at).total_seconds() * 1000),
                success=True,
            )

            # Store response as markdown
            await self._store_response(response, session_dir, checkpoint_id)

            return response
```

### 2.3 Checkpoint/Time-Travel System

#### 2.3.1 Checkpoint State Schema

**Location:** `app/agents/orchestration/checkpoint.py` (new)

```python
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class CheckpointStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class TokenMetrics(BaseModel):
    """Token usage at a checkpoint."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None = None

class AgentCheckpointData(BaseModel):
    """Data for a single agent at a checkpoint."""
    agent_name: str
    provider: str
    model: str

    response_file: str  # Relative path to markdown
    response_hash: str  # SHA256 for integrity

    tokens: TokenMetrics | None
    tools_used: list[str]

    trace_id: str
    trace_url: str | None

    success: bool
    error: str | None = None

class CheckpointState(BaseModel):
    """Complete state snapshot at a checkpoint."""
    checkpoint_id: str
    workflow_id: str
    stage: str  # e.g., "discovery", "planning", "implementation"

    created_at: datetime
    status: CheckpointStatus

    # The prompt that was sent
    prompt: str
    prompt_hash: str

    # All agent responses
    agent_responses: list[AgentCheckpointData]

    # Aggregate metrics
    total_tokens: TokenMetrics

    # For time-travel
    parent_checkpoint_id: str | None = None
    child_checkpoint_ids: list[str] = []

    # Metadata
    metadata: dict[str, Any] = {}

class CheckpointManager:
    """Manages checkpoint creation, storage, and time-travel."""

    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.checkpoints_dir = session_dir / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

    async def create_checkpoint(
        self,
        workflow_id: str,
        stage: str,
        prompt: str,
        responses: list[AgentResponse],
        parent_checkpoint_id: str | None = None,
    ) -> CheckpointState:
        """Create a new checkpoint with all agent responses."""
        checkpoint_id = self._generate_checkpoint_id()
        checkpoint_dir = self.checkpoints_dir / checkpoint_id
        checkpoint_dir.mkdir(parents=True)

        # Store each agent response as markdown
        agent_data = []
        for response in responses:
            response_file = f"agent_responses/{response.agent_name}_response.md"
            await self._write_response_markdown(
                checkpoint_dir / response_file,
                response,
            )

            agent_data.append(AgentCheckpointData(
                agent_name=response.agent_name,
                provider=response.provider,
                model=response.model,
                response_file=response_file,
                response_hash=self._hash_content(response.response_content),
                tokens=TokenMetrics(
                    input_tokens=response.input_tokens or 0,
                    output_tokens=response.output_tokens or 0,
                    total_tokens=response.total_tokens or 0,
                ) if response.input_tokens else None,
                tools_used=response.tools_used,
                trace_id=response.trace_id,
                trace_url=response.trace_url,
                success=response.success,
                error=response.error,
            ))

        state = CheckpointState(
            checkpoint_id=checkpoint_id,
            workflow_id=workflow_id,
            stage=stage,
            created_at=datetime.utcnow(),
            status=CheckpointStatus.COMPLETED,
            prompt=prompt,
            prompt_hash=self._hash_content(prompt),
            agent_responses=agent_data,
            total_tokens=self._aggregate_tokens(agent_data),
            parent_checkpoint_id=parent_checkpoint_id,
        )

        # Save checkpoint state
        await self._save_checkpoint_state(checkpoint_dir, state)

        # Update parent's child list if applicable
        if parent_checkpoint_id:
            await self._link_to_parent(parent_checkpoint_id, checkpoint_id)

        return state

    async def restore_checkpoint(self, checkpoint_id: str) -> CheckpointState:
        """Restore state from a previous checkpoint (time-travel)."""
        checkpoint_dir = self.checkpoints_dir / checkpoint_id
        return await self._load_checkpoint_state(checkpoint_dir)

    async def list_checkpoints(
        self,
        workflow_id: str | None = None,
    ) -> list[CheckpointState]:
        """List all checkpoints, optionally filtered by workflow."""
        checkpoints = []
        for checkpoint_dir in self.checkpoints_dir.iterdir():
            if checkpoint_dir.is_dir():
                state = await self._load_checkpoint_state(checkpoint_dir)
                if workflow_id is None or state.workflow_id == workflow_id:
                    checkpoints.append(state)
        return sorted(checkpoints, key=lambda c: c.created_at)
```

#### 2.3.2 Response Markdown Format

Each agent response is stored as AI-optimized markdown:

```markdown
---
agent: claude-sonnet
provider: anthropic
model: claude-sonnet-4-20250514
checkpoint_id: cp_20260121_143052_abc123
workflow_id: wf_feature_auth_system
stage: discovery
timestamp: 2026-01-21T14:30:52Z
---

# Agent Response: claude-sonnet

## Metadata
- **Trace ID:** `abc123def456`
- **Trace URL:** [View in Logfire](https://logfire.pydantic.dev/...)
- **Input Tokens:** 1,234
- **Output Tokens:** 567
- **Total Tokens:** 1,801
- **Duration:** 2,345ms

## Tools/Skills Used
- `read_file`
- `search_codebase`
- `analyze_dependencies`

## Response

[Actual agent response content here...]

---
*Generated by Multi-Agent Orchestrator v1.0*
```

---

## 3. Telemetry Infrastructure

### 3.1 Telemetry Collection Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    TELEMETRY COLLECTORS                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Agent       │  │ Checkpoint  │  │ Workflow    │            │
│  │ Telemetry   │  │ Telemetry   │  │ Telemetry   │            │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
└─────────┼────────────────┼────────────────┼────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TELEMETRY ROUTER                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Routes to configured backends based on settings         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Logfire     │  │ JSONL       │  │ Prometheus  │
│ (Primary)   │  │ (Fallback)  │  │ (Metrics)   │
└─────────────┘  └─────────────┘  └─────────────┘
```

### 3.2 Telemetry Schema

**Location:** `app/agents/orchestration/telemetry.py` (new)

```python
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class TelemetryEventType(str, Enum):
    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"
    AGENT_ERROR = "agent_error"
    CHECKPOINT_CREATE = "checkpoint_create"
    CHECKPOINT_RESTORE = "checkpoint_restore"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    TOOL_INVOCATION = "tool_invocation"

class TelemetryEvent(BaseModel):
    """A single telemetry event."""
    event_type: TelemetryEventType
    timestamp: datetime

    # Identifiers
    trace_id: str
    span_id: str
    parent_span_id: str | None = None

    # Context
    workflow_id: str | None = None
    checkpoint_id: str | None = None
    agent_name: str | None = None

    # Metrics
    duration_ms: int | None = None
    tokens: dict[str, int] | None = None  # input, output, total

    # Details
    attributes: dict[str, Any] = {}

    # Error tracking
    error: str | None = None
    error_type: str | None = None

class TelemetryCollector:
    """Collects and routes telemetry events."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._init_backends()

    def _init_backends(self):
        """Initialize telemetry backends based on settings."""
        self.backends = []

        # Logfire (primary)
        if self.settings.LOGFIRE_SEND_TO_LOGFIRE:
            self.backends.append(LogfireBackend())

        # JSONL (always enabled as fallback)
        if self.settings.TELEMETRY_FILE:
            self.backends.append(JSONLBackend(self.settings.TELEMETRY_FILE))

        # Prometheus metrics
        self.backends.append(PrometheusBackend())

    async def record(self, event: TelemetryEvent) -> None:
        """Record telemetry event to all backends."""
        for backend in self.backends:
            try:
                await backend.record(event)
            except Exception as e:
                # Don't fail main flow on telemetry errors
                logger.warning(f"Telemetry backend error: {e}")

    def create_span(self, name: str, **attributes) -> TelemetrySpan:
        """Create a new telemetry span."""
        return TelemetrySpan(self, name, **attributes)
```

### 3.3 JSONL Telemetry Format

```jsonl
{"event_type":"workflow_start","timestamp":"2026-01-21T14:30:00Z","trace_id":"abc123","workflow_id":"wf_auth","attributes":{"prompt_hash":"sha256:..."}}
{"event_type":"agent_start","timestamp":"2026-01-21T14:30:01Z","trace_id":"abc123","span_id":"span1","agent_name":"claude-sonnet","attributes":{"model":"claude-sonnet-4"}}
{"event_type":"tool_invocation","timestamp":"2026-01-21T14:30:02Z","trace_id":"abc123","span_id":"span2","parent_span_id":"span1","attributes":{"tool":"read_file","path":"src/auth.py"}}
{"event_type":"agent_complete","timestamp":"2026-01-21T14:30:15Z","trace_id":"abc123","span_id":"span1","duration_ms":14000,"tokens":{"input":1234,"output":567,"total":1801}}
{"event_type":"checkpoint_create","timestamp":"2026-01-21T14:30:16Z","trace_id":"abc123","checkpoint_id":"cp_001","attributes":{"stage":"discovery","agent_count":3}}
```

---

## 4. Role-Based Workflow Parallelization

### 4.1 Role Definitions

**Location:** `app/agents/orchestration/roles.py` (new)

```python
from dataclasses import dataclass
from enum import Enum
from typing import Callable

class WorkflowPhase(str, Enum):
    DISCOVERY = "discovery"
    PLANNING = "planning"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    REVIEW = "review"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"

@dataclass
class RoleConfig:
    """Configuration for a workflow role."""
    name: str
    description: str

    # When this role participates
    active_phases: list[WorkflowPhase]

    # Role-specific prompt augmentation
    system_prompt_template: str

    # Evaluation criteria
    pass_criteria: list[str]  # For binary pass/fail

    # Priority (lower = earlier in phase)
    priority: int = 50

# 17 Role Definitions
WORKFLOW_ROLES: dict[str, RoleConfig] = {
    "ceo_stakeholder": RoleConfig(
        name="CEO/Stakeholder",
        description="Strategic alignment and business value assessment",
        active_phases=[WorkflowPhase.DISCOVERY, WorkflowPhase.REVIEW],
        system_prompt_template="""
You are acting as a CEO/Stakeholder reviewing this proposal.
Focus on: ROI, strategic alignment, risk assessment, resource allocation.
Provide binary PASS/FAIL with quantifiable metrics.
""",
        pass_criteria=["business_value_score >= 7", "risk_level <= 'medium'"],
        priority=10,
    ),

    "project_manager": RoleConfig(
        name="Project Manager",
        description="Timeline, resources, and coordination",
        active_phases=[WorkflowPhase.PLANNING, WorkflowPhase.MONITORING],
        system_prompt_template="""
You are acting as a Project Manager.
Focus on: Timeline estimation, resource allocation, milestone definition, risk mitigation.
Provide binary PASS/FAIL with specific dates and deliverables.
""",
        pass_criteria=["timeline_feasible", "resources_available"],
        priority=20,
    ),

    "software_architect": RoleConfig(
        name="Software Architect",
        description="System design and technical decisions",
        active_phases=[WorkflowPhase.DESIGN, WorkflowPhase.REVIEW],
        system_prompt_template="""
You are acting as a Software Architect.
Focus on: System design, scalability, maintainability, technical debt.
Provide binary PASS/FAIL with architecture decision records.
""",
        pass_criteria=["scalability_score >= 8", "no_critical_anti_patterns"],
        priority=15,
    ),

    "business_analyst": RoleConfig(
        name="Business Analyst",
        description="Requirements and domain analysis",
        active_phases=[WorkflowPhase.DISCOVERY, WorkflowPhase.PLANNING],
        system_prompt_template="""
You are acting as a Business Analyst.
Focus on: Requirements clarity, acceptance criteria, domain modeling.
Provide binary PASS/FAIL with requirement coverage metrics.
""",
        pass_criteria=["requirements_coverage >= 95%", "no_ambiguous_requirements"],
        priority=25,
    ),

    "research_scientist": RoleConfig(
        name="Research Scientist",
        description="State-of-the-art research and innovation",
        active_phases=[WorkflowPhase.DISCOVERY],
        system_prompt_template="""
You are acting as a Research Scientist.
Focus on: Academic literature, cutting-edge approaches, experimental design.
Provide binary PASS/FAIL with citation-backed recommendations.
""",
        pass_criteria=["research_depth_score >= 7", "citations_provided"],
        priority=30,
    ),

    "staff_engineer": RoleConfig(
        name="Staff Software Engineer",
        description="Technical leadership and complex implementation",
        active_phases=[WorkflowPhase.DESIGN, WorkflowPhase.IMPLEMENTATION, WorkflowPhase.REVIEW],
        system_prompt_template="""
You are acting as a Staff Software Engineer.
Focus on: Technical excellence, code quality, mentorship, cross-team impact.
Provide binary PASS/FAIL with specific technical recommendations.
""",
        pass_criteria=["code_quality_score >= 9", "follows_best_practices"],
        priority=35,
    ),

    "senior_engineer": RoleConfig(
        name="Senior Software Engineer",
        description="Feature implementation and technical guidance",
        active_phases=[WorkflowPhase.IMPLEMENTATION, WorkflowPhase.REVIEW],
        system_prompt_template="""
You are acting as a Senior Software Engineer.
Focus on: Implementation quality, code review, technical mentorship.
Provide binary PASS/FAIL with code-level feedback.
""",
        pass_criteria=["implementation_complete", "tests_passing"],
        priority=40,
    ),

    "junior_engineer": RoleConfig(
        name="Junior Software Engineer",
        description="Implementation support and learning",
        active_phases=[WorkflowPhase.IMPLEMENTATION],
        system_prompt_template="""
You are acting as a Junior Software Engineer.
Focus on: Implementation tasks, asking clarifying questions, learning patterns.
Provide binary PASS/FAIL with questions and assumptions documented.
""",
        pass_criteria=["task_completed", "assumptions_documented"],
        priority=45,
    ),

    "qa_engineer": RoleConfig(
        name="QA/Test Automation Engineer",
        description="Quality assurance and test automation",
        active_phases=[WorkflowPhase.TESTING, WorkflowPhase.REVIEW],
        system_prompt_template="""
You are acting as a QA/Test Automation Engineer.
Focus on: Test coverage, edge cases, regression prevention, test automation.
Provide binary PASS/FAIL with test coverage metrics.
""",
        pass_criteria=["test_coverage >= 80%", "no_critical_bugs"],
        priority=50,
    ),

    "unit_test_engineer": RoleConfig(
        name="Unit Test Engineer",
        description="Unit test implementation",
        active_phases=[WorkflowPhase.IMPLEMENTATION, WorkflowPhase.TESTING],
        system_prompt_template="""
You are acting as a Unit Test Engineer.
Focus on: Unit test coverage, mocking strategies, test isolation.
Provide binary PASS/FAIL with unit test metrics.
""",
        pass_criteria=["unit_test_coverage >= 85%", "tests_isolated"],
        priority=55,
    ),

    "code_reviewer": RoleConfig(
        name="Code Reviewer",
        description="Code quality and standards enforcement",
        active_phases=[WorkflowPhase.REVIEW],
        system_prompt_template="""
You are acting as a Code Reviewer.
Focus on: Code quality, standards compliance, security, maintainability.
Provide binary PASS/FAIL with specific line-level feedback.
""",
        pass_criteria=["no_blocking_issues", "standards_compliant"],
        priority=60,
    ),

    "data_scientist": RoleConfig(
        name="Data Scientist",
        description="Data analysis and ML considerations",
        active_phases=[WorkflowPhase.DISCOVERY, WorkflowPhase.DESIGN],
        system_prompt_template="""
You are acting as a Data Scientist.
Focus on: Data requirements, ML feasibility, metrics, experiments.
Provide binary PASS/FAIL with data quality metrics.
""",
        pass_criteria=["data_available", "metrics_defined"],
        priority=65,
    ),

    "devops_engineer": RoleConfig(
        name="DevOps Engineer",
        description="Infrastructure and deployment",
        active_phases=[WorkflowPhase.DESIGN, WorkflowPhase.DEPLOYMENT],
        system_prompt_template="""
You are acting as a DevOps Engineer.
Focus on: Infrastructure, deployment, monitoring, reliability.
Provide binary PASS/FAIL with infrastructure readiness metrics.
""",
        pass_criteria=["infrastructure_ready", "monitoring_configured"],
        priority=70,
    ),

    "network_engineer": RoleConfig(
        name="Network Engineer",
        description="Network architecture and security",
        active_phases=[WorkflowPhase.DESIGN],
        system_prompt_template="""
You are acting as a Network Engineer.
Focus on: Network topology, security, latency, reliability.
Provide binary PASS/FAIL with network readiness assessment.
""",
        pass_criteria=["network_secure", "latency_acceptable"],
        priority=75,
    ),

    "cicd_engineer": RoleConfig(
        name="CI/CD Automation Engineer",
        description="Pipeline automation and deployment",
        active_phases=[WorkflowPhase.DEPLOYMENT],
        system_prompt_template="""
You are acting as a CI/CD Automation Engineer.
Focus on: Pipeline design, automation, deployment strategies.
Provide binary PASS/FAIL with pipeline status.
""",
        pass_criteria=["pipeline_green", "deployment_automated"],
        priority=80,
    ),

    "beta_user": RoleConfig(
        name="Canary/Beta User",
        description="Early user feedback and validation",
        active_phases=[WorkflowPhase.TESTING, WorkflowPhase.MONITORING],
        system_prompt_template="""
You are acting as a Beta User testing new features.
Focus on: Usability, bugs, edge cases, user experience.
Provide binary PASS/FAIL with user acceptance feedback.
""",
        pass_criteria=["usability_score >= 7", "no_blocking_bugs"],
        priority=85,
    ),

    "documentation_engineer": RoleConfig(
        name="Software Documentation Engineer",
        description="Documentation and knowledge management",
        active_phases=[WorkflowPhase.REVIEW, WorkflowPhase.DEPLOYMENT],
        system_prompt_template="""
You are acting as a Documentation Engineer.
Focus on: API docs, user guides, architecture docs, runbooks.
Provide binary PASS/FAIL with documentation completeness.
""",
        pass_criteria=["docs_complete", "api_documented"],
        priority=90,
    ),

    "performance_engineer": RoleConfig(
        name="Performance Engineer",
        description="Performance optimization and benchmarking",
        active_phases=[WorkflowPhase.TESTING, WorkflowPhase.MONITORING],
        system_prompt_template="""
You are acting as a Performance Engineer.
Focus on: Benchmarks, optimization, scalability, resource efficiency.
Provide binary PASS/FAIL with performance metrics.
""",
        pass_criteria=["latency_p99 <= threshold", "throughput >= target"],
        priority=95,
    ),
}
```

### 4.2 Role-Based Workflow Executor

```python
class RoleBasedWorkflowExecutor:
    """Executes workflows with role-based parallelization."""

    def __init__(
        self,
        dispatcher: PromptDispatcher,
        checkpoint_manager: CheckpointManager,
        telemetry: TelemetryCollector,
    ):
        self.dispatcher = dispatcher
        self.checkpoint_manager = checkpoint_manager
        self.telemetry = telemetry

    async def execute_phase(
        self,
        workflow_id: str,
        phase: WorkflowPhase,
        prompt: str,
        *,
        parent_checkpoint_id: str | None = None,
    ) -> PhaseResult:
        """Execute a workflow phase with all active roles."""
        # Get roles active in this phase
        active_roles = [
            role for role in WORKFLOW_ROLES.values()
            if phase in role.active_phases
        ]
        active_roles.sort(key=lambda r: r.priority)

        # Group roles by priority for parallel execution
        priority_groups = self._group_by_priority(active_roles)

        all_responses = []
        current_checkpoint_id = parent_checkpoint_id

        for priority, roles in priority_groups:
            # Execute all roles at this priority level in parallel
            role_prompts = [
                self._augment_prompt_with_role(prompt, role)
                for role in roles
            ]

            # Dispatch to all agents for each role
            group_responses = await asyncio.gather(*[
                self.dispatcher.dispatch_to_all(
                    role_prompt,
                    checkpoint_id=f"{workflow_id}_{phase.value}_{role.name}",
                    session_dir=self.session_dir,
                )
                for role_prompt, role in zip(role_prompts, roles)
            ])

            all_responses.extend(group_responses)

            # Create checkpoint after each priority group
            checkpoint = await self.checkpoint_manager.create_checkpoint(
                workflow_id=workflow_id,
                stage=f"{phase.value}_priority_{priority}",
                prompt=prompt,
                responses=[r for group in group_responses for r in group],
                parent_checkpoint_id=current_checkpoint_id,
            )
            current_checkpoint_id = checkpoint.checkpoint_id

        # Evaluate pass/fail for each role
        evaluations = self._evaluate_roles(all_responses, active_roles)

        return PhaseResult(
            phase=phase,
            checkpoint_id=current_checkpoint_id,
            role_evaluations=evaluations,
            passed=all(e.passed for e in evaluations),
        )
```

---

## 5. OpenAI Deep Research SDK Integration

### 5.1 Research Agent Architecture

**Location:** `app/agents/research/deep_research.py` (new)

```python
from openai import AsyncOpenAI

class DeepResearchAgent:
    """Integration with OpenAI Deep Research SDK."""

    def __init__(self, settings: Settings):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.settings = settings

    async def conduct_research(
        self,
        topic: str,
        *,
        depth: str = "comprehensive",  # "quick", "standard", "comprehensive"
        max_sources: int = 20,
    ) -> ResearchResult:
        """Conduct deep research on a topic."""
        with logfire.span("deep_research", topic=topic, depth=depth):
            # Use OpenAI's research capabilities
            response = await self.client.chat.completions.create(
                model="gpt-4o",  # Or research-specific model when available
                messages=[
                    {
                        "role": "system",
                        "content": self._build_research_system_prompt(depth),
                    },
                    {
                        "role": "user",
                        "content": f"Conduct {depth} research on: {topic}",
                    },
                ],
                tools=self._get_research_tools(),
                tool_choice="auto",
            )

            return self._parse_research_result(response)

    def _get_research_tools(self) -> list[dict]:
        """Define tools available for research."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "num_results": {"type": "integer", "default": 10},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_url",
                    "description": "Read content from a URL",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                        },
                        "required": ["url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_code_repo",
                    "description": "Analyze a code repository",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "repo_url": {"type": "string"},
                            "focus_areas": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["repo_url"],
                    },
                },
            },
        ]
```

### 5.2 Auto-Generated Skills from Research

```python
class SkillGenerator:
    """Generates AI agent skills from research findings."""

    async def generate_skills_from_research(
        self,
        research_result: ResearchResult,
        target_agent: str,
    ) -> list[GeneratedSkill]:
        """Auto-generate skills based on research findings."""
        skills = []

        for finding in research_result.findings:
            if finding.is_actionable:
                skill = await self._create_skill_from_finding(
                    finding,
                    target_agent,
                )
                skills.append(skill)

        return skills

    async def _create_skill_from_finding(
        self,
        finding: ResearchFinding,
        target_agent: str,
    ) -> GeneratedSkill:
        """Create a skill definition from a research finding."""
        return GeneratedSkill(
            name=self._generate_skill_name(finding),
            description=finding.summary,
            implementation=await self._generate_implementation(finding),
            test_cases=await self._generate_test_cases(finding),
            documentation=await self._generate_docs(finding),
            metadata={
                "source": finding.source_url,
                "confidence": finding.confidence_score,
                "generated_at": datetime.utcnow().isoformat(),
            },
        )
```

---

## 6. Django-Style CLI Architecture

### 6.1 Command Discovery Pattern

**Location:** `cli/commands/__init__.py` (extend existing)

```python
import importlib
import pkgutil
from pathlib import Path
from typing import Callable
import click

def discover_commands(package_path: str) -> list[click.Command]:
    """Django-style automatic command discovery."""
    commands = []
    package = importlib.import_module(package_path)

    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package_path}.{modname}")

        # Look for Command class or cli function
        if hasattr(module, "Command"):
            cmd_class = getattr(module, "Command")
            commands.append(cmd_class().as_click_command())
        elif hasattr(module, "cli"):
            commands.append(getattr(module, "cli"))

    return commands

class BaseCommand:
    """Base class for Django-style CLI commands."""

    name: str = ""
    help: str = ""

    def add_arguments(self, parser: click.Command) -> None:
        """Override to add command arguments."""
        pass

    def handle(self, *args, **options) -> None:
        """Override to implement command logic."""
        raise NotImplementedError("Subclasses must implement handle()")

    def as_click_command(self) -> click.Command:
        """Convert to Click command."""
        @click.command(name=self.name, help=self.help)
        @click.pass_context
        def command(ctx, **kwargs):
            self.handle(**kwargs)

        self.add_arguments(command)
        return command
```

### 6.2 Agent Management Commands

**Location:** `cli/commands/agents/` (new directory)

```python
# cli/commands/agents/orchestrate.py
class Command(BaseCommand):
    name = "orchestrate"
    help = "Execute multi-agent orchestration workflow"

    def add_arguments(self, parser):
        parser = click.option("--prompt", "-p", required=True, help="Prompt to send to all agents")(parser)
        parser = click.option("--workflow", "-w", default="default", help="Workflow type")(parser)
        parser = click.option("--checkpoint", "-c", help="Resume from checkpoint")(parser)
        parser = click.option("--phase", help="Specific phase to execute")(parser)
        parser = click.option("--roles", "-r", multiple=True, help="Specific roles to include")(parser)
        return parser

    def handle(self, prompt, workflow, checkpoint, phase, roles):
        """Execute multi-agent orchestration."""
        import asyncio
        from app.agents.orchestration import Orchestrator

        orchestrator = Orchestrator()

        if checkpoint:
            result = asyncio.run(orchestrator.resume_from_checkpoint(checkpoint, prompt))
        else:
            result = asyncio.run(orchestrator.execute(
                prompt=prompt,
                workflow_type=workflow,
                phase=phase,
                roles=list(roles) if roles else None,
            ))

        self._display_result(result)

# cli/commands/agents/checkpoint.py
class Command(BaseCommand):
    name = "checkpoint"
    help = "Manage workflow checkpoints (time-travel)"

    def add_arguments(self, parser):
        parser = click.option("--list", "-l", is_flag=True, help="List all checkpoints")(parser)
        parser = click.option("--show", "-s", help="Show checkpoint details")(parser)
        parser = click.option("--restore", "-r", help="Restore to checkpoint")(parser)
        parser = click.option("--diff", "-d", nargs=2, help="Diff two checkpoints")(parser)
        parser = click.option("--workflow", "-w", help="Filter by workflow ID")(parser)
        return parser

    def handle(self, list, show, restore, diff, workflow):
        """Manage checkpoints."""
        import asyncio
        from app.agents.orchestration import CheckpointManager

        manager = CheckpointManager(get_session_dir())

        if list:
            checkpoints = asyncio.run(manager.list_checkpoints(workflow))
            self._display_checkpoints(checkpoints)
        elif show:
            checkpoint = asyncio.run(manager.get_checkpoint(show))
            self._display_checkpoint_details(checkpoint)
        elif restore:
            result = asyncio.run(manager.restore_checkpoint(restore))
            click.echo(f"Restored to checkpoint: {restore}")
        elif diff:
            diff_result = asyncio.run(manager.diff_checkpoints(diff[0], diff[1]))
            self._display_diff(diff_result)

# cli/commands/agents/research.py
class Command(BaseCommand):
    name = "research"
    help = "Conduct deep research and generate skills"

    def add_arguments(self, parser):
        parser = click.option("--topic", "-t", required=True, help="Research topic")(parser)
        parser = click.option("--depth", "-d", default="comprehensive", help="Research depth")(parser)
        parser = click.option("--generate-skills", "-g", is_flag=True, help="Auto-generate skills")(parser)
        parser = click.option("--target-agent", "-a", help="Target agent for skills")(parser)
        return parser

    def handle(self, topic, depth, generate_skills, target_agent):
        """Conduct research and optionally generate skills."""
        import asyncio
        from app.agents.research import DeepResearchAgent, SkillGenerator

        researcher = DeepResearchAgent(get_settings())
        result = asyncio.run(researcher.conduct_research(topic, depth=depth))

        self._display_research_result(result)

        if generate_skills:
            generator = SkillGenerator()
            skills = asyncio.run(generator.generate_skills_from_research(
                result,
                target_agent or "default",
            ))
            self._display_generated_skills(skills)
```

### 6.3 CLI Entry Point

```python
# cli/main.py
import click
from cli.commands import discover_commands

@click.group()
@click.version_option()
def cli():
    """guilde_lite_tdd_sprint - Multi-Agent AI Orchestration CLI"""
    pass

# Register agent commands
@cli.group()
def agents():
    """AI Agent orchestration commands."""
    pass

# Auto-discover and register agent subcommands
for cmd in discover_commands("cli.commands.agents"):
    agents.add_command(cmd)

# Register other command groups
@cli.group()
def workflow():
    """Workflow management commands."""
    pass

@cli.group()
def telemetry():
    """Telemetry and observability commands."""
    pass

if __name__ == "__main__":
    cli()
```

---

## 7. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Implement `AgentRegistry` with SDK and CLI agent support
- [ ] Implement `PromptDispatcher` for parallel execution
- [ ] Extend existing telemetry with new event types
- [ ] Create basic checkpoint storage

### Phase 2: Orchestration Core (Week 3-4)
- [ ] Implement `CheckpointManager` with time-travel
- [ ] Implement `TelemetryCollector` with multi-backend support
- [ ] Create response markdown storage format
- [ ] Add token tracking across all agents

### Phase 3: Role-Based Workflows (Week 5-6)
- [ ] Implement all 17 role configurations
- [ ] Implement `RoleBasedWorkflowExecutor`
- [ ] Add pass/fail evaluation logic
- [ ] Create role-specific prompt templates

### Phase 4: Research Integration (Week 7-8)
- [ ] Implement `DeepResearchAgent`
- [ ] Implement `SkillGenerator`
- [ ] Add research-to-skill pipeline
- [ ] Create skill validation and testing

### Phase 5: CLI & Polish (Week 9-10)
- [ ] Implement Django-style CLI commands
- [ ] Add comprehensive CLI help and documentation
- [ ] Create example workflows
- [ ] Performance optimization and testing

---

## 8. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Token cost explosion | High | Implement token budgets per workflow, add cost estimation |
| Checkpoint storage growth | Medium | Implement retention policies, compression |
| Agent timeout handling | Medium | Circuit breakers, graceful degradation |
| Conflicting agent responses | Medium | Judge evaluation, consensus mechanisms |
| Rate limiting across providers | High | Implement backoff, queue management |

---

## 9. Success Metrics

| Metric | Target |
|--------|--------|
| Agent response collection rate | 100% (all enabled agents respond) |
| Checkpoint restore accuracy | 100% (perfect state restoration) |
| Telemetry completeness | 100% (all events captured) |
| Role evaluation consistency | >95% (reproducible pass/fail) |
| Research-to-skill conversion | >70% (actionable findings converted) |

---

## Appendix A: Configuration Schema

```python
# Additional settings for multi-agent orchestration
class MultiAgentSettings(BaseSettings):
    # Agent configuration
    ENABLED_AGENTS: list[str] = ["claude-sonnet", "gpt-4o", "codex-cli"]
    AGENT_TIMEOUT_SECONDS: int = 120
    PARALLEL_EXECUTION_LIMIT: int = 10

    # Checkpoint configuration
    CHECKPOINT_RETENTION_DAYS: int = 30
    CHECKPOINT_COMPRESSION: bool = True
    MAX_CHECKPOINTS_PER_WORKFLOW: int = 100

    # Token management
    MAX_TOKENS_PER_AGENT: int = 16000
    MAX_TOKENS_PER_WORKFLOW: int = 100000
    TRACK_TOKEN_COSTS: bool = True

    # Role configuration
    ENABLED_ROLES: list[str] = list(WORKFLOW_ROLES.keys())
    ROLE_TIMEOUT_SECONDS: int = 300
    REQUIRE_ALL_ROLES_PASS: bool = False

    # Research configuration
    RESEARCH_MAX_SOURCES: int = 20
    AUTO_GENERATE_SKILLS: bool = True
    SKILL_VALIDATION_REQUIRED: bool = True
```

---

## Appendix B: File Structure

```
backend/app/agents/
├── orchestration/
│   ├── __init__.py
│   ├── dispatcher.py          # PromptDispatcher
│   ├── checkpoint.py          # CheckpointManager
│   ├── telemetry.py           # TelemetryCollector
│   ├── roles.py               # Role definitions
│   ├── workflow.py            # RoleBasedWorkflowExecutor
│   └── registry.py            # AgentRegistry
├── research/
│   ├── __init__.py
│   ├── deep_research.py       # DeepResearchAgent
│   └── skill_generator.py     # SkillGenerator
├── tools/
│   ├── agent_integration.py   # (existing, extended)
│   └── filesystem.py          # (existing)
└── ralph_planner.py           # (existing, reference for patterns)

cli/commands/
├── __init__.py                # Command discovery
├── agents/
│   ├── __init__.py
│   ├── orchestrate.py         # Multi-agent orchestration
│   ├── checkpoint.py          # Checkpoint management
│   ├── research.py            # Deep research
│   └── registry.py            # Agent registry management
├── workflow/
│   └── ...
└── telemetry/
    └── ...
```

---

*Document generated as part of architectural review for guilde-lite-tdd-sprint multi-agent AI orchestration system.*
