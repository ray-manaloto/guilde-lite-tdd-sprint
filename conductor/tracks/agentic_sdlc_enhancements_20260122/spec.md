# Spec: Agentic SDLC Enhancements

## Summary

Enhance the parallel agentic SDLC workflow with explicit UI/UX roles, stronger
context engineering via subagents, continuous documentation synchronization,
resilient session state recovery, and improved QA automation (smoke E2E per PR,
full E2E nightly). Research-backed hooks, skills, tools, and commands will be
proposed and implemented under Conductor.

## Objectives

- Add UI/UX roles with code change responsibilities and QA gates.
- Improve agentic context engineering with dedicated subagents.
- Run a documentation-engineer subagent in parallel to keep code/docs/plan
  synchronized and recoverable after session crashes.
- Research and recommend skills/plugins/tools/hooks to streamline the SDLC.
- Update hook strategy using current Claude Code best practices.
- Improve QA automation with reliable integration + E2E coverage.

## Scope

In scope:

- New SDLC role matrix covering requirements/design/implement/quality/release.
- Context engineering upgrades and subagent responsibilities.
- Documentation synchronization and crash recovery workflow.
- Hook recommendations and implementation plan (global + project).
- Recommendations for skills, plugins, tools, slash commands, MCP servers.
- QA automation strategy with smoke E2E on PR + full nightly suite.

Out of scope:

- Large UI/UX redesigns unrelated to SDLC automation.
- Removing PydanticAI dependencies (migration still in progress).
- Changing the core FastAPI/Next.js architecture.

## Requirements

### R1: UI/UX Roles in SDLC
- Add UI/UX roles in each SDLC phase.
- UI/UX roles must be empowered to propose and implement code changes.
- Include accessibility review checkpoints.

### R2: Context Engineering via Subagents
- Add a dedicated context-engineer subagent.
- Define context tiers (core, task, transient) and compaction rules.
- Ensure critical context survives compaction and session restarts.

### R3: Documentation Synchronization + Recovery
- Add a documentation-engineer subagent that runs in parallel.
- Ensure Conductor plan/spec/code/docs are kept in sync.
- Implement crash recovery strategy to restore last session state.

### R4: Hooks & Automation
- Propose and implement hooks based on current Claude Code guidance.
- Use both global (~/.claude/settings.json) and project-level hooks.
- Hooks must prioritize speed and determinism; avoid long-running tasks.

### R5: Skills/Plugins/Tools/Commands Discovery
- Research and recommend skills, plugins, MCP servers, and slash commands.
- Include modern agentic workflow patterns and best practices.

### R6: QA Automation Improvements
- Define smoke E2E suite for PR gating.
- Define full E2E suite for nightly execution.
- Ensure integration tests validate live system dependencies (no mocks).

### R7: Deep Research Enforcement
- Implement a Deep Research runner module and CLI entrypoint.
- Ensure `conductor-plan` auto-runs Deep Research for research tasks.
- Add a hook to block research outputs when no Deep Research artifact exists.

## Design Notes

### Deep Research Runner + Enforcement

- Module: `backend/app/agents/deep_research.py` wraps Agents SDK and writes
  `conductor/tracks/<id>/research.md` plus timestamped artifacts.
- CLI entrypoint: `project cmd deep-research --track-id <id> --query <text>` for
  manual runs, with `--output-format json` support and optional schema overrides.
- Planning integration: `conductor-plan` auto-runs deep research when task text
  includes research keywords, skipping if a digest already exists (unless forced).
- Enforcement hook: `require_deep_research.py` runs on `UserPromptSubmit` + `Stop`,
  checks active track(s) for research artifacts, and blocks when missing.

### Phase 2 Design Artifacts

