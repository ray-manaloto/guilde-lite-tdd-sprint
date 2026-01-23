# Template & Framework Research Audit

**Date:** 2026-01-22
**Auditors:** SDLC Parallel Agents (Research Scientist, Software Architect, Staff Engineer)
**Scope:** Template feature usage, DeepAgents evaluation, Feature gap analysis

---

## Executive Summary

This audit evaluates our implementation against the `full-stack-fastapi-nextjs-llm-template`, analyzes the `pydantic-deepagents` framework for potential adoption, and identifies feature gaps from external sources that could improve system robustness.

### Key Findings

| Area | Score | Recommendation |
|------|-------|----------------|
| **Template Usage** | 85/100 | Using most features; enable conversation persistence |
| **DeepAgents Fit** | Partial Adopt | Adopt SummarizationProcessor, keep our dual-provider pattern |
| **Feature Gaps** | 12 P0/P1 items | Priority: workspace isolation, state backends, background jobs |

---

## Part 1: Template Feature Usage Analysis

### Feature Comparison Matrix

| Feature | Template Has | We Use | Our Extension | Gap |
|---------|--------------|--------|---------------|-----|
| **Planning** | Basic | ✅ | Dual-subagent + judge | None |
| **Filesystem Tools** | Basic | ✅ | Session sandboxing | None |
| **Subagent Capabilities** | Basic | ✅ | Full `AgentTddService` orchestration | None |
| **Type-safe AI Tools** | PydanticAI | ✅ | Custom tools (browser, http, fs) | None |
| **WebSocket Streaming** | Yes | ✅ | Full event streaming | None |
| **Conversation Persistence** | Yes | ❌ | Not enabled | **GAP** |
| **Logfire** | Yes | ✅ | Full instrumentation + trace links | None |
| **LangSmith** | Yes | ❌ | Not configured | Optional |
| **Sentry** | Yes | ✅ | Configured via `SENTRY_DSN` | None |
| **Prometheus** | Yes | ✅ | `/metrics` endpoint active | None |
| **Rate Limiting** | Yes | ✅ | `slowapi` configured | None |
| **Celery** | Yes | ✅ | Beat + Worker setup | None |
| **Webhooks** | Yes | ✅ | Full CRUD + delivery | None |
| **Admin Panel** | Yes | ✅ | SQLAdmin with auto-discovery | None |
| **JWT + Refresh** | Yes | ✅ | 30min access, 7d refresh | None |
| **API Keys** | Yes | ✅ | `X-API-Key` header | None |
| **OAuth2 Google** | Yes | ✅ | authlib integration | None |
| **Django-style CLI** | Yes | ✅ | Auto-discovery in `commands/` | None |
| **Tool Visualization** | Yes | ✅ | `tool-call-card.tsx` | None |

### Custom Extensions (Value-Add)

We've significantly extended the template in these areas:

1. **Dual-Subagent + Judge Pattern** (`ralph_planner.py`)
   - Runs both OpenAI and Anthropic in parallel
   - Judge selects best response
   - Not available in template

2. **AgentTddService** (`services/agent_tdd.py`)
   - Full orchestration with checkpointing
   - Database models: `AgentRun`, `AgentCandidate`, `AgentDecision`, `AgentCheckpoint`
   - Multi-provider execution with telemetry

3. **PhaseRunner** (`runners/phase_runner.py`)
   - Sprint execution workflow
   - Evaluator-optimizer integration
   - WebSocket event streaming

4. **Evaluator System** (`runners/evaluators/`)
   - RuffLintEvaluator, PytestEvaluator, TypeCheckEvaluator
   - FeedbackMemory for retry optimization

### CLI Tools Assessment

| Tool | Purpose | Recommendation |
|------|---------|----------------|
| `Makefile` | Standard operations (lint, test, db) | Keep |
| `scripts/devctl.sh` | Service management, tmux, preflight | Keep |

**Decision:** Keep both. They serve different purposes:
- `Makefile` for CI/CD and standard commands
- `devctl.sh` for local development workflow

**Do NOT migrate off devctl.sh** - it provides service orchestration that Makefile doesn't.

### Gaps to Address

| Gap | Priority | Action |
|-----|----------|--------|
| Conversation persistence disabled | P2 | Enable if product requires chat history |
| LangSmith not configured | P3 | Optional - Logfire suffices |

