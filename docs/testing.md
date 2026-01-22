
# Testing Guide

## Agent CLI Integration Testing

The application integrates with external AI CLI tools (`claude` and `codex`). Testing this integration involves two strategies:

### 1. Mocked Testing (Docker/CI)
In Docker environments (like CI or standard `docker-compose up`), the CLIs are not installed. We use a mocking strategy:
- **Environment Variable:** `MOCK_AGENT_CLI=true`
- **Behavior:** The backend intercepts `claude` and `codex` calls and returns fixed mock responses (e.g., `"Mock Claude Output: <prompt>"`).
- **Usage:** This is the default in `docker-compose.yml` and is used for standard E2E tests.

### 2. Live Verification (Local Host)
To verify the *actual* integration with installed CLIs:
- **Prerequisite:** Ensure `claude` and `codex` are installed and authenticated on your host machine.
- **Run Backend Locally:** `make run` (runs on host, access to host binaries).
- **Run Live Integration Tests:**
  ```bash
  RUN_LIVE_TESTS=1 uv run --directory backend pytest tests/integration/test_tools_live.py
  ```
- **Run E2E Tests Locally:**
  ```bash
  # Ensure backend is running locally on port 8000
  cd frontend
  npx playwright test e2e/cli-agent.spec.ts
  npx playwright test e2e/codex-agent.spec.ts
  ```

---


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
- Assert the judge + subagent models match `OPENAI_MODEL`, `ANTHROPIC_MODEL`, and `JUDGE_MODEL`.
- Read the judge + subagent trace links from the UI.
- Save answers and create a sprint (full workflow).
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

## Sprint Interview-to-Code Integration Test

### Overview

The sprint interview-to-code integration test (`test_sprint_interview_to_code.py`) validates the complete workflow from planning interview through code generation and execution. This is a P0 priority integration test that exercises the full sprint lifecycle with dual-provider AI execution.

### Workflow Tested

```
Planning Interview --> Spec Generation --> Sprint Creation --> PhaseRunner Execution --> Code Validation
        |                    |                   |                     |                      |
   AI Questions        Store Q&A         Link Spec to         Discovery/Coding/       Execute & Verify
   (dual-provider)     Artifacts          Sprint             Verification Loop         Artifacts
```

### Test Structure

The test file contains four main test groups:

#### Phase 1: Planning Interview Tests

**Purpose:** Validate that AI generates clarifying questions dynamically

Tests in this group:
- `test_planning_interview_generates_questions`: Verifies questions are generated and metadata is structured correctly
- `test_spec_create_with_planning_stores_metadata`: Confirms planning results are stored in the spec artifacts

Key validations:
- Questions list is populated
- Metadata includes `mode`, `question_count`, and provider information
- Dual-provider metadata (when enabled) includes candidates and judge info

#### Phase 2: Dual-Provider Execution Tests

**Purpose:** Confirm OpenAI and Anthropic models both run and judge selection works

Tests in this group:
- `test_dual_provider_candidates_created`: Verifies both providers generate candidates with model names and metrics
- `test_judge_selection_stores_metadata`: Confirms judge selects a winning candidate and stores rationale

Key validations:
- Both OpenAI and Anthropic candidates are created
- Each candidate has `provider`, `model_name`, and `duration_ms` metrics
- Judge decision includes model name and candidate ID reference

#### Phase 3: Checkpointing Tests

**Purpose:** Ensure execution states are captured at key lifecycle points

Tests in this group:
- `test_checkpoints_track_execution_labels`: Verifies checkpoint labels (start, candidate:*, decision) exist
- `test_checkpoint_state_contains_metadata`: Confirms checkpoint state includes input payload and metadata

Key validations:
- Start checkpoint exists with `input_payload` field
- Candidate checkpoints created for each provider
- Decision checkpoint created when judge runs
- Checkpoints maintain sequential order

#### Phase 4: Full Workflow Integration Test

**Purpose:** Run the complete end-to-end flow and generate executable code

Tests in this group:
- `test_full_sprint_interview_to_code_workflow`: Complete workflow from interview to code execution
- `test_agent_tdd_service_sprint_agent_type`: Verify SprintAgent uses filesystem tools
- `test_sprint_workflow_database_schema_fields`: Validate database schema has required fields
- `test_sprint_agent_uses_filesystem_tools`: Confirm filesystem tools are registered
- `test_phase_runner_workspace_persistence`: Verify workspace_ref persists across phases

