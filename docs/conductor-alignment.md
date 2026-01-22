# Conductor Workflow Alignment

This captures the current Conductor alignment review and the target workflow
so we do not lose decisions, gaps, or enforcement goals.

## Objectives

1. Make this Codex session follow the Conductor workflow.
2. Make the guilde-lite-tdd-sprint repo follow the same Conductor workflow.
3. Enforce that the operational workflow and the code implementation match.

## Sources Reviewed

- https://github.com/gemini-cli-extensions/conductor
- https://developers.googleblog.com/conductor-introducing-context-driven-development-for-gemini-cli/
- https://github.com/fcoury/conductor
- https://raw.githubusercontent.com/thanhtoan105/Accounting_ERP_Chatbot/main/.agents/skills/conductor/SKILL.md
- https://github.com/gotalab/cc-sdd
- https://github.com/existential-birds/amelia
- https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- https://www.anthropic.com/engineering/advanced-tool-use
- https://www.anthropic.com/engineering/code-execution-with-mcp
- https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- https://github.com/ClaytonFarr/ralph-playbook
- See `docs/agents-sdk-research.md` for Agents SDK research and phase mapping.

## Current State (Repo)

- Conductor context files exist in `conductor/`, but no local commands implement
  `/conductor:*` behavior. `conductor/` is currently documentation-only.
- The execution runner uses a transient `implementation_plan.md` and does not
  read or update `conductor/tracks/<id>/plan.md`.
- Parallelization only exists across subagents (provider runs), not across tasks.
- Ralph planning uses a custom tool, not a UI-driven AskUserQuestionTool.
- No hooks configured for guardrails or workflow enforcement.

## Gaps / Risks

- Conductor Context -> Spec -> Plan -> Implement is not the execution path.
- No track artifact enforcement (plan/spec status is not updated by the runner).
- No task dependency DAG or concurrent task execution within a sprint.
- No acceptance-driven backpressure or human approval gates per phase.
- No hook guardrails (tool allowlist, step checks, planning gates).

## Decisions Needed

- Canonical source of truth: Conductor files vs database?
- Parallelization target: intra-sprint task DAG vs multi-sprint planning lanes?
- AskUserQuestionTool: UI-driven tool or custom tool acceptable?
- MCP/tool policy: which tools are allowed and how are they gated?

## Enforcement Plan (Codex Session)

- Always read `conductor/product.md`, `conductor/tech-stack.md`,
  `conductor/workflow.md`, and `conductor/tracks.md` before work.
- When working on a track, read `conductor/tracks/<id>/spec.md` and
  `conductor/tracks/<id>/plan.md`.
- Do not implement before plan approval.
- Update plan task status markers during implementation.
- Require manual verification checkpoints at phase boundaries.

## Enforcement Plan (Repo)

- Implement conductor commands in-repo (setup/new-track/implement/status/revert).
- Make the runner read/update Conductor track artifacts, not a temp plan file.
- Store plan, phase, and task status in the Conductor plan file as canonical.
- Add hooks to enforce: plan approval before coding, tool allowlist, and
  verification checkpoints.
- Align Ralph planning with AskUserQuestionTool (or define a documented adapter).

## Parallelization Options

Option A: Intra-sprint DAG (parallel tasks in a single track)

Pros:
- Faster delivery for one feature.
- Shared context reduces drift.
- Single acceptance surface.

Cons:
- Higher orchestration complexity.
- More merge/test contention.
- Requires strong dependency modeling.

Option B: Parallel spec/planning across multiple sprints

Pros:
- High throughput in discovery.
- Keeps implementation focused.
- Better backlog prioritization.

Cons:
- Specs go stale if context shifts.
- More review overhead.
- More rework during implementation.

## AskUserQuestionTool Menu (Codex TUI Proposal)

```text
Planning interview tool:
1) AskUserQuestionTool (interactive, UI-driven)
2) Custom tool (collect questions; answers captured later)
3) Manual questions (user types list now)
4) Skip interview (not recommended)

Advanced options:
- Max questions [5]:
- Mode: single | dual-subagent
- Provider override:
```

Override path: allow flags (e.g. `--planning-tool`, `--max-questions`) and store
defaults in `conductor/setup_state.json` or `.claude/settings.json`.

## Next Steps (Proposed)

1. Decide the canonical source of truth (Conductor files vs DB).
2. Select a parallelization strategy.
3. Define the AskUserQuestionTool default and overrides.
4. Implement conductor commands + runner alignment with Conductor artifacts.
5. Add hooks for approval gates and tool guardrails.
