# CLAUDE.md

## SDLC Workflow (MANDATORY)

This project uses **SDLC Orchestration** for all feature development. Before implementing any feature:

```bash
# Full feature workflow (parallel agents)
/sdlc-orchestration:full-feature "feature description"

# Or run specific phases
/sdlc-orchestration:phase requirements "feature description"
/sdlc-orchestration:phase design "feature description"
/sdlc-orchestration:phase implement "feature description"
/sdlc-orchestration:phase quality "feature description"
/sdlc-orchestration:phase release "feature description"

# Parallel research (3 agents)
/sdlc-orchestration:research "topic"

# Single role agent
/sdlc-orchestration:role <role> "task"
```

**Phase Gates (Enforced):**
- Requirements must complete before Design
- Design must complete before Implementation
- Quality (including code review) must pass before Release
- Backpressure: lint/type errors trigger warnings

See `conductor/workflow.md` for detailed workflow and `.claude/plugins/sdlc-orchestration/` for plugin docs.

---

## Project Overview

**guilde_lite_tdd_sprint** - FastAPI application generated with [Full-Stack FastAPI + Next.js Template](https://github.com/vstorm-co/full-stack-fastapi-nextjs-llm-template).

**Stack:** FastAPI + Pydantic v2, PostgreSQL (async), JWT auth, Redis, PydanticAI, Celery, Next.js 15

## Commands

```bash
# Backend
cd backend
uv run uvicorn app.main:app --reload --port 8000
uv run pytest
uv run ruff check . --fix && uv run ruff format .

# Database
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "Description"

# Frontend
cd frontend
bun dev
bun run test

# Docker
docker compose up -d
```

## Project Structure

```
backend/app/
├── api/routes/v1/    # HTTP endpoints
├── services/         # Business logic
├── repositories/     # Data access
├── schemas/          # Pydantic models
├── db/models/        # Database models
├── core/config.py    # Settings
├── agents/           # AI agents
└── commands/         # CLI commands
```

## Key Conventions

- Use `db.flush()` in repositories (not `commit`)
- Services raise domain exceptions (`NotFoundError`, `AlreadyExistsError`)
- Schemas: separate `Create`, `Update`, `Response` models
- Commands auto-discovered from `app/commands/`

## Where to Find More Info

Before starting complex tasks, read relevant docs:
- **Architecture details:** `docs/architecture.md`
- **Adding features:** `docs/adding_features.md`
- **Testing guide:** `docs/testing.md`
- **Code patterns:** `docs/patterns.md`

## Environment Variables

Key variables in `.env`:
```bash
ENVIRONMENT=local
POSTGRES_HOST=localhost
POSTGRES_PASSWORD=secret
SECRET_KEY=change-me-use-openssl-rand-hex-32
OPENAI_API_KEY=sk-...
LOGFIRE_TOKEN=your-token
```
