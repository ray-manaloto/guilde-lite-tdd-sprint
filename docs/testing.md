# Testing Guide

## Running Tests

```bash
cd backend

# Run unit + API + integration tests
uv run pytest

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=term-missing

# Run specific test file
uv run pytest tests/api/test_health.py -v

# Run specific test
uv run pytest tests/api/test_health.py::test_health_check -v

# Run only unit tests
uv run pytest tests/unit/

# Run only integration tests
uv run pytest tests/integration/

# Run with verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x
```

## Local Dev Services

Use the dev control script to start/stop backend API, agent web, and frontend
from one command:

```bash
./scripts/devctl.sh start
./scripts/devctl.sh status
./scripts/devctl.sh stop
```

If `tmux` is installed, the script runs services inside a tmux session
(default: `guilde-lite-dev`). Attach to a service window with:

```bash
./scripts/devctl.sh logs frontend
```

## Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── api/                 # API endpoint tests
│   ├── test_health.py
│   └── test_auth.py
├── unit/                # Unit tests (services, utils)
│   └── test_services.py
└── integration/         # Integration tests
    └── test_db.py
```

## Key Fixtures (`conftest.py`)

```python
# Database session for tests
@pytest.fixture
async def db_session():
    async with async_session() as session:
        yield session
        await session.rollback()

# Test client
@pytest.fixture
def client():
    return TestClient(app)

