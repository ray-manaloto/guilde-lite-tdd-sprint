# Tech Stack

This project is built using the [full-stack-fastapi-nextjs-llm-template](https://github.com/vstorm-co/full-stack-fastapi-nextjs-llm-template) as its foundation.

## Backend
- **Language:** Python 3.12+
- **Framework:** FastAPI (Async)
- **Validation:** Pydantic v2
- **Database (Relational):** PostgreSQL (using `asyncpg` and SQLAlchemy 2.0)
- **Database (Key-Value/Cache):** Redis
- **Migrations:** Alembic
- **Background Tasks:** Celery
- **AI Agent Framework:** PydanticAI
- **LLM Providers:** OpenAI, Anthropic (via PydanticAI)
- **CLI:** Custom click-based CLI commands

## Frontend
- **Framework:** Next.js 15 (App Router)
- **Library:** React 19
- **Language:** TypeScript
- **Styling:** Tailwind CSS v4
- **State Management:** Zustand
- **Data Fetching:** TanStack Query (React Query)
- **Icons:** Lucide React

## Observability & Monitoring
- **Tracing & Logs:** Logfire (integrated with PydanticAI and FastAPI)
- **Metrics:** Prometheus (via `prometheus-fastapi-instrumentator`)
- **Error Tracking:** Sentry
- **Admin Panel:** SQLAdmin

## Infrastructure & DevOps
- **Containerization:** Docker & Docker Compose
- **Orchestration:** Kubernetes
- **Package Management:** `uv` (Backend), `bun` (Frontend)
- **CI/CD:** GitHub Actions

## Testing
- **Backend:** `pytest` with `pytest-asyncio` and `pytest-cov`
- **Frontend (Unit):** `vitest`
- **Frontend (E2E):** `playwright`
