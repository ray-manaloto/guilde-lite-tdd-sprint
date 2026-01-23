# Project Plan

> **Single Source of Truth** - This document is the authoritative project backlog.
> All tasks, audits, and priorities are consolidated here. Do not maintain separate TODO files.

> **SDLC Orchestration MANDATORY** - All features must use the SDLC workflow
>
> **Quick Start:**
> - `/sdlc-orchestration:full-feature "description"` - Full 5-phase workflow with parallel agents
> - `/sdlc-orchestration:research "topic"` - Parallel research with 3 agents
> - `/sdlc-orchestration:phase <phase> "context"` - Run specific phase
>
> **Enforcement:** Phase gates, backpressure hooks, and code review integration are active.
> See `conductor/workflow.md` and `.claude/plugins/sdlc-orchestration/` for details.

---

## Best Practices: Single Source of Truth

**Why one document?** Multiple TODO files, issue trackers, and project plans inevitably drift out of sync. This creates confusion, duplicate work, and missed items.

**This document is the canonical backlog.** All priorities flow from here.

### Maintenance Rules

1. **No separate TODO.md files** - Delete any found; migrate items here
2. **Audits feed this document** - Audit reports (`docs/audit/`) provide analysis; action items are added here
3. **Sprint planning references this** - Sprint items should trace back to entries here
4. **Weekly review** - Mark completed items, reprioritize as needed
5. **Single owner per item** - Every task has one `@role` owner

### Document Structure

```
project-plan.md
├── Goals (why we exist)
├── Milestones (major deliverables)
├── Backlog by Priority (P0 → P3)
│   ├── P0: Critical (this week)
│   ├── P1: High (this sprint)
│   ├── P2: Medium (next sprint)
│   └── P3: Low (backlog)
├── Quick Wins (< 2 hours each)
├── Technical Debt
├── Test Coverage Targets
└── Audit References (links to detailed reports)
```

### Integration with Tools

| Tool | Role | Sync Pattern |
|------|------|--------------|
| **GitHub Issues** | External collaboration | Create from P0/P1 items; link back |
| **Sprint Board UI** | Execution tracking | Create sprint items from this backlog |
| **Audit Reports** | Analysis | Read-only; action items copied here |
| **ADRs** | Decisions | Reference from relevant backlog items |

## Goals

- Port Auto-Claude workflows onto the full-stack FastAPI + Next.js template.
- Provide sprint planning with an optional Kanban view.
- Keep agent UX parity where it matters (agent runs, review loops, UI).

## Milestones (SDLC-Aligned)

| # | Milestone | Status | SDLC Phase | Lead Role |
|---|-----------|--------|------------|-----------|
| 1 | Sprint planning API + web UI | done | Released | @architect |
| 2 | PydanticAI Web UI integration | done | Released | @senior |
| 3 | Testing automation + validation gates | in progress | Quality | @qa |
| 4 | Codex skills for test automation | in progress | Implementation | @senior |
| 5 | Agent-browser + SDK parity | in progress | Implementation | @staff |
| 6 | Kanban board parity | planned | Requirements | @ba |
| 7 | Ralph playbook agentic loop | planned | Design | @architect |
| 8 | Auto-Claude workflow parity | planned | Requirements | @ceo |

### Milestone Details

**M6: Kanban Board Parity** [@ba → @architect → @senior → @qa]
- Requirements: Drag-drop cards, swimlanes, WIP limits
- Design: React DnD integration, state management
- Implementation: Board component, real-time sync
- Quality: E2E tests for drag operations

**M7: Ralph Playbook Agentic Loop** [@architect → @staff → @qa]
- Design: Agent orchestration architecture
- Implementation: Playbook executor, phase tracking
- Quality: Integration tests, replay capability

**M8: Auto-Claude Workflow Parity** [@ceo → @ba → @architect → @senior]
- Requirements: Feature parity analysis
- Design: Migration strategy
- Implementation: Port existing workflows

## Current Sprint (Foundation)