# Authenticated client
@pytest.fixture
async def auth_client(client, test_user):
    token = create_access_token(test_user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return client
```

## Writing Tests

### Integration Test (DB + service layer)
```python
async def test_create_item_integration(db_session):
    service = ItemService(db_session)
    item = await service.create(ItemCreate(name="Test"))
    assert item.id is not None
```

### API Endpoint Test
```python
def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

### Service Test
```python
async def test_create_item(db_session):
    service = ItemService(db_session)
    item = await service.create(ItemCreate(name="Test"))
    assert item.name == "Test"
```

### Test with Authentication
```python
def test_protected_endpoint(auth_client):
    response = auth_client.get("/api/v1/users/me")
    assert response.status_code == 200
```

## Playwright E2E Tests (Browser)

Playwright is configured in `frontend/playwright.config.ts` with `testDir=./e2e`.
The config starts the Next.js dev server automatically for local runs.

Recommended flow:
1. Start backend (required for auth + API tests).
2. Run Playwright from `frontend/`.

```bash
cd frontend

# Uses webServer in playwright config
bun run test:e2e

# Run in headed mode (see browser)
bun run test:e2e:headed
```

Chat streaming tests (PydanticAI WebSocket) are gated by an env flag to avoid
LLM calls during standard runs. Enable them when the backend is configured with
valid LLM credentials:

```bash
E2E_ALLOW_LLM=true bun run test:e2e
```

The sprint planning interview can also call LLMs. To stub those questions during
E2E runs, set the backend env var before starting the API:

```bash
PLANNING_INTERVIEW_MODE=stub uv run --directory backend uvicorn app.main:app --reload
```

### Logfire Validation (Sprint Telemetry)

The sprint planning telemetry panel has a Playwright validation that can query
Logfire and confirm the trace IDs resolve. Enable it only when you have valid
Logfire read access and want to validate telemetry links:

```bash
export PLAYWRIGHT_LOGFIRE_VALIDATION=true
export LOGFIRE_READ_TOKEN=...
export LOGFIRE_TRACE_URL_TEMPLATE="https://logfire.pydantic.dev/.../{trace_id}..."
export LOGFIRE_SERVICE_NAME=guilde_lite_tdd_sprint
```

The Playwright test will:
- Start a sprint planning interview (requires real LLM keys).
- Read the judge + subagent trace links from the UI.
- Query Logfire using the read token to validate the trace IDs exist.

If `LOGFIRE_TRACE_URL_TEMPLATE` is not set, the test will fall back to trace IDs
rendered in the telemetry panel (if available).

Example E2E test:
```ts
import { test, expect } from "@playwright/test";

test("register page loads", async ({ page }) => {
  await page.goto("/register");
  await expect(page.getByLabel(/email/i)).toBeVisible();
  await expect(
    page.getByRole("button", { name: /create account|sign up/i })
  ).toBeVisible();
});
```

If you want to point to a running frontend server instead of starting one:
```bash
PLAYWRIGHT_BASE_URL=http://localhost:3000 bun run test:e2e
```

## LLM Smoke Test (OpenAI SDK)

Use the OpenAI Python SDK directly to validate the configured OpenAI key/model
without PydanticAI. This mirrors the OpenAI agents SDK usage patterns.

```bash
cd backend
uv run python scripts/openai_sdk_smoke.py
```

Notes:
- Reads `OPENAI_API_KEY` and `OPENAI_MODEL` from repo `.env` if not set in the shell.
- `OPENAI_MODEL` must use `openai-responses:<model>`; the prefix is stripped for the SDK call.
- `openai:<model>` (chat) is intentionally unsupported in this repo.
- This script makes a paid API call.

### API Key Requirements (OpenAI + Anthropic)

- Use project-level keys with full model access for the providers you enable.
- OpenAI keys must allow Responses API usage for the configured models.
- Anthropic keys must allow Messages API usage for the configured models.

## LLM Smoke Test (Anthropic SDK)

Use the Anthropic Python SDK directly to validate the configured Anthropic key/model
without PydanticAI.

```bash
cd backend
uv run python scripts/anthropic_sdk_smoke.py
```

Notes:
- Reads `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` from repo `.env` if not set in the shell.
- If `ANTHROPIC_MODEL` starts with `anthropic:`, the prefix is stripped before the SDK call.
- This script makes a paid API call.

## PydanticAI OpenAI Models List

Use PydanticAI's OpenAI provider to list available models for the configured key.

```bash
cd backend
uv run python scripts/pydanticai_openai_models.py
```

Notes:
- Reads `OPENAI_API_KEY` and `OPENAI_BASE_URL` from repo `.env` if not set in the shell.
- Uses `pydantic_ai.providers.openai.OpenAIProvider` and its async client.

## OpenAI Model Permutation Test

Verify which OpenAI model string formats work across the OpenAI SDK and
PydanticAI model classes.

```bash
cd backend
uv run python scripts/openai_model_permutations.py
```

Notes:
- Reads `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_ORG` from repo `.env` if not set in the shell.
- Tests model variants: `gpt-5.2-codex`, `openai:gpt-5.2-codex`, `openai-responses:gpt-5.2-codex`.
- Uses OpenAI Responses API and PydanticAI Chat/Responses models.
- This script makes paid API calls.

### Latest Results (gpt-5.2-codex)

Working:
- OpenAI SDK Responses: `model="gpt-5.2-codex"`
- PydanticAI Responses model: `OpenAIResponsesModel("gpt-5.2-codex")`
- PydanticAI agent string: `Agent("openai-responses:gpt-5.2-codex")`

Not working:
- PydanticAI Chat model (`OpenAIChatModel`) with `gpt-5.2-codex` (not a chat model)
- Any OpenAI SDK model string with `openai:` or `openai-responses:` prefix

PydanticAI routing note:
- `Agent("openai-responses:<model>")` maps to `OpenAIResponsesModel` via `infer_model`.
- `Agent("openai:<model>")` maps to `OpenAIChatModel` (not supported here).

## Skills & Browser Automation Helpers

- **agent-browser**: CLI-driven browser automation that can complement Playwright for smoke checks
  or reproducing UI bugs interactively. The backend agent exposes this tool by default and
  allows all URLs (no allowlist). See:
  - https://github.com/vercel-labs/agent-browser
  - https://github.com/vercel-labs/agent-browser/blob/main/skills/agent-browser/SKILL.md
  - https://agent-browser.dev/
  Config:
  - `AGENT_BROWSER_ENABLED=true|false`
  - `AGENT_BROWSER_TIMEOUT_SECONDS=60`
- **http-fetch**: Direct HTTP fetch tool for link access when a browser tool is unavailable.
  The agent can call this to retrieve page text (allow-all URLs, no allowlist). Config:
  - `HTTP_FETCH_ENABLED=true|false`
  - `HTTP_FETCH_TIMEOUT_SECONDS=15`
  - `HTTP_FETCH_MAX_CHARS=12000`
- **Codex skills**: Use local `skills/testing-automation` for repeatable validation workflow.
  References:
  - https://developers.openai.com/codex/skills/
  - https://developers.openai.com/codex/skills/create-skill/
  - https://github.com/openai/skills
  - https://agentskills.io/
- **AI Research Skills marketplace**: install + validate with:
  - `scripts/install-ai-research-skills.sh`
  - `scripts/validate-ai-research-skills.sh`

## Test Coverage Expectations (Required)

- Every new feature must include automated tests.
- Backend: unit + API/integration coverage.
- Frontend: unit tests for helpers + Playwright for user flows.
- Add or update tests when behavior changes to avoid regressions.
- Agent routing: verify dual-subagent + judge flow and persisted decisions.

## Validation Matrix (Required)

- **Auth**: register, login, invalid creds, required fields (Playwright).
- **Sprints**: create + list sprint, basic navigation (Playwright + integration).
- **Chat**: UI loads + connection state (Playwright); streaming only with `E2E_ALLOW_LLM=true`.
- **API**: health, auth, sprints, and chat endpoints (pytest integration).
- **Agents**: OpenAI + Anthropic subagents run per prompt, judge chooses, decision stored.
  Requires `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `JUDGE_MODEL`, and
  `DUAL_SUBAGENT_ENABLED=true` in `.env`.
  Validate checkpoints include input history and decision metadata for the chosen model.

## Frontend Tests

```bash
cd frontend

# Run unit tests
bun run test

# Run with watch mode
bun run test

# Run unit tests once
bun run test:run

# Run E2E tests
bun run test:e2e

# Run E2E in headed mode (see browser)
bun run test:e2e:headed
```

## Test Database

Tests use a separate test database or SQLite in-memory:
- Configuration in `tests/conftest.py`
- Database is reset between tests
- Use fixtures for test data
