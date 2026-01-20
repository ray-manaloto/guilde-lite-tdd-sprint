"""Tests for spec workflow routes."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.db.models.spec import SpecComplexity, SpecStatus
from app.main import app


class MockSpec:
    """Mock spec."""

    def __init__(
        self,
        id=None,
        title="Spec Draft",
        task="Build a sprint planner",
        complexity=SpecComplexity.STANDARD,
        status=SpecStatus.DRAFT,
        phases=None,
        artifacts=None,
        user_id=None,
    ):
        self.id = id or uuid4()
        self.user_id = user_id
        self.title = title
        self.task = task
        self.complexity = complexity
        self.status = status
        self.phases = phases or ["discovery", "spec", "validation"]
        self.artifacts = artifacts or {}
        self.created_at = datetime.now(UTC)
        self.updated_at = None


@pytest.fixture
def mock_spec() -> MockSpec:
    return MockSpec()


@pytest.fixture
def mock_spec_service(mock_spec: MockSpec) -> MagicMock:
    service = MagicMock()
    service.create = AsyncMock(return_value=mock_spec)
    service.create_with_planning = AsyncMock(
        return_value=(
            mock_spec,
            {
                "status": "needs_answers",
                "questions": [
                    {"question": "Who is the primary user?", "rationale": "Clarify audience."}
                ],
                "answers": [],
                "metadata": {"provider": "openai", "model_name": "openai-responses:test"},
            },
        )
    )
    service.get_by_id = AsyncMock(return_value=mock_spec)
    service.save_planning_answers = AsyncMock(
        return_value=(
            mock_spec,
            {
                "status": "answered",
                "questions": [{"question": "Who is the primary user?"}],
                "answers": [{"question": "Who is the primary user?", "answer": "Team leads"}],
                "metadata": {"provider": "openai"},
            },
        )
    )
    service.validate = AsyncMock(return_value=(mock_spec, {"valid": True, "errors": [], "warnings": []}))
    return service


@pytest.fixture
async def client_with_mock_service(
    mock_spec_service: MagicMock,
    mock_db_session,
) -> AsyncClient:
    from httpx import ASGITransport

    from app.api.deps import get_spec_service
    from app.db.session import get_db_session

    app.dependency_overrides[get_spec_service] = lambda db=None: mock_spec_service
    app.dependency_overrides[get_db_session] = lambda: mock_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_create_spec_success(client_with_mock_service: AsyncClient):
    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/specs",
        json={"task": "Build a sprint planner"},
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Spec Draft"


@pytest.mark.anyio
async def test_get_spec_success(
    client_with_mock_service: AsyncClient,
    mock_spec: MockSpec,
):
    response = await client_with_mock_service.get(
        f"{settings.API_V1_STR}/specs/{mock_spec.id}",
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(mock_spec.id)


@pytest.mark.anyio
async def test_get_spec_not_found(
    client_with_mock_service: AsyncClient,
    mock_spec_service: MagicMock,
):
    from app.core.exceptions import NotFoundError

    mock_spec_service.get_by_id = AsyncMock(
        side_effect=NotFoundError(message="Spec not found")
    )
    response = await client_with_mock_service.get(
        f"{settings.API_V1_STR}/specs/{uuid4()}",
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_validate_spec_success(
    client_with_mock_service: AsyncClient,
    mock_spec: MockSpec,
):
    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/specs/{mock_spec.id}/validate",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["validation"]["valid"] is True


@pytest.mark.anyio
async def test_create_spec_planning_success(client_with_mock_service: AsyncClient):
    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/specs/planning",
        json={"task": "Plan sprint outcomes"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["planning"]["status"] == "needs_answers"
    assert data["planning"]["questions"]


@pytest.mark.anyio
async def test_save_planning_answers_success(
    client_with_mock_service: AsyncClient,
    mock_spec: MockSpec,
):
    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/specs/{mock_spec.id}/planning/answers",
        json={"answers": [{"question": "Who is the primary user?", "answer": "Team leads"}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["planning"]["status"] == "answered"
