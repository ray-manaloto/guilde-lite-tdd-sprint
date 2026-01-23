# Plan: Agentic SDLC Enhancements

Track ID: `agentic_sdlc_enhancements_20260122`
Created: 2026-01-22
Status: approved

## Overview

Research modern parallel agentic SDLC practices, define role matrix additions
(UI/UX + documentation + context engineering), then implement hooks, commands,
and QA automation gates with Conductor artifacts as the plan of record.

## Phase 1: Requirements

### Tasks

- [x] **Task 1.1**: Run parallel research across Claude Code docs and cookbooks.
- [x] **Task 1.2**: Capture requirements artifacts for UI/UX, context, QA, docs.
- [x] **Task 1.3**: Summarize role additions and best practices in research.md.
- [x] **Task 1.4**: Identify skills/plugins/tools/commands to streamline SDLC.

### Verification

- [x] **Verify 1.1**: Requirements artifacts stored under `artifacts/requirements/*`.

## Phase 2: Design

### Tasks

- [x] **Task 2.1**: Define SDLC role matrix with phase responsibilities. `artifacts/design/role-matrix/20260122T201657Z.md`
- [x] **Task 2.2**: Design context-engineering flow (tiers, compaction, recovery). `artifacts/design/context-engineering/20260122T201657Z.md`
- [x] **Task 2.3**: Design documentation-engineer workflow and sync rules. `artifacts/design/documentation-engineer/20260122T201657Z.md`
- [x] **Task 2.4**: Design hook strategy (global + project) and command set. `artifacts/design/hook-strategy/20260122T204924Z.md`
- [x] **Task 2.5**: Define QA automation gates (TUI-only smoke/nightly + manual frontend E2E). `artifacts/design/qa-gates/20260122T204924Z.md`
- [x] **Task 2.6**: Design Deep Research runner + enforcement rules.
- [x] **Task 2.7**: Run parallel role sweep (UI/UX, context, docs, QA) via Agents SDK. `artifacts/design/parallel-sweep/`
- [x] **Task 2.8**: Synthesize parallel sweep outputs into Phase 2 design summary. `artifacts/design/parallel-sweep/synthesis/20260122T204407Z.md`
- [x] **Task 2.9**: Run parallel sweep against everything-claude-code (UI/UX, context, docs, QA). `artifacts/design/parallel-ecc/`
- [x] **Task 2.10**: Document everything-claude-code adoption guidance. `docs/everything-claude-code-review.md`
- [x] **Task 2.11**: Run parallel sweep against codex exec plans guidance. `artifacts/design/parallel-codex-exec-plans/`
- [x] **Task 2.12**: Incorporate codex exec plans guidance into workflow docs. `conductor/workflow.md`
- [x] **Task 2.13**: Run deep research on cloud subagent offload workflow. `artifacts/research/20260122T222513Z.md`
- [x] **Task 2.14**: Run parallel sweep for cloud subagent workflow (infra, context, docs, QA). `artifacts/design/parallel-cloud-agents/`
- [x] **Task 2.15**: Document cloud subagent workflow summary. `docs/cloud-agents.md`

### Verification

- [x] **Verify 2.1**: Design decisions recorded in spec + plan.

## Phase 3: Implement

### Tasks

- [x] **Task 3.1**: Add/adjust hook configs and scripts (per design).
- [x] **Task 3.2**: Add slash commands for role workflows and QA gates. `backend/app/commands/qa.py`, `backend/app/commands/codex_guard.py`
- [x] **Task 3.3**: Implement doc-sync + state recovery automation. `backend/app/commands/sync_docs.py`, `backend/app/commands/snapshot_state.py`
- [x] **Task 3.4**: Add/retag E2E smoke tests and nightly suite config. `frontend/e2e/smoke.spec.ts`, `backend/tests/integration/test_tools_live.py`
- [x] **Task 3.5**: Implement Deep Research runner and enforcement hook.

### Verification

- [ ] **Verify 3.1**: Hooks execute as expected on sample actions.
- [ ] **Verify 3.2**: Frontend E2E smoke runs when explicitly invoked (manual/optional).

## Phase 4: Quality

### Tasks

- [ ] **Task 4.1**: Run integration tests; optionally run frontend E2E smoke.
- [ ] **Task 4.2**: Validate docs/plan/code synchronization.

### Verification

- [ ] **Verify 4.1**: QA gates pass; no new regressions.

## Phase 5: Release (Sequential)

### Tasks

- [ ] **Task 5.1**: Update Conductor workflow documentation.
- [ ] **Task 5.2**: Update tracks registry + metadata.

### Verification

- [ ] **Verify 5.1**: Acceptance criteria met and approved.

## Checkpoints

| Phase | Checkpoint SHA | Date | Status |
| --- | --- | --- | --- |
| Phase 1 |  |  | pending |
| Phase 2 |  |  | pending |
| Phase 3 |  |  | pending |
| Phase 4 |  |  | pending |
| Phase 5 |  |  | pending |