- Parallel sweep (UI/UX): `artifacts/design/parallel-sweep/ui-ux/20260122T204407Z.md`
- Parallel sweep (Context): `artifacts/design/parallel-sweep/context-engineering/20260122T204407Z.md`
- Parallel sweep (Docs): `artifacts/design/parallel-sweep/documentation/20260122T204407Z.md`
- Parallel sweep (QA): `artifacts/design/parallel-sweep/qa-automation/20260122T204407Z.md`
- Parallel sweep synthesis: `artifacts/design/parallel-sweep/synthesis/20260122T204407Z.md`
- everything-claude-code parallel sweep (UI/UX): `artifacts/design/parallel-ecc/ui-ux/20260122T215158Z.md`
- everything-claude-code parallel sweep (Context): `artifacts/design/parallel-ecc/context-engineering/20260122T215158Z.md`
- everything-claude-code parallel sweep (Docs): `artifacts/design/parallel-ecc/documentation/20260122T215158Z.md`
- everything-claude-code parallel sweep (QA): `artifacts/design/parallel-ecc/qa-automation/20260122T215158Z.md`
- everything-claude-code parallel sweep synthesis: `artifacts/design/parallel-ecc/synthesis/20260122T215158Z.md`
- codex exec plans parallel sweep (UI/UX): `artifacts/design/parallel-codex-exec-plans/ui-ux/20260122T220401Z.md`
- codex exec plans parallel sweep (Context): `artifacts/design/parallel-codex-exec-plans/context-engineering/20260122T220401Z.md`
- codex exec plans parallel sweep (Docs): `artifacts/design/parallel-codex-exec-plans/documentation/20260122T220401Z.md`
- codex exec plans parallel sweep (QA): `artifacts/design/parallel-codex-exec-plans/qa-automation/20260122T220401Z.md`
- codex exec plans parallel sweep synthesis: `artifacts/design/parallel-codex-exec-plans/synthesis/20260122T220401Z.md`
- cloud subagents parallel sweep (Infra): `artifacts/design/parallel-cloud-agents/cloud-infra/20260122T222600Z.md`
- cloud subagents parallel sweep (Context): `artifacts/design/parallel-cloud-agents/context-engineering/20260122T222600Z.md`
- cloud subagents parallel sweep (Docs): `artifacts/design/parallel-cloud-agents/documentation/20260122T222600Z.md`
- cloud subagents parallel sweep (QA): `artifacts/design/parallel-cloud-agents/qa-automation/20260122T222600Z.md`
- cloud subagents parallel sweep synthesis: `artifacts/design/parallel-cloud-agents/synthesis/20260122T222600Z.md`
- Hook strategy: `artifacts/design/hook-strategy/20260122T204924Z.md`
- QA gates: `artifacts/design/qa-gates/20260122T204924Z.md`

- Role matrix: `artifacts/design/role-matrix/20260122T201657Z.md`
- Context engineering flow: `artifacts/design/context-engineering/20260122T201657Z.md`
- Documentation engineer workflow: `artifacts/design/documentation-engineer/20260122T201657Z.md`
- everything-claude-code review summary: `docs/everything-claude-code-review.md`
- cloud subagents workflow summary: `docs/cloud-agents.md`

## Parallel Roles (Target Matrix)

| Phase | Roles (Parallel) |
| --- | --- |
| requirements | product-lead, ux-researcher, context-engineer, qa-automation, documentation-engineer |
| design | ui-designer, interaction-designer, accessibility-specialist, systems-architect |
| implement | frontend-engineer, ux-engineer, backend-engineer, devex-automation |
| quality | qa-automation, ux-qa, a11y-auditor, test-engineer |
| release | documentation-engineer, release-manager, observability-analyst (sequential) |

## Skills To Use

- `parallel-agents`
- `context-window-management`
- `hook-development`
- `claude-automation-recommender`
- `e2e-testing-patterns`
- `python-testing-patterns`

## Acceptance Criteria

- New SDLC role matrix documented and approved in Conductor artifacts.
- Context engineering plan defines compaction + recovery behavior.
- Documentation-engineer parallel workflow defined with recovery steps.
- Hooks strategy documented and updated plan to implement.
- Skills/plugins/tools/commands recommendations captured.
- QA automation plan includes smoke PR gate + nightly full suite.
- Deep Research runner exists and research is blocked when artifacts are missing.
- Cloud subagent offload workflow documented with guardrails.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Excess automation slows inner loop | Medium | Keep hooks fast; run heavy tasks in nightly jobs. |
| Role sprawl without ownership | Medium | Assign clear outputs per role per phase. |
| Context bloat reduces agent quality | High | Tiered context + precompact summaries. |
| E2E flakiness blocks PRs | High | Smoke-only on PR + retries + stable selectors. |

## Open Questions

- Which exact UI/UX roles are required for each phase?
- Which hooks should be project-only vs global defaults?
- What E2E flows are required for smoke gating?
