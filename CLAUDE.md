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

## Autonomous Operation Rules

This project enforces autonomous SDLC workflow. Claude operates without consultation for routine tasks.

### Auto-Approved (No Confirmation)
- Read, search, explore operations (Read, Glob, Grep)
- Quality checks (pytest, ruff, mypy, bandit)
- Git read operations (status, diff, log, branch, show)
- Health checks (curl to localhost)
- DevCtl status commands

### Confirm Once Per Session
- File modifications (Write, Edit)
- Git write operations (add, commit, push)
- Creating PRs and issues

### Always Require Confirmation
- `.env` file modifications (secrets)
- Destructive git operations (force push, reset --hard)
- Database migrations
- Service restarts
- Production deployments

### Consultation Triggers
Only consult user for:
1. Config changes requiring secrets
2. Service restarts requiring system access
3. Critical architectural decisions
4. Ambiguous requirements

---

## Claude Code CLI Health Check

This project includes automated health checks for the Claude Code CLI setup.

### Health Check
```bash
./.claude/scripts/health-check.sh
```
Validates:
- `.claude/settings.json` exists and is valid JSON
- All skill scripts have execute permissions
- Hooks files are valid JSON
- Required environment variables are set
- CLAUDE.md exists

### Self-Healing
```bash
./.claude/scripts/self-heal-cli.sh
```
Automatically fixes:
- Missing execute permissions on scripts
- Missing `.claude` directory structure
- Missing or corrupted `settings.json`

### SessionStart Hook
Health check runs automatically on session start. If issues are found, self-heal is suggested.

---

## Project Overview

**guilde_lite_tdd_sprint** - FastAPI application generated with [Full-Stack FastAPI + Next.js Template](https://github.com/vstorm-co/full-stack-fastapi-nextjs-llm-template).

**Stack:** FastAPI + Pydantic v2, PostgreSQL (async), JWT auth, Redis, PydanticAI, Celery, Next.js 15

## Commands

### Development Workflow (devctl.sh)

Use `devctl.sh` for **local development** - it orchestrates all services:

```bash
# Start all services (backend, agent-web, frontend)
./scripts/devctl.sh start

# Check status
./scripts/devctl.sh status

# Tail logs
./scripts/devctl.sh logs backend

# Stop all services
./scripts/devctl.sh stop

# Start infrastructure (PostgreSQL, Redis)
./scripts/devctl.sh infra up

# Preflight health checks
./scripts/devctl.sh preflight --verbose
```

### Makefile (CI/CD & One-off Operations)

Use `make` for **individual operations**:

```bash
# Setup
make install          # Install deps + pre-commit hooks

# Code quality
make lint             # Check code quality
make format           # Auto-format code
make test             # Run tests

# Database
make db-upgrade       # Apply migrations
make db-migrate       # Create new migration
make docker-db        # Start PostgreSQL only

# Docker
make docker-up        # Start all backend services
make docker-down      # Stop all services

# Celery
make celery-worker    # Start worker
make celery-beat      # Start beat scheduler
```

### When to Use Which

| Task | Tool |
|------|------|
| Local development (all services) | `./scripts/devctl.sh start` |
| CI/CD pipelines | `make test`, `make lint` |
| Database migrations | `make db-upgrade` |
| Quick backend-only run | `make run` |
| Production Docker | `make docker-prod` |
| Check service status | `./scripts/devctl.sh status` |
| tmux session workflow | `./scripts/devctl.sh start` (auto-detects) |

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

---

## Observability & Diagnostics

### Current Stack
- **Logfire:** Traces, spans, PydanticAI instrumentation
- **Sentry:** Error tracking (basic init)
- **Prometheus:** Metrics at `/metrics`

### Diagnostic Schemas (NEW - 2026-01-22)
Located at `backend/app/schemas/diagnostic.py`:
- `ErrorEventCreate/Read` - Structured error capture
- `ErrorCategory` - 19 categories for AI classification
- `ErrorPattern` - Recurring issue detection
- `LogfireErrorEnrichment` - Span enrichment helper

### Error Boundaries (Frontend)
- `frontend/src/app/[locale]/(dashboard)/error.tsx` - Dashboard-wide
- `frontend/src/app/[locale]/(dashboard)/sprints/error.tsx` - Sprint-specific

### ADRs (Architecture Decisions)
- `docs/design/ADR-001-pagination-pattern.md` - Query-based pagination
- `docs/design/ADR-001-pagination-fix-implementation.md` - Pagination fix details
- `docs/design/ADR-002-self-diagnostic-architecture.md` - Self-healing design
- `docs/design/ADR-002-autonomous-hooks-architecture.md` - Autonomous hooks
- `docs/design/ADR-002-sdlc-uiux-roles-hooks-qa.md` - UI/UX roles and QA
- `docs/design/ADR-git-worktree-isolation.md` - Sprint isolation
- `docs/design/ADR-deepagents-framework-evaluation.md` - DeepAgents evaluation

---

## Self-Healing System

Automated error detection and fix generation.

### Status Endpoint
```bash
curl http://localhost:8000/api/v1/self-heal/status
```

### Trigger Manual Fix
```bash
curl -X POST http://localhost:8000/api/v1/self-heal/trigger \
  -H "Content-Type: application/json" \
  -d '{"error_type": "...", "error_message": "...", "confidence_score": 0.8}'
```

### GitHub Workflow
- File: `.github/workflows/ai-self-heal.yml`
- Triggers: `repository_dispatch`, issue labeled `ai-fix`
- Action: Creates PR with automated fix

### Roadmap

Research completed 2026-01-22. See `docs/design/ADR-002-self-diagnostic-architecture.md`.

| Component | Status | Priority |
|-----------|--------|----------|
| Enhanced Logfire spans | Pending | P1 |
| Sentry user context | Pending | P1 |
| Circuit breakers (aiobreaker) | Pending | P2 |
| dev3000 integration | Pending | P2 |
| healing-agent (auto-fix) | Pending | P3 |
| Unleash feature flags | Pending | P3 |

### Recommended Tools
- **dev3000** (https://github.com/vercel-labs/dev3000) - AI debugging
- **healing-agent** (https://github.com/matebenyovszky/healing-agent) - Auto-fix
- **web-interface-guidelines** (https://github.com/vercel-labs/web-interface-guidelines) - UX

---

## SDLC Roles

23 agents available. Use `/sdlc-orchestration:role <role> "task"`:

| Role | Use For |
|------|---------|
| `debugger` | Root cause analysis, bug investigation (NEW) |
| `qa-automation` | Test creation, coverage |
| `code-reviewer` | Code quality review |
| `staff-engineer` | Core architecture |
| `senior-engineer` | Feature implementation |

Full list: `.claude/plugins/sdlc-orchestration/README.md`

---

## Known Issues & Fixes

### Workspace Initialization (Fixed 2026-01-22)

**Issue:** Sprint execution failed with "Session directory not initialized" errors during filesystem operations.

**Root Cause:** `AgentTddService._run_subagent()` set `deps.session_dir` to the workspace path but never created the directory. The filesystem tools then failed when validating paths.

**Fix:** Added `session_path.mkdir(parents=True, exist_ok=True)` in `backend/app/services/agent_tdd.py` before setting `deps.session_dir`.

**Commit:** `ad35992`
