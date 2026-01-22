# Project Plan

> **SDLC Orchestration MANDATORY** - All features must use the SDLC workflow
>
> **Quick Start:**
> - `/sdlc-orchestration:full-feature "description"` - Full 5-phase workflow with parallel agents
> - `/sdlc-orchestration:research "topic"` - Parallel research with 3 agents
> - `/sdlc-orchestration:phase <phase> "context"` - Run specific phase
>
> **Enforcement:** Phase gates, backpressure hooks, and code review integration are active.
> See `conductor/workflow.md` and `.claude/plugins/sdlc-orchestration/` for details.

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
