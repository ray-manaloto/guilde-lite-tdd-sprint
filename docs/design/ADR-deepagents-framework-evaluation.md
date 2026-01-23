# ADR-001: DeepAgents Framework Evaluation

## Status
**Proposed** - Under evaluation for adoption

## Date
2026-01-22

## Context

We are evaluating the **pydantic-deep** (DeepAgents) framework from vstorm-co as a potential replacement for or complement to our current PydanticAI-based agent implementation. This evaluation is driven by the need to:

1. Simplify multi-agent orchestration
2. Improve context/token management for long-running sessions
3. Standardize tool/skill patterns across agents
4. Enhance state management and file handling

## Current State Analysis

### Our Current Agent Architecture

**Location:** `/backend/app/agents/`

**Key Components:**

| File | Purpose | Patterns Used |
|------|---------|---------------|
| `assistant.py` | Base agent with dual-provider support | Factory pattern, tool registration via decorators |
| `sprint_agent.py` | TDD-focused development agent | Inheritance from AssistantAgent |
| `ralph_planner.py` | Planning interview with judge pattern | Dual-subagent + judge orchestration |
| `deps.py` | Simple dataclass dependencies | Minimal state (user_id, metadata, session_dir) |
| `tools/*.py` | Tool implementations | Pure functions with RunContext |

**Current Patterns:**

```python
# Agent creation (assistant.py)
class AssistantAgent:
    def __init__(self, model_name, temperature, system_prompt, llm_provider):
        ...

    def _build_model(self):
        # Multi-provider: Anthropic, OpenAI, OpenRouter
        ...

    def _register_tools(self, agent):
        @agent.tool
        async def current_datetime(ctx: RunContext[Deps]) -> str:
            ...

# Dependencies (deps.py)
@dataclass
class Deps:
    user_id: str | None = None
    user_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    session_dir: Path | None = None
```

**Current Multi-Agent Pattern (ralph_planner.py):**

```python
# Dual-subagent with judge pattern
async def _run_dual_subagent_planning(prompt, max_questions):
    # Run OpenAI candidate
    questions_openai, telemetry_openai = await _run_planning_agent(
        prompt, provider="openai", model_name=settings.model_for_provider("openai")
    )
    # Run Anthropic candidate
    questions_anthropic, telemetry_anthropic = await _run_planning_agent(
        prompt, provider="anthropic", model_name=settings.model_for_provider("anthropic")
    )
    # Judge selects best
    selected = await _run_planning_judge(...)
```

### Strengths of Current Implementation

1. **Dual-provider execution** - Already supports OpenAI + Anthropic
2. **Simple, explicit code** - Easy to understand and debug
3. **Judge/evaluator pattern** - Quality control for outputs
4. **Flexible tool registration** - Feature-flagged tools (AGENT_BROWSER_ENABLED, etc.)
5. **Telemetry integration** - Built-in Logfire/OpenTelemetry support

### Pain Points

1. **No automatic context management** - Token overflow risk in long sessions
2. **Manual multi-agent coordination** - Custom code for each orchestration pattern
3. **No standard skill/capability system** - Tools are ad-hoc
4. **Limited state management** - Simple dataclass, no file tracking
5. **No human-in-the-loop primitives** - No standard approval workflow

---

## DeepAgents Framework Analysis

### Core Architecture

**Package:** `pydantic-deep` (v0.2.13)
**Foundation:** Built on pydantic-ai
**Modular Components:**
- `pydantic-ai-backend` - File storage, Docker sandbox
- `pydantic-ai-todo` - Task planning toolset
- `pydantic-deep` - Core orchestration

### Key Features

#### 1. Agent Factory Pattern

```python
from pydantic_deep import create_deep_agent, create_default_deps

agent = create_deep_agent(
    model="openai:gpt-4.1",
    instructions="Custom instructions",
    include_todo=True,          # Task planning
    include_filesystem=True,    # File operations
    include_subagents=True,     # Multi-agent delegation
    include_skills=True,        # Modular capabilities
    output_type=StructuredOutput,  # Type-safe responses
    history_processors=[summarization_processor],  # Context management
)
```

#### 2. Rich Dependencies Container