Key validations:
- Spec created with planning interview
- Sprint created and linked to spec
- PhaseRunner executes all phases
- Code file (hello.py) generated and executable
- Output matches expected "hello world" message

### Prerequisites

Before running the integration tests, ensure:

#### Environment Variables

```bash
# Required for all tests
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Configuration
DUAL_SUBAGENT_ENABLED=true        # Enable dual-provider execution
OPENAI_MODEL=gpt-4o or similar
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022 or similar
JUDGE_MODEL=gpt-4o or similar

# Filesystem artifacts
AUTOCODE_ARTIFACTS_DIR=/path/to/artifacts  # Temp directory for generated files

# Optional: For faster local testing
PLANNING_INTERVIEW_MODE=live       # Use real AI (not "stub")
AGENT_FS_ENABLED=true             # Enable filesystem tools
```

#### API Key Requirements

- **OpenAI keys**: Must have access to Responses API for the configured model
- **Anthropic keys**: Must have access to Messages API for the configured model
- Keys can be project-level or account-level; project keys are recommended for isolation

#### Database

- PostgreSQL must be running and accessible
- Database is configured in `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`
- Test session automatically rolls back transactions for isolation

### Running the Tests

#### Run All Integration Tests

```bash
cd backend
uv run pytest tests/integration/test_sprint_interview_to_code.py -v
```

#### Run Specific Test Group

```bash
# Planning interview tests
uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_planning_interview_generates_questions -v

# Dual-provider tests
uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_dual_provider_candidates_created -v

# Full workflow
uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_full_sprint_interview_to_code_workflow -v

# Standalone tests
uv run pytest tests/integration/test_sprint_interview_to_code.py::test_sprint_workflow_database_schema_fields -v
```

#### Run with Verbose Output

```bash
# Show test output and print statements
uv run pytest tests/integration/test_sprint_interview_to_code.py -v -s

# Show line numbers and verbose logging
uv run pytest tests/integration/test_sprint_interview_to_code.py -vv -s
```

#### Run with Coverage

```bash
uv run pytest tests/integration/test_sprint_interview_to_code.py \
  --cov=app.services \
  --cov=app.agents \
  --cov=app.runners \
  --cov-report=term-missing
```

### Markers and Skipping

The tests use a `@REQUIRES_API_KEYS` marker that skips tests when API keys are missing:

```bash
# Skip API key requirement checks (not recommended)
uv run pytest tests/integration/test_sprint_interview_to_code.py --run-skipped

# Show which tests would be skipped
uv run pytest tests/integration/test_sprint_interview_to_code.py --collect-only -q
```

### Test Execution Timeline

Expected execution times per test:

| Test | Time | Notes |
|------|------|-------|
| planning_interview_generates_questions | 30-60s | Single AI call with dual-provider |
| spec_create_with_planning_stores_metadata | 45-90s | Includes interview + dual-provider |
| dual_provider_candidates_created | 10-20s | Simple math problem, both providers |
| judge_selection_stores_metadata | 10-20s | Simple prompt, judge decision |
| checkpoints_track_execution_labels | 10-20s | Verify checkpoint structure |
| checkpoint_state_contains_metadata | 10-20s | Verify checkpoint content |
| full_sprint_interview_to_code_workflow | 120-300s | Complete workflow with code generation |
| agent_tdd_service_sprint_agent_type | 45-90s | Test filesystem tools |
| sprint_workflow_database_schema_fields | 10-20s | Quick schema validation |
| sprint_agent_uses_filesystem_tools | 10-20s | Tool registration check |
| phase_runner_workspace_persistence | 60-120s | Workspace ref across phases |

Total full suite: ~10-15 minutes (depending on AI responsiveness)

### What Each Test Validates

#### Planning Interview Tests

**test_planning_interview_generates_questions**
- Confirms AI generates 3-5 clarifying questions based on task complexity
- Validates dual-provider metadata structure (candidates, judge, selected)
- Verifies question count matches metadata
- Tests simpler tasks (hello world) requiring fewer questions

