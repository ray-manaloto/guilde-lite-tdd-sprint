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

## API (Phase 1)

- `GET /api/v1/specs` list specs (optional status filter)
- `POST /api/v1/specs` create spec draft
- `GET /api/v1/specs/{spec_id}` fetch spec
- `POST /api/v1/specs/{spec_id}/validate` validate spec

## CLI

- `uv run --directory backend guilde_lite_tdd_sprint cmd spec-run --task "..."` to create a spec draft

## Tests

- Unit: complexity assessment
- API: create/fetch/validate spec
