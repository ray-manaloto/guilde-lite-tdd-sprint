# Testing Workflow (Repo-Specific)

## Test Matrix

Run for every feature change:
- Backend unit + API tests: `uv run pytest`
- Frontend unit tests: `bun run test:run`
- Playwright E2E smoke: `bun run test:e2e`

Run when DB schema or service logic changes:
- Add or update integration tests under `backend/tests/integration/`

## Backend Commands

```bash
cd backend
uv run pytest
uv run pytest tests/integration/ -v
uv run pytest tests/api/ -v
```

## Frontend Commands

```bash
cd frontend
bun run test:run
bun run test:e2e
```

## Playwright Notes

- Requires backend running at `http://localhost:8000`.
- `frontend/playwright.config.ts` starts the frontend for local runs.
- Set `PLAYWRIGHT_BASE_URL` if the frontend is already running elsewhere.

## Integration Test Pattern

Use the service layer + DB session to validate real DB behavior:

```python
async def test_create_item_integration(db_session):
    service = ItemService(db_session)
    item = await service.create(ItemCreate(name="Test"))
    assert item.id is not None
```
