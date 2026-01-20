# Sprints

Sprint planning and execution tracking is handled by a dedicated API and a Sprint board in the
Next.js dashboard.

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
