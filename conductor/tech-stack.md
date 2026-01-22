# Tech Stack

## Backend

- FastAPI
- Pydantic v2
- PostgreSQL (async)
- Redis
- JWT auth

## Tooling

- Python: uv, pytest, ruff, alembic

## AI/Agent Layer

- OpenAI Agents SDK (Python, native OpenAI models)
- LiteLLM (Python) adapter for Anthropic models only
- Dual-subagent planning (OpenAI + Anthropic) with judge
- Deep Research API (planning-stage research)

## Conductor Canonical Source

- `conductor/` files are the source of truth.
- Database mirrors Conductor artifacts.