**test_spec_create_with_planning_stores_metadata**
- Confirms spec record created with status=DRAFT
- Validates planning questions stored in spec.artifacts.planning
- Verifies planning status transitions: needs_answers -> answered
- Tests metadata persistence across database commits

#### Dual-Provider Execution Tests

**test_dual_provider_candidates_created**
- Confirms both OpenAI and Anthropic clients are called
- Validates each candidate has model_name (e.g., gpt-4o, claude-3-5-sonnet)
- Checks metrics include duration_ms for performance tracking
- Verifies at least 2 candidates in dual mode

**test_judge_selection_stores_metadata**
- Confirms judge decision references a valid candidate ID
- Validates judge model_name is recorded
- Verifies selected candidate exists in candidates list
- Tests rationale field contains judge explanation

#### Checkpointing Tests

**test_checkpoints_track_execution_labels**
- Validates checkpoint labels: start, candidate:openai, candidate:anthropic, decision
- Confirms checkpoints maintain sequence order
- Checks no duplicate labels
- Tests label ordering reflects execution flow

**test_checkpoint_state_contains_metadata**
- Confirms start checkpoint has input_payload field
- Validates model_config stored in checkpoint state
- Checks subagents configuration persisted
- Tests metadata field includes custom context (test_key, etc.)

#### Full Workflow and Schema Tests

**test_full_sprint_interview_to_code_workflow**
- Complete end-to-end: interview -> answers -> sprint -> phases -> code execution
- Validates hello.py generated in artifacts directory
- Tests code execution produces "hello world" output
- Confirms PhaseRunner completes all phases (Discovery, Coding, Verification)
- Tests sprint status transitions: PLANNED -> ACTIVE -> COMPLETED

**test_agent_tdd_service_sprint_agent_type**
- Confirms SprintAgent used when agent_type='sprint' in metadata
- Validates workspace_ref set for artifact tracking
- Tests filesystem tools are invoked (fs_write_file, etc.)
- Checks candidates created with tool_calls populated

**test_sprint_workflow_database_schema_fields**
- Smoke test for schema validation
- Confirms run model_config field exists
- Validates candidate fields: provider, model_name, tool_calls, metrics, trace_id
- Tests decision fields: model_name, candidate_id, rationale

**test_sprint_agent_uses_filesystem_tools**
- Verifies SprintAgent model type (OpenAIResponsesModel or AnthropicModel)
- Tests filesystem tools registered: fs_read_file, fs_write_file, fs_list_dir
- Confirms agent tools list matches expected tools

**test_phase_runner_workspace_persistence**
- Validates workspace_ref generated in first phase
- Confirms workspace reused across Discovery, Coding, Verification
- Tests file persistence across phase boundaries

### Troubleshooting Common Issues

#### Test Skipped: "Integration tests require OPENAI_API_KEY and ANTHROPIC_API_KEY"

**Problem:** API keys not configured

**Solution:**
```bash
# Set environment variables
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# Or add to .env in backend directory
echo "OPENAI_API_KEY=sk-..." >> backend/.env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> backend/.env

# Verify they're loaded
uv run pytest tests/integration/test_sprint_interview_to_code.py --collect-only -q
```

#### Test Fails: "Dual subagent not enabled"

**Problem:** DUAL_SUBAGENT_ENABLED=false

**Solution:**
```bash
# Set in .env or environment
export DUAL_SUBAGENT_ENABLED=true
```

#### Test Fails: "Artifacts directory not configured"

**Problem:** AUTOCODE_ARTIFACTS_DIR not set or doesn't exist

**Solution:**
```bash
# Set to a temporary directory
export AUTOCODE_ARTIFACTS_DIR=/tmp/guilde-artifacts

# Or let pytest use temp_path fixture (automatic cleanup)
# Tests will skip artifact validation if directory is None
```

#### Test Hangs or Times Out

**Problem:** AI API calls are slow or unresponsive

**Solution:**
```bash
# Run with verbose logging to see where it's stuck
uv run pytest tests/integration/test_sprint_interview_to_code.py -v -s

# Check API key validity with smoke test
cd backend
uv run python scripts/openai_sdk_smoke.py
uv run python scripts/anthropic_sdk_smoke.py

# Increase test timeout (default 5 min = 300s)
uv run pytest tests/integration/test_sprint_interview_to_code.py --timeout=600
```

