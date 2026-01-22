# Starting Prompt (Context-Driven Request)

## Role and Workflow

Use a Conductor-led, context-driven workflow with parallel orchestration:
Context -> Spec -> Plan -> Implement. Run research in parallel before planning.
Do not implement until a plan is approved. Use Ralph-style planning interviews
to eliminate vagueness.

## Research Sources (Required)

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

## Project Goal (Immediate)

Make integration tests pass. This is the top priority before new features.

## Project Goal (Ongoing)

Align guilde-lite-tdd-sprint with a Conductor-led, parallel SDLC workflow.
Conductor artifacts are canonical; the DB is a cache.

## Required Deliverables

1. Research Digest that summarizes the required workflow behaviors and gaps.
2. Fresh `conductor/` context artifacts (start clean, no reuse).
3. Track spec and plan for the integration-test fix.
4. Guardrails for tools/MCP actions (allowlist + approval rules).
5. Parallelization recommendation with pros/cons.
6. Agents SDK research and phase mapping (see `docs/agents-sdk-research.md`).

## Workflow Requirements

- Conductor files are canonical; DB mirrors them.
- Always read Conductor context before work.
- Use `conductor/tracks/<id>/spec.md` and `plan.md` as the plan of record.
- Update task status markers as work progresses.
- Apply acceptance-driven backpressure until vagueness is resolved.
- Require manual confirmation only when confidence is low or requirements are
  vague, and keep asking sprint interview questions until vagueness is gone.
- Use the Deep Research API during planning to gather evidence and best
  practices.
- During Deep Research, discover relevant Codex skills. Create missing skills
  before coding.

## Technical Stack (Current)

- Backend: FastAPI + Pydantic v2
- Database: PostgreSQL
- Auth: JWT
- Cache/Queue: Redis
- Frontend: Next.js 15

## Constraints

- Follow TDD and the workflow gates.
- No new features before integration tests pass.
- Use AskUserQuestionTool if supported by the UI; otherwise provide an adapter.

## Definition of Done

- Integration tests pass reliably.
- Conductor workflow is enforced in both agent behavior and repo code.
- Conductor artifacts are updated and used as the source of truth.
- Planning interview eliminates vague requirements before coding begins.
