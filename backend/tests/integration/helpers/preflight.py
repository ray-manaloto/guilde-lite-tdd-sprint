"""Pre-flight service validation fixtures and helpers for integration tests.

This module provides pytest fixtures and helper functions to verify that
required services (PostgreSQL, Redis, Backend API, WebSocket) are available
before running integration tests.

Usage in tests:
    @pytest.mark.usefixtures("require_live_services")
    class TestIntegration:
        async def test_something(self):
            # Test will be skipped if services unavailable
            pass

    async def test_with_explicit_check(require_database):
        # Only requires database to be available
        pass
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


class ServiceStatus(StrEnum):
    """Service health status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class ServiceCheckResult:
    """Result of a single service health check."""

    service: str
    status: ServiceStatus
    message: str = ""
    latency_ms: float = 0.0


# =============================================================================
# Individual Service Check Functions
# =============================================================================


async def check_postgresql(
    database_url: str | None = None,
    timeout: float = 5.0,
) -> ServiceCheckResult:
    """Check PostgreSQL connectivity.

    Args:
        database_url: Database connection URL (uses settings if None)
        timeout: Connection timeout in seconds

    Returns:
        ServiceCheckResult with health status
    """
    import time

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    if database_url is None:
        from app.core.config import settings

        database_url = settings.DATABASE_URL

    start = time.perf_counter()
    try:
        engine = create_async_engine(database_url, pool_timeout=timeout)
        async with engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=timeout)
        latency = (time.perf_counter() - start) * 1000
        await engine.dispose()
        return ServiceCheckResult(
            service="postgresql",
            status=ServiceStatus.HEALTHY,
            message="Connection successful",
            latency_ms=latency,
        )
    except TimeoutError:
        return ServiceCheckResult(
            service="postgresql",
            status=ServiceStatus.TIMEOUT,
            message=f"Connection timeout after {timeout}s",
        )
    except Exception as e:
        return ServiceCheckResult(
            service="postgresql",
            status=ServiceStatus.UNHEALTHY,
            message=str(e),
        )


async def check_redis(
    redis_url: str | None = None,
    timeout: float = 2.0,
) -> ServiceCheckResult:
    """Check Redis connectivity.

    Args:
        redis_url: Redis connection URL (uses settings if None)
        timeout: Connection timeout in seconds

    Returns:
        ServiceCheckResult with health status
    """
    import time

    from redis.asyncio import Redis

    if redis_url is None:
        from app.core.config import settings

        redis_url = settings.REDIS_URL

    start = time.perf_counter()
    try:
        client = Redis.from_url(redis_url, socket_timeout=timeout)
        pong = await asyncio.wait_for(client.ping(), timeout=timeout)
        latency = (time.perf_counter() - start) * 1000
        await client.aclose()
        return ServiceCheckResult(
            service="redis",
            status=ServiceStatus.HEALTHY if pong else ServiceStatus.UNHEALTHY,
            message="PONG received" if pong else "No PONG response",
            latency_ms=latency,
        )
    except TimeoutError:
        return ServiceCheckResult(
            service="redis",
            status=ServiceStatus.TIMEOUT,
            message=f"Connection timeout after {timeout}s",
        )
    except Exception as e:
        return ServiceCheckResult(
            service="redis",
            status=ServiceStatus.UNHEALTHY,
            message=str(e),
        )


