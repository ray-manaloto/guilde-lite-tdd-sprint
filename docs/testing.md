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
  or reproducing UI bugs interactively. See:
  - https://github.com/vercel-labs/agent-browser
  - https://github.com/vercel-labs/agent-browser/blob/main/skills/agent-browser/SKILL.md
  - https://agent-browser.dev/
- **Codex skills**: Use local `skills/testing-automation` for repeatable validation workflow.
  References:
  - https://developers.openai.com/codex/skills/
  - https://developers.openai.com/codex/skills/create-skill/
  - https://github.com/openai/skills
  - https://agentskills.io/

## Test Coverage Expectations (Required)

- Every new feature must include automated tests.
- Backend: unit + API/integration coverage.
- Frontend: unit tests for helpers + Playwright for user flows.
- Add or update tests when behavior changes to avoid regressions.

## Validation Matrix (Required)

- **Auth**: register, login, invalid creds, required fields (Playwright).
- **Sprints**: create + list sprint, basic navigation (Playwright + integration).
- **Chat**: UI loads + connection state (Playwright); streaming only with `E2E_ALLOW_LLM=true`.
- **API**: health, auth, sprints, and chat endpoints (pytest integration).

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