---

## Part 2: DeepAgents Framework Evaluation

### Recommendation: **Adopt Partially**

### Comparison Matrix

| Aspect | DeepAgents | Our Current | Winner |
|--------|------------|-------------|--------|
| Multi-agent orchestration | Built-in SubAgentToolset | Manual `AgentTddService` | **DeepAgents** |
| Tool definition | Toolsets + Skills | `@agent.tool` decorator | Tie |
| Streaming | Full | Full | Tie |
| State management | Rich `DeepAgentDeps` + backends | Simple `Deps` dataclass | **DeepAgents** |
| Context management | SummarizationProcessor | None | **DeepAgents** |
| Human-in-the-loop | `interrupt_on` + DeferredToolRequests | None | **DeepAgents** |
| Multi-provider support | Single model per agent | Dual-provider + judge | **Our Current** |
| Observability | Basic pydantic-ai | Custom Logfire integration | **Our Current** |
| File uploads | Built-in `upload_file` | Session directory only | **DeepAgents** |

### Features to Adopt

| Priority | Feature | Effort | Value |
|----------|---------|--------|-------|
| **High** | SummarizationProcessor | 4-8h | Solves token overflow in long conversations |
| **Medium** | DeepAgentDeps pattern | 2-4h | Better file handling, backend abstraction |
| **Low** | SubAgentToolset | 8-16h | Structured delegation (new features only) |
| **Skip** | Skills System | - | Our feature flags work fine |

### Features to Keep (Our Implementation)

| Feature | Reason |
|---------|--------|
| Dual-provider + judge pattern | DeepAgents has no equivalent; provides quality control |
| Custom Logfire integration | Better observability than DeepAgents default |
| Evaluator system | Deterministic validation not in DeepAgents |

### Migration Path

```
Sprint 1: pip install pydantic-deep; add SummarizationProcessor
Sprint 2: Extend Deps class from DeepAgentDeps
Sprint 3: Evaluate SubAgentToolset on one new feature
```

### Risk Assessment

- **Low Risk**: Both frameworks share pydantic-ai foundation
- **Medium Risk**: Deps structure change affects all tools
- **Mitigated**: Keep battle-tested multi-agent patterns; don't force migration

---

## Part 3: Feature Gap Analysis

### External Sources Analyzed

1. **pydantic-deepagents** - Multi-agent patterns, state backends, toolsets
2. **full-stack-fastapi-nextjs-llm-template** - Production infrastructure
3. **Auto-Claude** - Workflow patterns, git worktree isolation

### P0 - Critical (Before Production)

| # | Feature | Source | Risk if Missing | Effort |
|---|---------|--------|-----------------|--------|
| 1 | **Git Worktree Isolation** | Auto-Claude | Agent writes outside sandbox | 3-5 days |
| 2 | **Filesystem Sandboxing Hardening** | pydantic-deepagents | Path traversal vulnerability | 1 day |

### P1 - Significant Improvement

| # | Feature | Source | Benefit | Effort |
|---|---------|--------|---------|--------|
| 3 | State Backend Protocol | pydantic-deepagents | Testability, persistence flexibility | 2-3 days |
| 4 | Background Job Queue | full-stack-template | Long sprints won't block API | 2 days |
| 5 | Human Approval Workflow | pydantic-deepagents | Governance for auto code changes | 2 days |
| 6 | LLM-Based Evaluators | pydantic-deepagents | Better quality assessment | 1-2 days |
| 7 | WebSocket Reconnection | full-stack-template | Reliability, event replay | 1-2 days |
| 8 | Cross-Session Memory | Auto-Claude | Pattern learning across sprints | 2 days |
| 9 | History Processors | pydantic-deepagents | Token limit management | 1 day |

### P2 - Nice to Have

| # | Feature | Source | Effort |
|---|---------|--------|--------|
| 10 | SubAgentToolset | pydantic-deepagents | 1-2 days |
| 11 | Enhanced Deps (DeepAgentDeps) | pydantic-deepagents | 2-4h |
| 12 | Kanban Board UI | Auto-Claude | 2-3 days |

### Features We Built That Are Brittle

