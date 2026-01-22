"""Integration test fixtures."""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

pytestmark = pytest.mark.integration

_DISALLOWED_FIXTURES = {"monkeypatch", "mocker"}


def pytest_runtest_setup(item: pytest.Item) -> None:
    disallowed = _DISALLOWED_FIXTURES.intersection(getattr(item, "fixturenames", []))
    if disallowed:
        names = ", ".join(sorted(disallowed))
        raise pytest.UsageError(
            f"Integration tests must not use mocks/patch fixtures: {names}"
        )


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a real database session for integration tests."""
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=NullPool,
    )
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()
            await engine.dispose()