async def check_backend_api(
    base_url: str = "http://localhost:8000",
    timeout: float = 10.0,
) -> ServiceCheckResult:
    """Check backend API health endpoint.

    Args:
        base_url: Backend API base URL
        timeout: Request timeout in seconds

    Returns:
        ServiceCheckResult with health status
    """
    import time

    import httpx

    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{base_url}/api/v1/health")
            latency = (time.perf_counter() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                return ServiceCheckResult(
                    service="backend_api",
                    status=ServiceStatus.HEALTHY,
                    message=f"Status: {data.get('status', 'unknown')}",
                    latency_ms=latency,
                )
            else:
                return ServiceCheckResult(
                    service="backend_api",
                    status=ServiceStatus.UNHEALTHY,
                    message=f"HTTP {response.status_code}",
                    latency_ms=latency,
                )
    except httpx.TimeoutException:
        return ServiceCheckResult(
            service="backend_api",
            status=ServiceStatus.TIMEOUT,
            message=f"Request timeout after {timeout}s",
        )
    except httpx.ConnectError:
        return ServiceCheckResult(
            service="backend_api",
            status=ServiceStatus.UNHEALTHY,
            message="Connection refused - server not running",
        )
    except Exception as e:
        return ServiceCheckResult(
            service="backend_api",
            status=ServiceStatus.UNHEALTHY,
            message=str(e),
        )


async def check_websocket(
    ws_url: str = "ws://localhost:8000/api/v1/ws",
    timeout: float = 5.0,
) -> ServiceCheckResult:
    """Check WebSocket connectivity.

    Args:
        ws_url: WebSocket URL
        timeout: Connection timeout in seconds

    Returns:
        ServiceCheckResult with health status
    """
    import time

    try:
        import websockets
    except ImportError:
        return ServiceCheckResult(
            service="websocket",
            status=ServiceStatus.UNKNOWN,
            message="websockets package not installed",
        )

    start = time.perf_counter()
    try:
        async with asyncio.timeout(timeout):
            async with websockets.connect(ws_url) as ws:
                pong = await ws.ping()
                await pong
                latency = (time.perf_counter() - start) * 1000
                return ServiceCheckResult(
                    service="websocket",
                    status=ServiceStatus.HEALTHY,
                    message="WebSocket connection successful",
                    latency_ms=latency,
                )
    except TimeoutError:
        return ServiceCheckResult(
            service="websocket",
            status=ServiceStatus.TIMEOUT,
            message=f"Connection timeout after {timeout}s",
        )
    except Exception as e:
        return ServiceCheckResult(
            service="websocket",
            status=ServiceStatus.UNHEALTHY,
            message=str(e),
        )


async def check_all_services(
    check_backend: bool = True,
    check_ws: bool = True,
) -> dict[str, ServiceCheckResult]:
    """Check all services and return results.

    Args:
        check_backend: Whether to check backend API
        check_ws: Whether to check WebSocket

    Returns:
        Dict mapping service name to check result
    """
    results: dict[str, ServiceCheckResult] = {}

    # Always check database and redis
    results["postgresql"] = await check_postgresql()
    results["redis"] = await check_redis()

    if check_backend:
        results["backend_api"] = await check_backend_api()

    if check_ws:
        results["websocket"] = await check_websocket()

    return results


def services_available(results: dict[str, ServiceCheckResult]) -> bool:
    """Check if all services in results are healthy.

    Args:
        results: Dict of service check results

    Returns:
        True if all services are healthy
    """
    return all(r.status == ServiceStatus.HEALTHY for r in results.values())


# =============================================================================
# Pytest Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default event loop policy for session-scoped async fixtures."""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="session")
async def preflight_check() -> dict[str, ServiceCheckResult]:
    """Session-scoped preflight check for integration tests.

    Runs once at the start of the test session and returns results.
    Use with require_live_services for automatic skip behavior.

    Returns:
        Dict of service check results
    """
    return await check_all_services(check_backend=False, check_ws=False)


@pytest.fixture(scope="session")
async def preflight_check_full() -> dict[str, ServiceCheckResult]:
    """Full preflight check including backend API and WebSocket.

    Runs once at the start of the test session.

    Returns:
        Dict of service check results
    """
    return await check_all_services(check_backend=True, check_ws=True)


@pytest.fixture
async def require_live_services(
    preflight_check: dict[str, ServiceCheckResult],
) -> dict[str, ServiceCheckResult]:
    """Fixture that skips tests if critical services are unavailable.

    Use this fixture for integration tests that require database and Redis.

    Example:
        @pytest.mark.usefixtures("require_live_services")
        class TestIntegration:
            async def test_something(self):
                pass

    Returns:
        The preflight check results if all services are healthy

    Raises:
        pytest.skip: If any critical service is unavailable
    """
    failures = [
        f"{name}: {result.message}"
        for name, result in preflight_check.items()
        if result.status != ServiceStatus.HEALTHY
    ]

    if failures:
        pytest.skip(f"Required services unavailable: {', '.join(failures)}")

    return preflight_check


@pytest.fixture
async def require_database() -> ServiceCheckResult:
    """Fixture that skips tests if PostgreSQL is unavailable.

    Use for tests that only require database connectivity.

    Returns:
        Database check result if healthy

    Raises:
        pytest.skip: If database is unavailable
    """
    result = await check_postgresql()
    if result.status != ServiceStatus.HEALTHY:
        pytest.skip(f"PostgreSQL unavailable: {result.message}")
    return result


@pytest.fixture
async def require_redis() -> ServiceCheckResult:
    """Fixture that skips tests if Redis is unavailable.

    Use for tests that only require Redis connectivity.

    Returns:
        Redis check result if healthy

    Raises:
        pytest.skip: If Redis is unavailable
    """
    result = await check_redis()
    if result.status != ServiceStatus.HEALTHY:
        pytest.skip(f"Redis unavailable: {result.message}")
    return result


@pytest.fixture
async def require_backend_api() -> ServiceCheckResult:
    """Fixture that skips tests if backend API is unavailable.

    Use for tests that require the backend server to be running.

    Returns:
        Backend API check result if healthy

    Raises:
        pytest.skip: If backend API is unavailable
    """
    result = await check_backend_api()
    if result.status != ServiceStatus.HEALTHY:
        pytest.skip(f"Backend API unavailable: {result.message}")
    return result


@pytest.fixture
async def require_websocket() -> ServiceCheckResult:
    """Fixture that skips tests if WebSocket is unavailable.

    Use for tests that require WebSocket connectivity.

    Returns:
        WebSocket check result if healthy

    Raises:
        pytest.skip: If WebSocket is unavailable
    """
    result = await check_websocket()
    if result.status != ServiceStatus.HEALTHY:
        pytest.skip(f"WebSocket unavailable: {result.message}")
    return result


@pytest.fixture
async def require_full_stack(
    preflight_check_full: dict[str, ServiceCheckResult],
) -> dict[str, ServiceCheckResult]:
    """Fixture that skips tests if any service is unavailable.

    Use for full integration/E2E tests that require all services.

    Returns:
        The full preflight check results if all services are healthy

    Raises:
        pytest.skip: If any service is unavailable
    """
    failures = [
        f"{name}: {result.message}"
        for name, result in preflight_check_full.items()
        if result.status != ServiceStatus.HEALTHY
    ]

    if failures:
        pytest.skip(f"Required services unavailable: {', '.join(failures)}")

    return preflight_check_full


# =============================================================================
# Convenience Decorators
# =============================================================================


def skip_if_services_unavailable(*services: str):
    """Decorator to skip tests if specified services are unavailable.

    Args:
        services: Service names to check ("postgresql", "redis", "backend_api", "websocket")

    Example:
        @skip_if_services_unavailable("postgresql", "redis")
        async def test_database_operations():
            pass
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            service_checks = {
                "postgresql": check_postgresql,
                "redis": check_redis,
                "backend_api": check_backend_api,
                "websocket": check_websocket,
            }

            for service in services:
                if service not in service_checks:
                    raise ValueError(f"Unknown service: {service}")

                result = await service_checks[service]()
                if result.status != ServiceStatus.HEALTHY:
                    pytest.skip(f"{service} unavailable: {result.message}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator
