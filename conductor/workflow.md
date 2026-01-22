# Workflow

## Conductor Loop

Context -> Spec -> Plan -> Implement -> Verify -> Update Context

- Context establishes constraints and standards.
- Spec defines requirements and acceptance criteria.
- Plan decomposes work into phases and tasks (with dependencies).
- Implementation follows TDD with task status updates.
- Verification includes manual checkpoints at phase boundaries.
- Context artifacts are updated after completion.

## Canonical Artifacts

- Conductor files are canonical; DB mirrors them.
- Do not implement before plan approval.
- Use `conductor/tracks/<id>/spec.md` and `plan.md` as the plan of record.

## Ralph Planning Interview

- Use a planning interview to remove vagueness before coding.
- If requirements are vague, keep asking until clarity is achieved.
- Manual confirmation is required only when confidence is low.

## Planning Research

- Use the OpenAI Deep Research API during planning to gather evidence and
  best practices for the track.
- Prefer the Deep Research API for multi-step synthesis and tool-based research.
- During Deep Research, search for relevant Codex skills to streamline
  implementation. If no suitable skill exists, create one based on research
  findings before coding.
- CLI: `project cmd deep-research --track-id <id> --query <text>` writes
  `conductor/tracks/<id>/research.md` plus timestamped artifacts.
- `conductor-plan` auto-runs Deep Research when the task includes research
  keywords, unless a digest already exists.
- Set `CONDUCTOR_TRACK_ID` to pin hook enforcement to a specific active track.

## ExecPlan Alignment (Multi-hour Work)

For complex, multi-hour tasks (cross-cutting changes, refactors, high-risk work),
use the `plan.md` as an ExecPlan-style document while keeping Conductor canonical.

- Keep `spec.md` as the requirements source of truth.
- Make `plan.md` self-contained for execution: include exact commands, expected
  outputs, and verification steps. Capture evidence expectations.
- Add living sections to `plan.md` when needed:
  - Progress (checkboxes with timestamps)
  - Surprises & Discoveries
  - Decision Log
  - Outcomes & Retrospective
- Avoid creating a separate ExecPlan file to prevent drift.

## Cloud Subagents (AWS Offload)

Cloud-hosted subagents can offload heavy or risky work while preserving
Conductor artifacts as canonical.

- Subagents return **unified diffs only**; no direct repo writes.
- Use minimal context bundles with explicit objectives and constraints.
- Apply patches via a validated pipeline (lint/test gates).
- Orchestrate via event-driven workflows (EventBridge + Step Functions + SQS).
- Enforce isolation: private subnets, least-privilege IAM, Secrets Manager.
- Observability: CloudWatch + X-Ray/OTel, token and runtime metrics.
- Cost guardrails: budgets, anomaly detection, concurrency caps.

## Confidence Gate

Low confidence triggers manual confirmation when any of the following are true:

- Acceptance criteria are missing or ambiguous.
- Critical dependencies are unknown.
- The plan cannot map to testable outcomes.

## Parallelization

- Plans should capture a task DAG with explicit dependencies.
- Independent tasks may run in parallel, bounded by concurrency limits.
- Do not parallelize tasks that share the same files or tests without explicit
  coordination.

## TDD Policy

- Red: write failing test(s).
- Green: minimal implementation to pass.
- Refactor: improve while tests stay green.

## Verification Checkpoints

- At the end of each phase, run relevant tests and confirm results.
- If confidence is low, require explicit user confirmation to proceed.
- Integration gate: `cd backend && uv run pytest -m integration`
- Integration tests must not use mocks or patch fixtures.
