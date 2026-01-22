# Integration Tests

This directory contains integration tests that validate the system's core workflows end-to-end.

## Test Files

### test_sprint_interview_to_code.py

**Priority:** P0 (Critical)
**Execution Time:** 5-15 minutes (full suite)
**Purpose:** Validates the complete sprint workflow from planning interview through code execution

This is the main integration test suite for the sprint TDD feature. It tests:

1. **Planning Interview Phase**: AI generates clarifying questions via dual-provider execution (OpenAI + Anthropic)
2. **Dual-Provider Execution**: Both providers run and a judge selects the best response
3. **Checkpointing**: Execution state is captured at key lifecycle points
4. **Full Workflow**: End-to-end flow from spec → sprint → code generation → validation

**Test Groups:**

| Test | Duration | What It Validates |
|------|----------|-------------------|
| test_planning_interview_generates_questions | 30-60s | Questions generated with dual-provider metadata |
| test_spec_create_with_planning_stores_metadata | 45-90s | Planning results stored in spec artifacts |
| test_dual_provider_candidates_created | 10-20s | Both OpenAI and Anthropic create candidates |
| test_judge_selection_stores_metadata | 10-20s | Judge selects winning candidate and stores rationale |
| test_checkpoints_track_execution_labels | 10-20s | Checkpoint labels (start, candidate:*, decision) exist |
| test_checkpoint_state_contains_metadata | 10-20s | Checkpoint state includes input payload and metadata |
| test_full_sprint_interview_to_code_workflow | 120-300s | Complete workflow with code generation and execution |
| test_agent_tdd_service_sprint_agent_type | 45-90s | SprintAgent uses filesystem tools |
| test_sprint_workflow_database_schema_fields | 10-20s | Schema has required fields |
| test_sprint_agent_uses_filesystem_tools | 10-20s | Filesystem tools registered |
| test_phase_runner_workspace_persistence | 60-120s | Workspace ref persists across phases |

## Running Tests

### Prerequisites

```bash
# Set required environment variables
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export DUAL_SUBAGENT_ENABLED=true
export AUTOCODE_ARTIFACTS_DIR=/tmp/guilde-artifacts
export POSTGRES_HOST=localhost
export POSTGRES_PASSWORD=secret
```

### Run All Integration Tests

```bash
cd backend
uv run pytest tests/integration/ -v
```

### Run Specific Test File

```bash
uv run pytest tests/integration/test_sprint_interview_to_code.py -v
```

### Run Test Class

```bash
uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow -v
```

### Run Single Test with Output

```bash
uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_planning_interview_generates_questions -v -s
```

### Run Fast Tests First (for quick feedback)

```bash
# These complete in 10-20 seconds each:
uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_checkpoints_track_execution_labels -v
uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_checkpoint_state_contains_metadata -v
```

### Run Full Workflow (longest test)

```bash
# This takes 2-5 minutes:
uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_full_sprint_interview_to_code_workflow -v -s
```

### Run with Coverage

```bash
uv run pytest tests/integration/test_sprint_interview_to_code.py \
  --cov=app.services \
  --cov=app.agents \
  --cov=app.runners \
  --cov-report=term-missing
```

## Environment Variables

### Required

```bash
OPENAI_API_KEY              # Your OpenAI API key (format: sk-...)
ANTHROPIC_API_KEY          # Your Anthropic API key (format: sk-ant-...)
```

### Configuration

```bash
DUAL_SUBAGENT_ENABLED=true           # Enable dual-provider execution (default)
OPENAI_MODEL=gpt-4o                  # OpenAI model to use
ANTHROPIC_MODEL=claude-3-5-sonnet    # Anthropic model to use
JUDGE_MODEL=gpt-4o                   # Judge model for selection
AUTOCODE_ARTIFACTS_DIR=/tmp/guilde   # Directory for generated files
PLANNING_INTERVIEW_MODE=live          # Use real AI (not "stub")
AGENT_FS_ENABLED=true                # Enable filesystem tools
```