#### Test Fails: "hello.py not found in artifacts"

**Problem:** Code generation didn't complete successfully

**Solution:**
```bash
# Check sprint status and phase output
# Enable verbose logging:
uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_full_sprint_interview_to_code_workflow -v -s

# Review generated files:
ls -la $AUTOCODE_ARTIFACTS_DIR/

# Check checkpoints for error details
# Look for failed candidate outputs in checkpoints

# Try with simpler task:
# Update test to use max_questions=2 for faster planning
```

#### Test Fails: "Checkpoint missing input_payload"

**Problem:** Checkpoint state not captured correctly

**Solution:**
```bash
# Verify AgentTddService checkpoint creation logic
# Check that checkpoint.state includes all required fields
# Run checkpoint-specific tests:
uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_checkpoint_state_contains_metadata -v -s

# Inspect database checkpoint records:
psql $POSTGRES_URL -c "SELECT label, state FROM agent_checkpoints ORDER BY sequence LIMIT 5;"
```

#### Test Fails: "Judge decision missing model_name"

**Problem:** Judge selection not storing metadata correctly

**Solution:**
```bash
# Verify Judge implementation in AgentTddService
# Confirm model_name passed to decision constructor
# Check database schema includes model_name column

# Run judge-specific test:
uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_judge_selection_stores_metadata -v -s
```

#### OpenAI/Anthropic API Errors

**Common errors:**
- `401 Unauthorized`: Invalid API key or insufficient permissions
- `429 Too Many Requests`: Rate limit exceeded
- `503 Service Unavailable`: API temporarily down

**Solution:**
```bash
# Verify API keys are correct and have required permissions
# Use smoke tests to validate credentials:
uv run python scripts/openai_sdk_smoke.py
uv run python scripts/anthropic_sdk_smoke.py

# Check API status pages:
# - OpenAI: https://status.openai.com
# - Anthropic: https://status.anthropic.com

# Wait and retry after rate limits reset
# Reduce test frequency if hitting limits
```

### Debug Tips

#### Enable Verbose Logging

```bash
# Show all print statements from tests
uv run pytest tests/integration/test_sprint_interview_to_code.py -v -s

# Show detailed test output with timestamps
uv run pytest tests/integration/test_sprint_interview_to_code.py -vv -s --log-cli-level=DEBUG
```

#### Inspect Generated Artifacts

```bash
# List files generated during test
ls -la $AUTOCODE_ARTIFACTS_DIR/

# View hello.py content
cat $AUTOCODE_ARTIFACTS_DIR/*/hello.py

# Execute hello.py manually to test
python3 $AUTOCODE_ARTIFACTS_DIR/*/hello.py
```

#### Database Queries

```bash
# Check sprint records created by test
psql $POSTGRES_URL -c "SELECT id, name, status FROM sprints ORDER BY created_at DESC LIMIT 5;"

# Check spec records with planning artifacts
psql $POSTGRES_URL -c "SELECT id, title, status, artifacts FROM specs ORDER BY created_at DESC LIMIT 5;"

# View checkpoint sequence for a run
psql $POSTGRES_URL -c "SELECT sequence, label, state FROM agent_checkpoints WHERE run_id = '<run-uuid>' ORDER BY sequence;"
```

#### Check API Calls with Logfire

If Logfire is configured:
```bash
# Trace IDs are stored in checkpoints and candidates
# View in Logfire UI or query via API:
export LOGFIRE_READ_TOKEN=your-token
# See docs/testing.md -> Logfire Validation section for details
```

### Integration with CI/CD

The tests are designed to run in CI pipelines:

```yaml
# Example GitHub Actions
- name: Run Sprint Integration Tests
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    POSTGRES_HOST: localhost
    POSTGRES_PASSWORD: postgres
    DATABASE_URL: postgresql://postgres:postgres@localhost/guilde_test
  run: |
    cd backend
    uv run pytest tests/integration/test_sprint_interview_to_code.py -v --tb=short
```

Key considerations:
- Tests make real API calls (charges apply)
- Use service accounts or dedicated API keys for CI
- Set reasonable timeouts (300s for local, 600s for CI)
- Mock WebSocket broadcasts if not under test
- Collect artifacts and logs on failure for debugging