- [x] Sprint models, services, routes, tests
- [x] Sprint board UI (Next.js)
- [x] PydanticAI Web UI CLI entrypoint
- [x] Playwright smoke suite aligned to auth/home/sprints UI
- [x] Codex testing-automation skill (local + package)
- [x] Skill validation checks (script + pytest)
- [x] CLI wrapper skills (add-skill, dev3000, claude-diary)
- [x] Spec-driven workflow (spec draft, complexity, phases, validation)
- [x] Review Logfire logs for auth/LLM usage (OpenAI/Anthropic)
- [x] Verify provider/model selection matches env + docs (Confirmed `gpt-4o-mini` usage)
- [ ] Integration test matrix + coverage for auth/sprints/chat
- [ ] CI: run backend tests + Playwright smoke
- [x] Install agent-browser + agent-skills (project scope)
- [x] Integrate agent-browser tool (default on, allow all URLs)
- [x] Add direct OpenAI + Anthropic SDK clients (response API) with smoke tests
- [x] Document SDK usage + required scopes for API keys
- [x] Add HTTP fetch tool for link access (allow all URLs)
- [ ] Resolve add-skill + dev3000 skill paths for project scope
- [x] Ralph playbook interview step for sprint prompts (AskUserQuestion)
- [x] Sprint planning session storage + APIs (questions/answers)
- [x] Sprint UI planning interview + enforce before create
- [x] Add Logfire trace links to chat messages (WS payload + UI)
- [x] Add sprint planning telemetry panel (judge + subagent trace links, chosen model)
- [ ] Route all user prompts through dual-subagent + judge workflow (OpenAI + Anthropic)
- [ ] Persist subagent outputs + judge decision (DB + telemetry)
- [x] Record history + chosen model metadata per checkpoint/event
- [ ] Kanban board implementation (optional)
- [ ] Agent terminals / live run dashboard

## Validation Requirements

- Every new feature ships with automated tests (unit + API or integration).
- User-facing flows require Playwright coverage.
- CI must run unit + integration + Playwright smoke.
- LLM-dependent checks are explicitly gated (no hidden network calls).

## Next Up (SDLC Role Assignments)

| Task | SDLC Role | Command |
|------|-----------|---------|
| Integration test matrix + CI gating | @qa | `/sdlc-orchestration:role qa "design integration test matrix"` |
| Dual-subagent + judge workflow | @architect | `/sdlc-orchestration:role architect "design dual-subagent judge workflow"` |
| Spec workflow API + CLI entrypoints | @senior | `/sdlc-orchestration:role senior "implement spec workflow API"` |
| Kanban board UX + drag/drop | @junior | `/sdlc-orchestration:role junior "implement Kanban drag-drop UI"` |
| Sprint metrics (velocity, burndown) | @data | `/sdlc-orchestration:role data "design sprint metrics calculations"` |
| Auto-Claude spec runner | @staff | `/sdlc-orchestration:role staff "implement Auto-Claude spec runner"` |

