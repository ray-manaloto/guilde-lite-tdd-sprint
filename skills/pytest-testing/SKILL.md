---
name: pytest-testing
description: Python testing with pytest for FastAPI applications. Use when writing tests, fixing test failures, setting up test infrastructure, or implementing TDD workflows.
---

# pytest Testing for FastAPI

Comprehensive testing patterns for this project's FastAPI backend.

## Project Test Structure

```
backend/tests/
├── conftest.py           # Shared fixtures
├── unit/                 # Unit tests
│   ├── test_services/
│   └── test_repositories/
├── integration/          # Integration tests
│   ├── test_api/
│   └── test_agents/
└── e2e/                  # End-to-end tests
```

## Running Tests

```bash
cd backend

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_services/test_sprint.py

# Run tests matching pattern
uv run pytest -k "test_sprint"

# Run with verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x

# Run failed tests from last run
uv run pytest --lf
```

## Key Fixtures (conftest.py)

```python
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.main import app
from app.db.session import get_db

@pytest.fixture
async def db_session():
    """Provide a clean database session for each test."""
    # Use test database
    engine = create_async_engine(settings.TEST_DATABASE_URL)
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session):
    """Async HTTP client for API testing."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest.fixture
def mock_anthropic(mocker):
    """Mock Anthropic API calls."""
    return mocker.patch("anthropic.Anthropic")
```

## Testing Patterns

### Service Tests

```python
# tests/unit/test_services/test_sprint.py
import pytest
from app.services.sprint import SprintService
from app.schemas.sprint import SprintCreate

@pytest.mark.asyncio
async def test_create_sprint(db_session):
    service = SprintService(db_session)

    sprint_data = SprintCreate(
        title="Test Sprint",
        spec_id="spec-123"
    )

    sprint = await service.create(sprint_data)

    assert sprint.title == "Test Sprint"
    assert sprint.status == "pending"

@pytest.mark.asyncio
async def test_create_sprint_duplicate_raises(db_session):
    service = SprintService(db_session)

    await service.create(SprintCreate(title="Sprint 1", spec_id="spec-123"))

    with pytest.raises(AlreadyExistsError):
        await service.create(SprintCreate(title="Sprint 1", spec_id="spec-123"))
```

### API Tests

```python
# tests/integration/test_api/test_sprints.py
import pytest

@pytest.mark.asyncio
async def test_create_sprint_endpoint(client, auth_headers):
    response = await client.post(
        "/api/v1/sprints",
        json={"title": "New Sprint", "spec_id": "spec-123"},
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Sprint"

@pytest.mark.asyncio
async def test_create_sprint_unauthorized(client):
    response = await client.post(
        "/api/v1/sprints",
        json={"title": "New Sprint", "spec_id": "spec-123"}
    )

    assert response.status_code == 401
```

### Agent Tests

```python
# tests/integration/test_agents/test_sprint_agent.py
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_sprint_agent_planning(mock_anthropic, db_session):
    mock_anthropic.return_value.messages.create = AsyncMock(
        return_value=MockResponse(content="Plan: ...")
    )

    agent = SprintAgent(db_session)
    result = await agent.plan_sprint("Build auth system")

    assert result.tasks is not None
    assert len(result.tasks) > 0
```

### Parametrized Tests

```python
@pytest.mark.parametrize("status,expected", [
    ("pending", True),
    ("in_progress", True),
    ("completed", False),
    ("failed", False),
])
async def test_sprint_can_start(status, expected, db_session):
    sprint = await create_sprint(db_session, status=status)
    assert sprint.can_start() == expected
```

## Mocking Best Practices

```python
# Mock external APIs
@pytest.fixture
def mock_openai(mocker):
    mock = mocker.patch("openai.AsyncOpenAI")
    mock.return_value.chat.completions.create = AsyncMock(
        return_value=MockCompletion(content="Response")
    )
    return mock

# Mock time
@pytest.fixture
def frozen_time(mocker):
    return mocker.patch("app.services.sprint.datetime",
                        now=lambda: datetime(2024, 1, 1))

# Mock Redis
@pytest.fixture
def mock_redis(mocker):
    return mocker.patch("app.core.redis.redis_client")
```

## Test Database Setup

```python
# conftest.py
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    """Create test database."""
    engine = create_async_engine(settings.TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

## Common Issues & Solutions

### Async Test Failures

```python
# Always use @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_call()
    assert result is not None
```

### Database State Leaking

```python
# Use transaction rollback in fixtures
@pytest.fixture
async def db_session(test_db):
    async with AsyncSession(test_db) as session:
        yield session
        await session.rollback()  # Cleanup
```

### Slow Tests

```bash
# Run tests in parallel
uv run pytest -n auto

# Profile slow tests
uv run pytest --durations=10
```

## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
