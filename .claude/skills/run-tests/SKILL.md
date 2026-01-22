---
name: run-tests
description: Run tests intelligently based on scope (backend, frontend, e2e, or specific file)
metadata:
  claude:
    disable-model-invocation: true
    arguments:
      - name: scope
        description: "Test scope: all | backend | frontend | e2e | file:<path>"
        required: false
---

# Smart Test Runner

Run tests for this FastAPI + Next.js project based on the specified scope.

## Default Behavior
If no scope is provided, detect which tests to run based on recent file changes.

## Scopes

### `all` - Run all tests
```bash
cd backend && uv run pytest
cd frontend && bun test:run
```

### `backend` - Run Python tests only
```bash
cd backend && uv run pytest -v
```

### `frontend` - Run Vitest unit tests only
```bash
cd frontend && bun test:run
```

### `e2e` - Run Playwright end-to-end tests
```bash
cd frontend && bun test:e2e
```

### `file:<path>` - Run specific test file or related tests
For a test file, run it directly. For a source file, find and run related tests.

**Backend example:**
```bash
cd backend && uv run pytest tests/test_services.py -v
```

**Frontend example:**
```bash
cd frontend && bun test src/components/Button.test.tsx
```

## Test Output

- Show test results clearly
- If tests fail, provide a summary of failures
- Offer to help fix failing tests

## Coverage (optional)

If the user wants coverage:
```bash
# Backend
cd backend && uv run pytest --cov=app --cov-report=term-missing

# Frontend
cd frontend && bun test:coverage
```
