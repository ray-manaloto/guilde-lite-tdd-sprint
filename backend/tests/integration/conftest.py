"""Integration test fixtures."""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker, engine


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a real database session for integration tests."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()
            await engine.dispose()
