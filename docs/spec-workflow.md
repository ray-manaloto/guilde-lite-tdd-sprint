# Spec Workflow (Port Plan)

Goal: mirror Auto-Claude's spec-driven workflow inside the FastAPI backend with a
simple, testable API that can grow into the full phase pipeline.

## Scope (Phase 1)

- Store specs in the database with task description, complexity, and phases.
- Provide an API to create and validate a spec draft.
- Provide a CLI entrypoint to run the spec workflow for local use.
- Keep the implementation deterministic (no mandatory LLM calls).

## Data Model

Spec:
- `id` (UUID)
- `user_id` (nullable)
- `title`
- `task`
- `complexity` (simple|standard|complex)
- `status` (draft|validated|approved|rejected)
- `phases` (list of phase names)
- `artifacts` (JSON for phase outputs, validation results)

## Complexity Assessment

Rules (initial heuristic):
- Simple: 1-2 files, no integrations.
- Standard: 3-10 files, 1-2 services, minimal integrations.
- Complex: 10+ files, multi-service, external integrations.

The assessment returns:
- complexity tier
- confidence score
- reasons/signals
- `phases` list derived from tier

## Phases (Initial)

- discovery
- requirements
- context
- spec
- planning
- validation

Note: phase list expands later to include research + critique.

## Planning Interview (Ralph Playbook)

For sprint prompts, we run a Ralph-style planning interview before moving into
implementation planning. The interview uses an AskUserQuestion-style tool to
collect clarifying questions (JTBD, edge cases, acceptance criteria).

Artifacts:
- `artifacts.assessment` stores complexity signals.
- `artifacts.planning` stores `{status, questions, answers, metadata}`.

### Dual-Subagent + Judge

When `DUAL_SUBAGENT_ENABLED=true`, the planning interview runs two agents and a
judge:

- OpenAI agent uses `OPENAI_MODEL`
- Anthropic agent uses `ANTHROPIC_MODEL`
- Judge uses `JUDGE_MODEL` (must start with `openai-responses:`)

The judge scores helpfulness and correctness, then selects the best candidate.
Selection is stored in `artifacts.planning.metadata.selected_candidate`.

### Telemetry

Planning metadata includes model names and Logfire trace IDs/URLs for the
agents and judge. The UI renders this data in the Sprint planning panel and the
Sprint Focus panel when a sprint is linked to the spec.

For Logfire links, configure `LOGFIRE_TRACE_URL_TEMPLATE` in `backend/.env` and
see `backend/docs/observability.md` for setup details.

## API (Phase 1)

- `GET /api/v1/specs` list specs (optional status filter)
- `POST /api/v1/specs` create spec draft
- `GET /api/v1/specs/{spec_id}` fetch spec
- `POST /api/v1/specs/{spec_id}/validate` validate spec
- `POST /api/v1/specs/planning` create spec draft + generate interview questions
- `POST /api/v1/specs/{spec_id}/planning/answers` store interview answers

## CLI

- `uv run --directory backend guilde_lite_tdd_sprint cmd spec-run --task "..."` to create a spec draft

## Tests

- Unit: complexity assessment
- API: create/fetch/validate spec
