# Sprints

Sprint planning and execution tracking is handled by a dedicated API and a Sprint board in the
Next.js dashboard.

## End-to-End Workflow (Idea → Sprint)

1. Enter a sprint prompt in the Sprint planning interview.
   - Expectation: prompt describes the outcome you want by the end of the sprint.
   - System action: starts the Ralph planning interview and generates clarifying questions.

2. Review the generated questions and provide answers.
   - Expectation: all questions must be answered before the sprint can be created.
   - System action: stores answers in the linked spec (`artifacts.planning.answers`).

3. Create the sprint after answers are saved.
   - Expectation: sprint name is required; goal is recommended.
   - System action: sprint is created with `spec_id` pointing to the planning spec.

4. Track the sprint in the board and add items.
   - Expectation: sprint focus shows status, dates, items, and planning telemetry.
   - System action: items are added to the sprint and move through status columns.

## Planning Interview Expectations

- The planning interview runs before sprint creation and must succeed.
- The interview produces 1-10 questions (default 5).
- Answers are validated for non-empty input.
- If the interview fails to produce questions, sprint creation is blocked.

## Model-as-Judge (Dual-Subagent Planning)

By default, planning uses a dual-subagent workflow:

- **OpenAI agent** uses `OPENAI_MODEL`
- **Anthropic agent** uses `ANTHROPIC_MODEL`
- **Judge** uses `JUDGE_MODEL` (must be an OpenAI responses model)

The judge scores helpfulness + correctness and selects the best candidate. The
selected provider is stored in `artifacts.planning.metadata.selected_candidate`
and shown in the UI.

Configuration:

- `DUAL_SUBAGENT_ENABLED=true` (default)
- `OPENAI_MODEL=openai-responses:gpt-5.2-codex` (example)
- `DEEP_RESEARCH_MODEL=o3-deep-research` (optional)
- `ANTHROPIC_MODEL=anthropic:claude-opus-4-5-20251101` (example)
- `JUDGE_MODEL=openai-responses:gpt-5.2-codex` (required in dual-subagent mode)

## Telemetry and Logfire

Planning telemetry is recorded in `artifacts.planning.metadata` and displayed in
two places:

- Sprint planning interview panel (current interview)
- Sprint Focus panel (persisted sprint history, from the linked spec)

Metadata includes:

- `candidates` with `provider`, `model_name`, `trace_id`, and `trace_url`
- `judge` with `model_name`, `trace_id`, `trace_url`, and scoring rationale
- `selected_candidate` with the chosen provider/model

To enable clickable Logfire links in the UI:

- Set `LOGFIRE_TRACE_URL_TEMPLATE` in `backend/.env` with `{trace_id}` placeholder.
- The backend emits `trace_url` when the template is set.

Logfire setup details are in `backend/docs/observability.md`.

## Status Values

- Sprint status: `planned`, `active`, `completed`
- Sprint item status: `todo`, `in_progress`, `blocked`, `done`
- Priority: `1` (high), `2` (medium), `3` (low)
- Optional `spec_id` links a sprint to its planning interview/spec.

## API Endpoints

Sprints:
- `GET /api/v1/sprints` (optional `status` query param)
- `POST /api/v1/sprints`
- `GET /api/v1/sprints/{sprint_id}`
- `PATCH /api/v1/sprints/{sprint_id}`
- `DELETE /api/v1/sprints/{sprint_id}`

Sprint items:
- `GET /api/v1/sprints/{sprint_id}/items`
- `POST /api/v1/sprints/{sprint_id}/items`
- `PATCH /api/v1/sprints/{sprint_id}/items/{item_id}`
- `DELETE /api/v1/sprints/{sprint_id}/items/{item_id}`

## Planning Interview

Sprint prompts should run through the Ralph planning interview before creating
the sprint. Use the spec planning endpoints to generate questions and capture
answers, then attach the resulting `spec_id` when creating the sprint.

## UI

- Sprint board: `frontend/src/app/[locale]/(dashboard)/sprints/page.tsx`
- Kanban placeholder (optional): `frontend/src/app/[locale]/(dashboard)/kanban/page.tsx`
