# Spec: Agents SDK Orchestration Layer

## Summary

Replace the current orchestration layer with OpenAI Agents SDK while preserving
Conductor as the canonical source of truth. OpenAI models run natively; Anthropic
models use LiteLLM only where needed.

## Objectives

- Keep Conductor files canonical; DB mirrors them.
- Implement a CLI-first workflow for sprint planning and execution.
- Support dual-subagent planning (OpenAI + Anthropic) with a judge.
- Preserve existing integration tests and fix any breakage.

## Scope

In scope:

- Agents SDK execution layer for planning and implementation.
- CLI interview flow to create/refresh Conductor spec + plan.
- Adapter layer that writes to `conductor/tracks/<id>/spec.md` and `plan.md`.

Out of scope:

- Replacing the web UI.
- Rewriting the FastAPI API surface.

## Requirements

- OpenAI models: use native Agents SDK.
- Anthropic models: use LiteLLM adapter only.
- Do not add new PydanticAI usage for orchestration/planning; keep existing
  dependencies in place until migration is complete.
- Preserve `.env` model identifiers.
- Planning interview must continue until vagueness is resolved.
- Manual confirmation required only when confidence is low.
- Use the Deep Research API during planning for evidence and best practices.
- Run paired subagents to research recent cookbooks (last 6 months) and capture
  findings in Conductor artifacts.
- CLI interface must support structured outputs via an argument.
- CLI must support both `--output-format json` and
  `--output-schema path/to/schema.json`.
- Deep Research must include skill discovery for relevant domains (python/pytest,
  OpenAI Agents SDK, LiteLLM). If a suitable skill does not exist, create one
  before implementation.
- Persist every artifact write and every Logfire/telemetry event to the DB.

## Skills To Use

- `python-testing-patterns`
- `uv-package-manager`
- `openai-agents-sdk`
- `litellm`

## Parallel Roles (Paired Subagents per Role)

| Phase | Agents (Parallel) |
| --- | --- |
| requirements | ceo-stakeholder, business-analyst, research-scientist |
| design | software-architect, data-scientist, network-engineer |
| implement | staff-engineer, senior-engineer, junior-engineer, devops-engineer |
| quality | qa-automation, code-reviewer, performance-engineer |
| release | cicd-engineer, canary-user, documentation-engineer (sequential) |

## Artifacts and Persistence

- Store each agent response as Markdown under:\n  `conductor/tracks/<id>/artifacts/<phase>/<role>/<timestamp>.md`
- Store per-agent state JSON alongside each response:\n  `conductor/tracks/<id>/artifacts/<phase>/<role>/<timestamp>.state.json`
- State must include:\n  context/token usage, context compactions, skills used, plugins used,\n  slash commands used, model used, tools used.
- Mirror all artifact writes and Logfire/telemetry events into the DB.

## Deep Research Trigger Policy

Use the Deep Research API during planning when any of the following apply:

- Required info is missing from Conductor context or subagent outputs.
- The plan cannot be produced without external evidence.
- Context compactions exceed a configurable threshold.

Default model: `o4-mini-deep-research` (configurable).

## Acceptance Criteria

- A CLI run can create or update a Conductor track with spec + plan.
- Agents SDK runner executes plan tasks and updates status markers.
- Integration tests pass reliably.
- Conductor artifacts remain the plan of record.

## Open Questions

- Which tasks should be parallelized in the first iteration?
- Where should the judge run (OpenAI only, or configurable)?
- What is the minimal CLI UX for interviews and confirmations?
