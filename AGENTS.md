# AGENTS.md

This file provides guidance for AI coding agents (Codex, Copilot, Cursor, Zed, OpenCode).

## Project Overview

**guilde_lite_tdd_sprint** - FastAPI application.

**Stack:** FastAPI + Pydantic v2, PostgreSQL, JWT auth, Redis, Next.js 15

## Commands

```bash
# Run server
cd backend && uv run uvicorn app.main:app --reload

# Tests & lint
uv run pytest
uv run ruff check . --fix && uv run ruff format .

# Migrations
uv run alembic upgrade head
```

## Project Structure

```
backend/app/
├── api/routes/v1/    # Endpoints
├── services/         # Business logic
├── repositories/     # Data access
├── schemas/          # Pydantic models
├── db/models/        # DB models
└── commands/         # CLI commands
```

## Key Conventions

- `db.flush()` in repositories, not `commit()`
- Services raise `NotFoundError`, `AlreadyExistsError`
- Separate `Create`, `Update`, `Response` schemas

## Conductor Workflow (Hard Requirements)

- Treat `conductor/` files as canonical context for planning and execution.
- Read `conductor/product.md`, `conductor/tech-stack.md`, `conductor/workflow.md`,
  and `conductor/tracks.md` before work starts.
- For active work, use `conductor/tracks/<id>/spec.md` and
  `conductor/tracks/<id>/plan.md` as the plan of record.
- Do not implement before the plan is approved.
- Update plan task status markers as work proceeds.
- Require manual verification checkpoints at phase boundaries.
- If required Conductor artifacts are missing or stale, stop and ask the user.
- See `docs/conductor-alignment.md` for alignment details and decisions.

## More Info

- `docs/architecture.md` - Architecture details
- `docs/adding_features.md` - How to add features
- `docs/testing.md` - Testing guide
- `docs/patterns.md` - Code patterns
