# Plan: Agents SDK Orchestration Layer

## Phase 1: Requirements

- [x] Confirm integration test failures and scope. (pytest -m integration selected 0 tests; 437 deselected, exit code 5.)
- [x] Inventory current orchestration flow and touchpoints.
- [x] Define CLI interview flow inputs/outputs. (Conductor CLI command, not DB `spec-run`, owns `--output-format/--output-schema`.)
- [x] Run Deep Research API for planning evidence and best practices. (Artifacts captured under requirements/research-scientist.)
- [x] Run paired subagents to review recent cookbooks and record findings. (Artifacts captured for requirements roles.)
- [x] Use Deep Research to discover relevant skills; create missing skills. (No missing skills found.)

## Phase 2: Design

- [x] Define Agents SDK runner interface.
- [x] Define LiteLLM adapter usage for Anthropic.
- [x] Define Conductor artifact write/update contract.
- [x] Define confidence/vagueness gate logic.
- [x] Define per-role artifact schema and state capture.
- [x] Define structured output CLI argument and schema.
- [x] Support `--output-format json` and optional `--output-schema` overrides.

## Phase 3: Implement

- [x] Add Agents SDK runner layer.
- [x] Add CLI interview flow to generate spec/plan.
- [ ] Replace temporary plan usage with Conductor artifacts.
- [ ] Wire DB mirroring from Conductor artifacts.
- [ ] Persist Logfire/telemetry events in DB.

## Phase 4: Quality

- [ ] Run integration tests and fix failures.
- [ ] Validate Conductor plan updates during execution.
- [ ] Confirm CLI interview works end-to-end.

## Phase 5: Release (Sequential)

- [ ] Verify CI/CD readiness and canary checks.
- [ ] Update documentation artifacts.
