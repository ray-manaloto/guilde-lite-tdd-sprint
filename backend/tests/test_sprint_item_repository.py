"""Tests for sprint item repository."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.db.models.sprint import SprintItem, SprintItemStatus
from app.repositories import sprint_item as sprint_item_repo


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
    mock_item = SprintItem(id=uuid4(), title="Test Item")
    mock_session.get.return_value = mock_item

    result = await sprint_item_repo.get_by_id(mock_session, mock_item.id)

    assert result == mock_item
    mock_session.get.assert_called_once_with(SprintItem, mock_item.id)


@pytest.mark.anyio
async def test_get_by_sprint(mock_session):
    """Test get_by_sprint."""
    sprint_id = uuid4()
    mock_items = [SprintItem(id=uuid4(), sprint_id=sprint_id) for _ in range(3)]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_items
    mock_session.execute.return_value = mock_result

    result = await sprint_item_repo.get_by_sprint(mock_session, sprint_id=sprint_id)

    assert result == mock_items
    mock_session.execute.assert_called_once()


@pytest.mark.anyio
async def test_create(mock_session):
    """Test create."""
    sprint_id = uuid4()
    title = "New Item"
    status = SprintItemStatus.TODO
    
    # Mock refresh to set ID
    async def refresh_side_effect(obj):
        obj.id = uuid4()
    mock_session.refresh.side_effect = refresh_side_effect

    result = await sprint_item_repo.create(
        mock_session,
        sprint_id=sprint_id,
        title=title,
        description="Desc",
        status=status,
        priority=1,
        estimate_points=5
    )

    assert result.title == title
    assert result.sprint_id == sprint_id
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
    mock_session.refresh.assert_called_once()


@pytest.mark.anyio
async def test_update(mock_session):
    """Test update."""
    mock_item = SprintItem(id=uuid4(), title="Old Title")
    update_data = {"title": "New Title"}

    result = await sprint_item_repo.update(
        mock_session,
        db_item=mock_item,
        update_data=update_data
    )

    assert result.title == "New Title"
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
    mock_session.refresh.assert_called_once()


@pytest.mark.anyio
async def test_delete(mock_session):
    """Test delete."""
    mock_item = SprintItem(id=uuid4())
    mock_session.get.return_value = mock_item

    result = await sprint_item_repo.delete(mock_session, mock_item.id)

    assert result == mock_item
    mock_session.delete.assert_called_once_with(mock_item)
    mock_session.flush.assert_called_once()