| Our Implementation | Better Alternative | Risk | Action |
|--------------------|-------------------|------|--------|
| `Deps` dataclass (17 lines) | `DeepAgentDeps` | Medium | Extend in Sprint 2 |
| `WorkflowTracker` (JSON files) | `StateBackend` protocol | Medium | Refactor to protocol |
| `FeedbackMemory` (in-memory) | Cross-session persistence | Medium | Add DB persistence |
| Filesystem tools (basic validation) | Proper sandboxing | **High** | Harden immediately |

### Implementation Specifications

#### 1. Git Worktree Isolation (P0)

**Current:** Files written to `AUTOCODE_ARTIFACTS_DIR/{timestamp}/` with no git isolation.

**Proposed:**
```python
# backend/app/services/worktree.py (NEW)
class WorktreeManager:
    async def create_worktree(self, sprint_id: UUID, base_branch: str = "main") -> Path:
        """Create isolated worktree for sprint execution."""
        worktree_path = self.base_dir / f"worktree-{sprint_id}"
        branch_name = f"sprint/{sprint_id}"
        # git worktree add -b {branch_name} {worktree_path} {base_branch}

    async def cleanup_worktree(self, sprint_id: UUID) -> None:
        """Remove worktree after sprint completion."""
```

#### 2. State Backend Protocol (P1)

**Current:** `WorkflowTracker` writes directly to JSON files.

**Proposed:**
```python
# backend/app/runners/backends/protocol.py (NEW)
class StateBackend(Protocol):
    async def save_state(self, key: str, state: dict) -> None: ...
    async def load_state(self, key: str) -> dict | None: ...
    async def list_checkpoints(self, prefix: str) -> list[str]: ...

# Implementations:
# - LocalBackend (current behavior)
# - PostgresBackend (production persistence)
# - CompositeBackend (multi-backend)
```

#### 3. Enhanced Deps (P2)

**Current:** Minimal 4-field dataclass.

**Proposed:**
```python
@dataclass
class Deps:
    user_id: str | None = None
    user_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    session_dir: Path | None = None
    # NEW:
    backend: StateBackend | None = None
    uploaded_files: list[Path] = field(default_factory=list)
    confirmation_callback: Callable | None = None
    memory_context: dict[str, Any] = field(default_factory=dict)
```

---

## Part 4: Consolidated Recommendations

### Immediate Actions (This Week)

1. **Harden filesystem sandboxing** - Add strict path validation
2. **Review AUTOCODE_ARTIFACTS_DIR** - Remove hardcoded path
3. **Enable exception handler** - Already in P0 from previous audit

### Sprint Priorities

| Sprint | Focus | Items |
|--------|-------|-------|
| **Current** | Security + Stability | P0 items 1-8 from codebase audit + filesystem hardening |
| **Next** | Production Readiness | Git worktree, state backends, background jobs |
| **Future** | Enhancement | DeepAgents integration, cross-session memory |

### Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Keep dual-provider + judge | ✅ Yes | Unique value, no DeepAgents equivalent |
| Adopt DeepAgents fully | ❌ No | Too disruptive, partial adoption better |
| Migrate off devctl.sh | ❌ No | Provides value Makefile doesn't |
| Enable conversation persistence | ⏸️ Defer | Enable when product requires |

---

## Appendix A: Files Referenced

**Our Implementation:**
- `backend/app/agents/ralph_planner.py` - Dual-subagent planning
- `backend/app/agents/deps.py` - Dependencies dataclass
- `backend/app/agents/assistant.py` - Base agent
- `backend/app/runners/phase_runner.py` - Phase orchestration
- `backend/app/services/agent_tdd.py` - Multi-provider TDD service
- `backend/app/services/workflow_tracker.py` - Workflow state
- `backend/app/runners/evaluators/` - Evaluator system
- `backend/app/agents/tools/filesystem.py` - Filesystem tools
- `scripts/devctl.sh` - Service management

**External Sources:**
- https://github.com/vstorm-co/pydantic-deepagents
- https://github.com/vstorm-co/full-stack-fastapi-nextjs-llm-template
- https://github.com/AndyMik90/Auto-Claude

## Appendix B: Related Documents

- `docs/audit/2026-01-22-comprehensive-audit.md` - Codebase audit (UI/UX, bugs, QA, deployment)
- `docs/design/ADR-deepagents-framework-evaluation.md` - DeepAgents ADR
- `docs/design/evaluator-optimizer-architecture.md` - Evaluator system design

---

*Report generated by SDLC Orchestration parallel research workflow*
