"""Tests for sprint repository."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models.sprint import Sprint, SprintStatus
from app.repositories import sprint as sprint_repo


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = MagicMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.mark.anyio
async def test_get_by_id(mock_session):
    """Test get_by_id."""
    mock_sprint = Sprint(id=uuid4(), name="Test Sprint")
    mock_session.get.return_value = mock_sprint

    result = await sprint_repo.get_by_id(mock_session, mock_sprint.id)

    assert result == mock_sprint
    mock_session.get.assert_called_once_with(Sprint, mock_sprint.id)


@pytest.mark.anyio
async def test_get_by_id_with_items(mock_session):
    """Test get_by_id_with_items."""
    mock_sprint = Sprint(id=uuid4(), name="Test Sprint")
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_sprint
    mock_session.execute.return_value = mock_result

    result = await sprint_repo.get_by_id_with_items(mock_session, mock_sprint.id)

    assert result == mock_sprint
    # We can't easily assert the complex select query equality with mocks,
    # but we verify execute was called.
    mock_session.execute.assert_called_once()


@pytest.mark.anyio
async def test_get_multi(mock_session):
    """Test get_multi."""
    mock_sprints = [Sprint(id=uuid4(), name=f"Sprint {i}") for i in range(3)]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_sprints
    mock_session.execute.return_value = mock_result

    result = await sprint_repo.get_multi(mock_session)

    assert result == mock_sprints
    mock_session.execute.assert_called_once()


@pytest.mark.anyio
async def test_create(mock_session):
    """Test create."""
    name = "New Sprint"
    
    # Mock refresh to set ID
    async def refresh_side_effect(obj):
        obj.id = uuid4()
    mock_session.refresh.side_effect = refresh_side_effect

    result = await sprint_repo.create(mock_session, name=name)

    assert result.name == name
    assert result.status == SprintStatus.PLANNED
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
    mock_session.refresh.assert_called_once()


@pytest.mark.anyio
async def test_update(mock_session):
    """Test update."""
    mock_sprint = Sprint(id=uuid4(), name="Old Name", status=SprintStatus.PLANNED)
    update_data = {"name": "New Name", "status": SprintStatus.ACTIVE}

    result = await sprint_repo.update(
        mock_session, 
        db_sprint=mock_sprint, 
        update_data=update_data
    )

    assert result.name == "New Name"
    assert result.status == SprintStatus.ACTIVE
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
    mock_session.refresh.assert_called_once()


@pytest.mark.anyio
async def test_delete(mock_session):
    """Test delete."""
    mock_sprint = Sprint(id=uuid4(), name="To Delete")
    mock_session.get.return_value = mock_sprint

    result = await sprint_repo.delete(mock_session, mock_sprint.id)

    assert result == mock_sprint
    mock_session.delete.assert_called_once_with(mock_sprint)
    mock_session.flush.assert_called_once()