### Database (for local testing)

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=guilde_lite_tdd_sprint
POSTGRES_PASSWORD=secret
DATABASE_URL=postgresql://postgres:secret@localhost/guilde_lite_tdd_sprint
```

## Common Issues

### Tests Skipped: "requires OPENAI_API_KEY and ANTHROPIC_API_KEY"

**Problem:** Environment variables not set

**Solution:**
```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
```

### Test Fails: "Dual subagent not enabled"

**Problem:** DUAL_SUBAGENT_ENABLED is false

**Solution:**
```bash
export DUAL_SUBAGENT_ENABLED=true
```

### Test Fails: "hello.py not found in artifacts"

**Problem:** Code generation incomplete or AUTOCODE_ARTIFACTS_DIR not writable

**Solution:**
```bash
# Create and verify artifacts directory
export AUTOCODE_ARTIFACTS_DIR=/tmp/guilde-artifacts
mkdir -p $AUTOCODE_ARTIFACTS_DIR
chmod 755 $AUTOCODE_ARTIFACTS_DIR

# Run test with verbose output
uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_full_sprint_interview_to_code_workflow -v -s

# Check what files were created
ls -la $AUTOCODE_ARTIFACTS_DIR/
```

### Test Times Out

**Problem:** AI API calls are slow

**Solution:**
```bash
# Run simpler tests first to verify API keys work
uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_checkpoints_track_execution_labels -v -s

# Verify API key validity
cd backend
uv run python scripts/openai_sdk_smoke.py
uv run python scripts/anthropic_sdk_smoke.py

# Increase timeout for slow networks
uv run pytest tests/integration/test_sprint_interview_to_code.py --timeout=600
```

### "Judge decision missing model_name"

**Problem:** Judge metadata not stored correctly

**Solution:**
```bash
# Run judge-specific test for diagnostics
uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_judge_selection_stores_metadata -v -s

# Check database schema
psql $POSTGRES_URL -c "\d agent_decisions;"
```

### API Rate Limiting (429 errors)

**Problem:** Too many API calls in short time

**Solution:**
```bash
# Wait a few minutes before retrying
# Run tests with longer intervals between runs
# Use dedicated API key with higher rate limits
```

## Debug Workflow

1. **Start with fast tests** to verify environment:
   ```bash
   uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_checkpoints_track_execution_labels -v -s
   ```

2. **Check API connectivity**:
   ```bash
   cd backend
   uv run python scripts/openai_sdk_smoke.py
   uv run python scripts/anthropic_sdk_smoke.py
   ```

3. **Run planning interview test**:
   ```bash
   uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_planning_interview_generates_questions -v -s
   ```

4. **Run dual-provider tests**:
   ```bash
   uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_dual_provider_candidates_created -v -s
   ```

5. **Run full workflow** (if earlier tests pass):
   ```bash
   uv run pytest tests/integration/test_sprint_interview_to_code.py::TestSprintInterviewToCodeWorkflow::test_full_sprint_interview_to_code_workflow -v -s
   ```

## Test Structure

Each test in `TestSprintInterviewToCodeWorkflow` follows this pattern:

1. **Arrange**: Set up test data and services
2. **Act**: Execute the feature under test
3. **Assert**: Verify expected outcomes
4. **Cleanup**: Automatic via fixtures (database rollback, artifact cleanup)

Key fixtures:
- `db_session`: Database session with automatic rollback
- `artifacts_dir`: Clean artifacts directory for file generation
- `temp_workspace`: Temporary directory for test artifacts

## Viewing Test Results

### Standard Output

```bash
uv run pytest tests/integration/test_sprint_interview_to_code.py -v
```

Output shows:
- Test name and status (PASSED/FAILED/SKIPPED)
- Execution time
- Short error messages

### Verbose Output with Prints

```bash
uv run pytest tests/integration/test_sprint_interview_to_code.py -v -s
```

Shows:
- All print statements from tests
- Full error tracebacks
- Generated questions and answers

### With Logging

```bash
uv run pytest tests/integration/test_sprint_interview_to_code.py -vv -s --log-cli-level=DEBUG
```

Shows:
- Debug-level logs from application
- SQL queries (if SQLAlchemy logging enabled)
- Detailed execution flow

## Integration with CI/CD

Tests are designed to run in automated pipelines:

```yaml
# Example GitHub Actions
- name: Run Integration Tests
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    cd backend
    uv run pytest tests/integration/test_sprint_interview_to_code.py -v --tb=short --timeout=600
```

## Further Reading

- Full testing guide: `docs/testing.md`
- Sprint workflow design: `docs/design/sprint_interview_to_code_integration_test.md`
- Architecture docs: `docs/architecture.md`