```python
@dataclass
class DeepAgentDeps:
    backend: BackendProtocol        # StateBackend, LocalBackend, DockerSandbox
    files: dict[str, FileData]      # In-memory file cache
    todos: list[Todo]               # Task planning state
    subagents: dict[str, Any]       # Cached subagent instances
    uploads: dict[str, UploadedFile] # User-uploaded file tracking

    def upload_file(self, name: str, content: bytes) -> str: ...
    def get_uploads_summary(self) -> str: ...  # For system prompt
    def clone_for_subagent(self) -> DeepAgentDeps: ...  # Isolated subagent deps
```

#### 3. Subagent Toolset

```python
# Built-in subagent delegation
subagent_configs = [
    SubAgentConfig(
        name="code-analyzer",
        description="Analyzes code for issues",
        instructions="You are a code analysis expert...",
        model="openai:gpt-4.1",
    ),
]

agent = create_deep_agent(subagents=subagent_configs)

# Agent can now delegate: task("Analyze this code", subagent_type="code-analyzer")
```

#### 4. Skills System

```markdown
# SKILL.md format
---
name: code-review
description: Reviews code for quality issues
version: 1.0.0
tags: [quality, review]
---

## Instructions
When reviewing code, check for:
1. Security vulnerabilities
2. Performance issues
3. Code style violations
...
```

```python
# Skills discovery
agent = create_deep_agent(
    skill_directories=[{"path": "~/.pydantic-deep/skills", "recursive": True}]
)
# Agent can: list_skills(), load_skill("code-review"), read_skill_resource(...)
```

#### 5. Context Summarization

```python
from pydantic_deep.processors import create_summarization_processor

processor = create_summarization_processor(
    model="openai:gpt-4.1",
    trigger=("tokens", 100000),    # Summarize at 100k tokens
    keep=("messages", 20),         # Keep last 20 messages
)

agent = create_deep_agent(history_processors=[processor])
```

#### 6. Human-in-the-Loop

```python
agent = create_deep_agent(
    interrupt_on={
        "execute": True,           # Pause for shell commands
        "write_file": True,        # Pause for file writes
    },
)
# Returns DeferredToolRequests for approval workflow
```

---

## Comparison Matrix

| Aspect | DeepAgents | Our Current | Winner |
|--------|------------|-------------|--------|
| **Multi-agent orchestration** | Built-in SubAgentToolset with isolated deps | Manual implementation per use case | **DeepAgents** - standardized pattern |
| **Tool definition pattern** | Toolsets (FunctionToolset) + Skills | @agent.tool decorator | **Tie** - both use pydantic-ai patterns |
| **Streaming support** | Full streaming via pydantic-ai | Full streaming via agent.iter() | **Tie** |
| **State management** | Rich DeepAgentDeps with file tracking | Simple Deps dataclass | **DeepAgents** - more complete |
| **Context management** | SummarizationProcessor built-in | None | **DeepAgents** - critical feature |
| **Error handling** | Try/except in tools, subagent isolation | Try/except in tools | **Tie** |
| **Testing** | pytest with mock agents | pytest | **Tie** |
| **Human-in-the-loop** | interrupt_on + DeferredToolRequests | None | **DeepAgents** |
| **Multi-provider support** | Single model per agent | Dual-provider + judge | **Our Current** - more sophisticated |
| **Observability** | Relies on pydantic-ai | Custom Logfire + telemetry spans | **Our Current** - more integrated |
| **File uploads** | Built-in upload_file + tracking | Session directory only | **DeepAgents** |
| **Skills/capabilities** | Markdown-based skill system | Feature flags per tool | **DeepAgents** |

---

## Migration Assessment

### What Would Need to Change

#### Phase 1: Adopt DeepAgentDeps (Low Risk)

```python
# Current
@dataclass
class Deps:
    user_id: str | None = None
    session_dir: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

# Proposed: Extend DeepAgentDeps
from pydantic_deep.deps import DeepAgentDeps as BaseDeepAgentDeps

@dataclass
class Deps(BaseDeepAgentDeps):
    user_id: str | None = None
    user_name: str | None = None
    # Inherits: backend, files, todos, subagents, uploads
```

#### Phase 2: Adopt Context Summarization (Medium Risk)

```python
from pydantic_deep.processors import create_summarization_processor

processor = create_summarization_processor(
    trigger=("tokens", 100000),
    keep=("messages", 20),
)

class AssistantAgent:
    def _create_agent(self) -> Agent[Deps, str]:
        return Agent[Deps, str](
            model=self._build_model(),
            history_processors=[processor],  # Add this
            ...
        )
```

#### Phase 3: Adopt SubAgentToolset (Medium Risk)

