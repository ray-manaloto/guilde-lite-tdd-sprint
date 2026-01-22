# Conductor - Guilde Lite TDD Sprint

Navigation hub for Conductor context and workflow artifacts.

## Quick Links

| Document | Description |
|----------|-------------|
| [Product Definition](./product.md) | Project overview, goals, and constraints |
| [Product Guidelines](./product-guidelines.md) | Communication and UX guidelines |
| [Tech Stack](./tech-stack.md) | Technologies, versions, and tooling |
| [Workflow](./workflow.md) | Conductor workflow and quality gates |
| [Tracks](./tracks.md) | Track registry and status |
| [Tooling](./tooling.md) | Tool guardrails and approvals |
| [Evals](./evals.md) | Evaluation strategy and gates |

## Workflow Enforcement

Hard requirements for this repo:

- Treat `conductor/` files as canonical context for planning and execution.
- Read `conductor/product.md`, `conductor/tech-stack.md`, `conductor/workflow.md`,
  and `conductor/tracks.md` before work starts.
- Use `conductor/tracks/<id>/spec.md` and `conductor/tracks/<id>/plan.md` as the
  plan of record for active work.
- Do not implement before the plan is approved.
- Update plan task status markers as work proceeds.
- Require manual verification checkpoints at phase boundaries.
- If Conductor artifacts are missing or stale, stop and ask the user.

## Starting Point

Use `docs/starting-prompt.md` as the initial prompt for new sessions.
Use `docs/conductor-alignment.md` and `docs/agents-sdk-research.md` as reference
for workflow alignment and orchestration strategy.