### Completed Tasks
- [x] Agent-browser tool integration + usage doc
- [x] OpenAI/Anthropic SDK usage doc + smoke tests
- [x] HTTP fetch tool for link access
- [x] Checkpoint-level history + chosen model metadata
- [x] Evaluator-Optimizer system integration (PR #18)
- [x] Documentation sync (22 agents, UI/UX layer, evaluator docs)

---

## Consolidated Backlog (2026-01-22)

> **Audit Reports:**
> - Codebase audit: `docs/audit/2026-01-22-comprehensive-audit.md`
> - Framework research: `docs/audit/2026-01-22-template-framework-research.md`
> - DeepAgents ADR: `docs/design/ADR-deepagents-framework-evaluation.md`

### P0 - Critical (Fix This Week) - COMPLETED 2026-01-22

| # | Issue | Category | Source | Effort | Owner | Status |
|---|-------|----------|--------|--------|-------|--------|
| 1 | WebSocket authentication missing | Security | Codebase Audit | 4h | @staff | [x] |
| 2 | Remove hardcoded AUTOCODE_ARTIFACTS_DIR | Bug | Codebase Audit | 1h | @senior | [x] |
| 3 | Add database backup script | DevOps | Codebase Audit | 4h | @devops | [x] |
| 4 | Enable unhandled exception handler | Bug | Codebase Audit | 0.5h | @senior | [x] |
| 5 | Remove K8s secrets from git | Security | Codebase Audit | 2h | @devops | [x] |
| 6 | Add CSRF middleware tests | QA | Codebase Audit | 4h | @qa | [x] |
| 7 | Fix WebSocket broadcast race condition | Bug | Codebase Audit | 2h | @senior | [x] |
| 8 | Add database migration to deploy workflow | DevOps | Codebase Audit | 2h | @devops | [x] |
| 9 | **Harden filesystem sandboxing** | Security | Framework Research | 8h | @staff | [x] |
| 10 | **Git worktree isolation for sprints** | Architecture | Framework Research | 24h | @architect | [x] ADR created |

### P1 - High Priority (This Sprint)

| # | Issue | Category | Source | Effort | Owner | Status |
|---|-------|----------|--------|--------|-------|--------|
| 11 | Sprint planning workflow stepper | UX | Codebase Audit | 8h | @junior | [ ] |
| 12 | Form validation feedback (password strength) | UX | Codebase Audit | 4h | @junior | [ ] |
| 13 | Fix sprint items pagination bug | Bug | Codebase Audit | 2h | @senior | [x] |
| 14 | Add container vulnerability scanning (Trivy) | DevOps | Codebase Audit | 2h | @devops | [ ] |
| 15 | Enable CI coverage threshold (70%) | QA | Codebase Audit | 1h | @qa | [ ] |
| 16 | Implement toast notification system | UX | Codebase Audit | 4h | @junior | [ ] |
| 17 | Improve WebSocket status indicator | UX | Codebase Audit | 2h | @junior | [ ] |
| 18 | Add rate limiting tests | QA | Codebase Audit | 4h | @qa | [ ] |
| 19 | **State backend protocol (PostgresBackend)** | Architecture | Framework Research | 16h | @staff | [ ] |
| 20 | **Background job queue (ARQ/Taskiq)** | Architecture | Framework Research | 16h | @devops | [ ] |
| 21 | **Human approval workflow** | Feature | Framework Research | 16h | @senior | [ ] |
| 22 | **LLM-based evaluators** | Feature | Framework Research | 8h | @staff | [ ] |
| 23 | **WebSocket reconnection + event replay** | Reliability | Framework Research | 8h | @senior | [ ] |
| 24 | **Cross-session memory layer** | Feature | Framework Research | 16h | @architect | [ ] |
| 25 | **DeepAgents SummarizationProcessor** | Feature | Framework Research | 8h | @staff | [ ] |

### P2 - Medium Priority (Next Sprint)

| # | Issue | Category | Source | Effort | Owner | Status |
|---|-------|----------|--------|--------|-------|--------|
| 26 | Create reusable Textarea component | UX | Codebase Audit | 4h | @junior | [ ] |
| 27 | Create styled Select component | UX | 4h | Codebase Audit | @junior | [ ] |
| 28 | Add confirmation dialogs (destructive actions) | UX | Codebase Audit | 4h | @junior | [ ] |
| 29 | Add frontend Dockerfile HEALTHCHECK | DevOps | Codebase Audit | 1h | @devops | [ ] |
| 30 | Create production Procfile | DevOps | Codebase Audit | 1h | @devops | [ ] |
| 31 | Add K8s network policies | DevOps | Codebase Audit | 4h | @devops | [ ] |
| 32 | Fix useChat connection cleanup | Bug | Codebase Audit | 2h | @senior | [ ] |
| 33 | Add OAuth user password reset flow | Bug | Codebase Audit | 4h | @senior | [ ] |
| 34 | **Enhanced Deps (DeepAgentDeps pattern)** | Architecture | Framework Research | 4h | @staff | [ ] |
| 35 | **SubAgentToolset integration** | Feature | Framework Research | 16h | @staff | [ ] |
| 36 | **Enable conversation persistence** | Feature | Framework Research | 8h | @senior | [ ] |
| 37 | **Kanban board UI** | Feature | Framework Research | 24h | @junior | [ ] |

### P3 - Low Priority (Backlog)

| # | Issue | Category | Source | Effort | Owner | Status |
|---|-------|----------|--------|--------|-------|--------|
| 38 | Split sprints/page.tsx (1034 lines) | Code Quality | Codebase Audit | 8h | @senior | [ ] |
| 39 | Split PhaseRunner (800+ lines) | Code Quality | Codebase Audit | 8h | @staff | [ ] |
| 40 | Add skip navigation link | A11Y | Codebase Audit | 2h | @junior | [ ] |
| 41 | Fix color contrast issues | A11Y | Codebase Audit | 2h | @junior | [ ] |
| 42 | Add aria-live regions for updates | A11Y | Codebase Audit | 4h | @junior | [ ] |
| 43 | Create Grafana dashboards | DevOps | Codebase Audit | 4h | @devops | [ ] |
| 44 | Configure alerting rules | DevOps | Codebase Audit | 4h | @devops | [ ] |
| 45 | Set up centralized logging | DevOps | Codebase Audit | 8h | @devops | [ ] |
| 46 | **LangSmith integration** | Observability | Framework Research | 4h | @devops | [ ] |
| 47 | **Skills file loader (markdown tools)** | Feature | Framework Research | 8h | @staff | [ ] |
| 48 | **Enhanced Logfire spans** | Observability | Self-Healing Research | 4h | @devops | [ ] |
| 49 | **Sentry user context + breadcrumbs** | Observability | Self-Healing Research | 2h | @senior | [ ] |
| 50 | **Circuit breakers (aiobreaker)** | Resilience | Self-Healing Research | 8h | @staff | [ ] |
| 51 | **dev3000 integration** | DevX | Self-Healing Research | 8h | @devops | [ ] |
| 52 | **healing-agent auto-fix** | Self-Healing | Self-Healing Research | 16h | @staff | [ ] |
| 53 | **Unleash feature flags** | Rollback | Self-Healing Research | 12h | @devops | [ ] |

### Quick Wins (< 2 hours each)

- [ ] Enable exception handler in production (0.5h)
- [ ] Remove hardcoded AUTOCODE_ARTIFACTS_DIR (1h)
- [ ] Enable CI coverage threshold (1h)
- [ ] Add production password validators (1h)
- [ ] Add frontend Dockerfile HEALTHCHECK (1h)
- [ ] Create production Procfile (1h)
- [ ] Add aria-label to chat input (0.5h)
- [ ] Fix button heights consistency (1h)

### Test Coverage Targets

| Module | Current | Target | Gap |
|--------|---------|--------|-----|
| Backend Unit | ~45% | 80% | -35% |
| Frontend Unit | ~25% | 70% | -45% |
| Security Modules | ~15% | 90% | -75% |
| E2E Tests | ~30% | 60% | -30% |

### Missing UI Components (Create in Design System)

- [ ] Textarea (styled with error states)
- [ ] Select (styled dropdown)
- [ ] Checkbox (styled with label)
- [ ] Skeleton (loading placeholders)
- [ ] Toast/Notification
- [ ] AlertDialog (confirmations)
- [ ] Stepper (multi-step workflows)
- [ ] Progress (completion indicator)

---

## Framework & Architecture Decisions

> Full analysis: `docs/audit/2026-01-22-template-framework-research.md`

### Template Usage Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| **Template features used** | 85% | Most infrastructure adopted |
| **Custom extensions** | Significant | Dual-subagent, evaluators, PhaseRunner |
| **Gaps** | Minor | Conversation persistence disabled |
| **CLI tools** | Keep both | Makefile + devctl.sh serve different purposes |

### DeepAgents Framework Decision

**Decision:** Adopt Partially (not full migration)

| Feature | Action | Rationale |
|---------|--------|-----------|
| SummarizationProcessor | **Adopt** | Solves token overflow |
| DeepAgentDeps pattern | **Adopt** | Better file/state handling |
| SubAgentToolset | **Evaluate** | Try on new features only |
| Skills System | **Skip** | Our feature flags work |
| Dual-provider + judge | **Keep ours** | No DeepAgents equivalent |

### Architecture Priorities

```
Sprint Current: Security & Stability
├── P0 items 1-10 (critical fixes)
├── Filesystem sandboxing
└── Exception handling

Sprint Next: Production Readiness
├── Git worktree isolation
├── State backend protocol
├── Background job queue
└── Human approval workflow

Sprint Future: Enhancement
├── DeepAgents integration
├── Cross-session memory
└── Kanban board
```

### Technical Debt Tracking

| Debt | Risk | Mitigation |
|------|------|------------|
| `Deps` dataclass too simple | Medium | Extend with DeepAgentDeps pattern (P2) |
| `WorkflowTracker` writes JSON only | Medium | Add StateBackend protocol (P1) |
| `FeedbackMemory` not persisted | Medium | Add DB persistence (P1) |
| Filesystem tools need hardening | **High** | Strict sandboxing (P0) |
| PhaseRunner 800+ lines | Low | Split into services (P3) |

---

## Effort Summary

| Priority | Items | Total Effort |
|----------|-------|--------------|
| P0 Critical | 10 | ~52 hours |
| P1 High | 15 | ~117 hours |
| P2 Medium | 12 | ~72 hours |
| P3 Low | 10 | ~52 hours |
| **Total** | **47** | **~293 hours** |

---

## Audit References

| Date | Report | Focus |
|------|--------|-------|
| 2026-01-22 | `docs/audit/2026-01-22-comprehensive-audit.md` | UI/UX, Bugs, QA, Deployment |
| 2026-01-22 | `docs/audit/2026-01-22-template-framework-research.md` | Template, DeepAgents, Feature Gaps |
| - | `docs/design/ADR-deepagents-framework-evaluation.md` | DeepAgents decision record |

---

## Recent Changes (2026-01-22)

### SDLC Full Feature Workflow Executed

**Trigger:** Sprint creation API returned pagination error
**Root Cause:** `TypeError: _new_paginate_sign() missing 1 required positional argument: 'query'`
**Location:** `backend/app/api/routes/v1/sprints.py:102`

### Completed Work

| Phase | Agents | Output |
|-------|--------|--------|
| **Diagnosis** | Debugger | Log analysis, stack trace identification |
| **Requirements** | CEO, BA, Research | 8 user stories, missing roles identified |
| **Design** | Architect, Data, DevOps | ADR-001, ADR-002, diagnostic schemas |
| **Implementation** | Staff, Senior, Junior, DevOps | Pagination fix, error boundaries, debugger role |
| **Quality** | QA, Reviewer, Perf | 14 new tests, datetime fix, perf validation |
| **Release** | All sequential | Tests pass (486 total), docs updated |

### Artifacts Created

| File | Description |
|------|-------------|
| `backend/app/schemas/diagnostic.py` | 20+ schemas for error tracking |
| `backend/tests/api/test_sprint_items_pagination.py` | 14 pagination tests |
| `frontend/src/app/[locale]/(dashboard)/error.tsx` | Dashboard error boundary |
| `frontend/src/app/[locale]/(dashboard)/sprints/error.tsx` | Sprint error boundary |
| `.claude/plugins/sdlc-orchestration/agents/debugger.md` | New debugger role |
| `docs/design/ADR-001-pagination-pattern.md` | Pagination decision |
| `docs/design/ADR-002-self-diagnostic-architecture.md` | Self-healing architecture |
| `docker-compose.diagnostic.yml` | Diagnostic services overlay |

### New SDLC Role Added

**Debugger** (`/sdlc-orchestration:role debugger "task"`):
- Root cause analysis
- Stack trace interpretation
- Git bisect for regression hunting
- State inspection
- 8-step debugging methodology

### Self-Healing Research Summary

Evaluated tools for autonomous bug detection/fixing:
- **dev3000** - MCP server for AI debugging (recommended for P2)
- **healing-agent** - Auto-fix Python exceptions (recommended for P3)
- **aiobreaker** - Circuit breaker pattern (recommended for P2)

Backlog items #48-53 added for implementation.

### Test Count

| Before | After | Delta |
|--------|-------|-------|
| 472 | 486 | +14 |

### For New AI Agents

1. **Read** `CLAUDE.md` for project overview and SDLC workflow
2. **Check** `docs/project-plan.md` (this file) for current backlog
3. **Use** `/sdlc-orchestration:full-feature` for new features
4. **Use** `/sdlc-orchestration:role debugger` for bug investigation
5. **Reference** `docs/design/ADR-*` for architectural decisions