```python
# Replace ralph_planner.py dual-subagent pattern with:
from pydantic_deep.toolsets.subagents import create_subagent_toolset

subagent_configs = [
    SubAgentConfig(
        name="planner-openai",
        description="Planning agent using OpenAI",
        instructions=RALPH_PLANNING_SYSTEM_PROMPT,
        model="openai:gpt-4.1",
    ),
    SubAgentConfig(
        name="planner-anthropic",
        description="Planning agent using Anthropic",
        instructions=RALPH_PLANNING_SYSTEM_PROMPT,
        model="anthropic:claude-sonnet-4-20250514",
    ),
]
```

**Note:** Our dual-provider + judge pattern is more sophisticated. We might keep this custom.

#### Phase 4: Adopt Skills System (Optional)

Convert our tool implementations to skills:

```
skills/
  browser-automation/
    SKILL.md
    examples/
  http-fetch/
    SKILL.md
  filesystem/
    SKILL.md
```

### Breaking Changes

1. **Deps signature change** - All tools using `ctx.deps` would need updates
2. **Agent instantiation** - Factory function vs class constructor
3. **Tool registration** - Toolsets vs inline @agent.tool

### Effort Estimate

| Phase | Effort | Risk | Value |
|-------|--------|------|-------|
| Phase 1: Deps extension | 2-4 hours | Low | Medium |
| Phase 2: Summarization | 4-8 hours | Medium | **High** |
| Phase 3: SubAgents | 8-16 hours | Medium | Medium |
| Phase 4: Skills | 16-24 hours | Low | Low |
| **Total** | 30-52 hours | | |

### Risk Assessment

**Low Risks:**
- Both frameworks use pydantic-ai as foundation
- Incremental adoption possible
- Same tool calling patterns

**Medium Risks:**
- Deps structure change ripples through codebase
- Summarization quality depends on prompt engineering
- SubAgent isolation may lose telemetry correlation

**High Risks:**
- Our dual-provider + judge pattern is custom; DeepAgents doesn't have equivalent
- Migration during active development could cause instability

---

## Recommendation

### Verdict: **Adopt Partially**

**Rationale:**

1. **Adopt Summarization Processor (Priority: High)**
   - Solves critical token overflow issue
   - Low integration effort
   - Can be added to existing AssistantAgent without restructuring

2. **Adopt DeepAgentDeps Pattern (Priority: Medium)**
   - Better file tracking and uploads
   - Todos integration for planning
   - Can extend rather than replace

3. **Keep Our Multi-Provider + Judge Pattern**
   - DeepAgents doesn't have equivalent sophistication
   - Our implementation is battle-tested for quality control

4. **Skip Skills System (Priority: Low)**
   - Our feature-flagged tools are simpler
   - Skills add complexity without clear benefit for our use case

5. **Consider SubAgentToolset for New Features**
   - Don't migrate existing ralph_planner
   - Use for new multi-agent features

### Implementation Plan

```
Sprint 1: Add Summarization
  - Install pydantic-deep
  - Add SummarizationProcessor to AssistantAgent
  - Test token management

Sprint 2: Extend Deps
  - Create Deps extending DeepAgentDeps
  - Update tools to use new capabilities
  - Add file upload support

Sprint 3: Evaluate SubAgents
  - Build one new feature using SubAgentToolset
  - Compare with custom implementation
  - Decide on broader adoption
```

---

## Consequences

### Positive
- Solves token overflow problem
- Better file handling primitives
- Standard subagent pattern available
- Aligns with upstream pydantic-ai direction

### Negative
- Additional dependency to manage
- Partial adoption creates cognitive overhead
- DeepAgents is young (v0.2.x)

### Alternatives Considered

1. **Full Adoption** - Too risky, loses our dual-provider + judge pattern
2. **Don't Adopt** - Misses critical summarization feature
3. **Build Custom Summarization** - Reinventing wheel, DeepAgents version is well-designed
4. **Wait for pydantic-ai Core** - Summarization coming in late January 2025, but DeepAgents is compatible

---

## References

- [pydantic-deep GitHub](https://github.com/vstorm-co/pydantic-deepagents)
- [pydantic-ai-backend GitHub](https://github.com/vstorm-co/pydantic-ai-backend)
- [pydantic-ai-todo GitHub](https://github.com/vstorm-co/pydantic-ai-todo)
- [pydantic-ai PR #3780 - Summarization](https://github.com/pydantic/pydantic-ai/pull/3780)
- Our current agent code: `/backend/app/agents/`
