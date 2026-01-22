#!/usr/bin/env python
"""Pre-flight service validator for integration tests.

Usage:
    uv run python scripts/preflight.py [--backend-only] [--wait SECONDS] [--verbose]

Exit codes:
    0 - All services healthy
    1 - One or more services failed
    2 - Configuration error
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

if TYPE_CHECKING:
    pass


class ServiceStatus(StrEnum):
    """Service health status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """Result of a service health check."""

    service: str
    status: ServiceStatus
    latency_ms: float = 0
    details: str = ""
    critical: bool = True


@dataclass
class PreflightReport:
    """Aggregate report of all service checks."""

    results: list[CheckResult] = field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        """All critical services are healthy."""
        return all(r.status == ServiceStatus.HEALTHY for r in self.results if r.critical)

    @property
    def critical_failures(self) -> list[CheckResult]:
        """List of failed critical services."""
        return [r for r in self.results if r.critical and r.status != ServiceStatus.HEALTHY]


class ServiceChecker(Protocol):
    """Protocol for service health checkers."""

    async def check(self) -> CheckResult:
        """Perform health check and return result."""
        ...


class PostgresChecker:
    """PostgreSQL database connectivity check."""

    def __init__(self, database_url: str, timeout: float = 5.0):
        self.database_url = database_url
        self.timeout = timeout

    async def check(self) -> CheckResult:
        """Check PostgreSQL connectivity with SELECT 1."""
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        start = time.perf_counter()
        try:
            engine = create_async_engine(self.database_url, pool_timeout=self.timeout)
            async with engine.connect() as conn:
                await asyncio.wait_for(
                    conn.execute(text("SELECT 1")),
                    timeout=self.timeout,
                )
            latency = (time.perf_counter() - start) * 1000
            await engine.dispose()
            return CheckResult(
                service="postgresql",
                status=ServiceStatus.HEALTHY,
                latency_ms=latency,
                details="Connection successful",
            )
        except TimeoutError:
            return CheckResult(
                service="postgresql",
                status=ServiceStatus.TIMEOUT,
                details=f"Connection timeout after {self.timeout}s",
            )
        except Exception as e:
            return CheckResult(
                service="postgresql",
                status=ServiceStatus.UNHEALTHY,
                details=str(e),
            )


class RedisChecker:
    """Redis connectivity check."""

    def __init__(self, redis_url: str, timeout: float = 2.0):
        self.redis_url = redis_url
        self.timeout = timeout

    async def check(self) -> CheckResult:
        """Check Redis connectivity with PING."""
        from redis.asyncio import Redis

        start = time.perf_counter()
        try:
            client = Redis.from_url(self.redis_url, socket_timeout=self.timeout)
            pong = await asyncio.wait_for(client.ping(), timeout=self.timeout)
            latency = (time.perf_counter() - start) * 1000
            await client.aclose()
            return CheckResult(
                service="redis",
                status=ServiceStatus.HEALTHY if pong else ServiceStatus.UNHEALTHY,
                latency_ms=latency,
                details="PONG received" if pong else "No PONG response",
            )
        except TimeoutError:
            return CheckResult(
                service="redis",
                status=ServiceStatus.TIMEOUT,
                details=f"Connection timeout after {self.timeout}s",
            )
        except Exception as e:
            return CheckResult(
                service="redis",
                status=ServiceStatus.UNHEALTHY,
                details=str(e),
            )


class BackendAPIChecker:
    """Backend API health endpoint check."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 10.0):
        self.base_url = base_url
        self.timeout = timeout

    async def check(self) -> CheckResult:
        """Check backend health endpoint."""
        import httpx

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/health")
                latency = (time.perf_counter() - start) * 1000

                if response.status_code == 200:
                    data = response.json()
                    return CheckResult(
                        service="backend_api",
                        status=ServiceStatus.HEALTHY,
                        latency_ms=latency,
                        details=f"Status: {data.get('status', 'unknown')}",
                    )
                else:
                    return CheckResult(
                        service="backend_api",
                        status=ServiceStatus.UNHEALTHY,
                        latency_ms=latency,
                        details=f"HTTP {response.status_code}",
                    )
        except httpx.TimeoutException:
            return CheckResult(
                service="backend_api",
                status=ServiceStatus.TIMEOUT,
                details=f"Request timeout after {self.timeout}s",
            )
        except httpx.ConnectError:
            return CheckResult(
                service="backend_api",
                status=ServiceStatus.UNHEALTHY,
                details="Connection refused - server not running",
            )
        except Exception as e:
            return CheckResult(
                service="backend_api",
                status=ServiceStatus.UNHEALTHY,
                details=str(e),
            )


class WebSocketChecker:
    """WebSocket connectivity check."""

    def __init__(self, ws_url: str = "ws://localhost:8000/api/v1/ws", timeout: float = 5.0):
        self.ws_url = ws_url
        self.timeout = timeout

    async def check(self) -> CheckResult:
        """Check WebSocket connectivity."""
        try:
            import websockets
        except ImportError:
            return CheckResult(
                service="websocket",
                status=ServiceStatus.SKIPPED,
                details="websockets package not installed",
                critical=False,
            )

        start = time.perf_counter()
        try:
            async with asyncio.timeout(self.timeout):
                async with websockets.connect(self.ws_url) as ws:
                    # Send a ping and wait for pong
                    pong = await ws.ping()
                    await pong
                    latency = (time.perf_counter() - start) * 1000
                    return CheckResult(
                        service="websocket",
                        status=ServiceStatus.HEALTHY,
                        latency_ms=latency,
                        details="WebSocket connection successful",
                    )
        except TimeoutError:
            return CheckResult(
                service="websocket",
                status=ServiceStatus.TIMEOUT,
                details=f"Connection timeout after {self.timeout}s",
            )
        except Exception as e:
            return CheckResult(
                service="websocket",
                status=ServiceStatus.UNHEALTHY,
                details=str(e),
            )


class FrontendChecker:
    """Frontend server check (optional)."""

    def __init__(self, base_url: str = "http://localhost:3000", timeout: float = 10.0):
        self.base_url = base_url
        self.timeout = timeout

    async def check(self) -> CheckResult:
        """Check frontend availability."""
        import httpx

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url)
                latency = (time.perf_counter() - start) * 1000

                return CheckResult(
                    service="frontend",
                    status=(
                        ServiceStatus.HEALTHY
                        if response.status_code < 500
                        else ServiceStatus.UNHEALTHY
                    ),
                    latency_ms=latency,
                    details=f"HTTP {response.status_code}",
                    critical=False,  # Frontend is optional
                )
        except Exception as e:
            return CheckResult(
                service="frontend",
                status=ServiceStatus.UNHEALTHY,
                details=str(e),
                critical=False,
            )


class MigrationChecker:
    """Database migration status check."""

    def __init__(self, backend_dir: str | Path):
        self.backend_dir = Path(backend_dir)

    async def check(self) -> CheckResult:
        """Verify all migrations are applied using alembic current."""
        try:
            result = subprocess.run(
                ["uv", "run", "alembic", "current"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.backend_dir),
            )

            if result.returncode == 0 and "(head)" in result.stdout:
                return CheckResult(
                    service="migrations",
                    status=ServiceStatus.HEALTHY,
                    details="All migrations applied",
                )
            elif result.returncode == 0:
                # Alembic ran but not at head
                return CheckResult(
                    service="migrations",
                    status=ServiceStatus.UNHEALTHY,
                    details=f"Migrations not at head: {result.stdout.strip()}",
                )
            else:
                return CheckResult(
                    service="migrations",
                    status=ServiceStatus.UNHEALTHY,
                    details=f"Alembic error: {result.stderr.strip()}",
                )
        except subprocess.TimeoutExpired:
            return CheckResult(
                service="migrations",
                status=ServiceStatus.TIMEOUT,
                details="Alembic command timed out",
            )
        except FileNotFoundError:
            return CheckResult(
                service="migrations",
                status=ServiceStatus.UNHEALTHY,
                details="uv or alembic not found",
            )
        except Exception as e:
            return CheckResult(
                service="migrations",
                status=ServiceStatus.UNHEALTHY,
                details=str(e),
            )


class PreflightValidator:
    """Main preflight validation orchestrator."""

    def __init__(
        self,
        database_url: str,
        redis_url: str,
        backend_url: str = "http://localhost:8000",
        frontend_url: str = "http://localhost:3000",
        backend_dir: str | Path | None = None,
        backend_only: bool = False,
        check_migrations: bool = True,
        check_websocket: bool = True,
    ):
        self.checkers: list[ServiceChecker] = [
            PostgresChecker(database_url),
            RedisChecker(redis_url),
            BackendAPIChecker(backend_url),
        ]

        if check_websocket:
            # Extract host from backend_url for WebSocket
            ws_host = backend_url.replace("http://", "").replace("https://", "")
            self.checkers.append(WebSocketChecker(f"ws://{ws_host}/api/v1/ws"))

        if check_migrations and backend_dir:
            self.checkers.append(MigrationChecker(backend_dir))

        if not backend_only:
            self.checkers.append(FrontendChecker(frontend_url))

    async def run_checks(self, retry_count: int = 3, retry_delay: float = 2.0) -> PreflightReport:
        """Run all health checks with retry logic."""
        report = PreflightReport()

        for checker in self.checkers:
            result = None
            for attempt in range(retry_count):
                result = await checker.check()
                if result.status == ServiceStatus.HEALTHY:
                    report.results.append(result)
                    break
                elif attempt < retry_count - 1:
                    await asyncio.sleep(retry_delay)
            else:
                # All retries exhausted, add the last result
                if result:
                    report.results.append(result)

        return report

    def print_report(self, report: PreflightReport, verbose: bool = False) -> None:
        """Print formatted report to stdout."""
        print("\n" + "=" * 60)
        print("PRE-FLIGHT SERVICE CHECK REPORT")
        print("=" * 60 + "\n")

        for result in report.results:
            status_icon = {
                ServiceStatus.HEALTHY: "[OK]",
                ServiceStatus.UNHEALTHY: "[FAIL]",
                ServiceStatus.TIMEOUT: "[TIMEOUT]",
                ServiceStatus.SKIPPED: "[SKIP]",
            }[result.status]

            critical_marker = "*" if result.critical else " "
            latency_str = f"{result.latency_ms:.1f}ms" if result.latency_ms > 0 else "-"

            print(f"  {status_icon} {critical_marker}{result.service:<15} {latency_str:<10}")
            if verbose and result.details:
                print(f"       Details: {result.details}")

        print("\n" + "-" * 60)
        if report.is_healthy:
            print("  STATUS: ALL CRITICAL SERVICES HEALTHY")
        else:
            print("  STATUS: CRITICAL SERVICE FAILURES DETECTED")
            for failure in report.critical_failures:
                print(f"    - {failure.service}: {failure.details}")
        print("-" * 60 + "\n")


async def check_services_available(
    database_url: str | None = None,
    redis_url: str | None = None,
    backend_url: str = "http://localhost:8000",
    check_backend_api: bool = True,
    check_websocket: bool = False,
) -> tuple[bool, PreflightReport]:
    """Utility function to check if services are available.

    This is a simplified interface for programmatic use.

    Args:
        database_url: PostgreSQL connection URL (uses settings if None)
        redis_url: Redis connection URL (uses settings if None)
        backend_url: Backend API base URL
        check_backend_api: Whether to check the backend health endpoint
        check_websocket: Whether to check WebSocket connectivity

    Returns:
        Tuple of (is_healthy, report)
    """
    # Import settings here to avoid import errors when module is imported
    try:
        from app.core.config import settings

        database_url = database_url or settings.DATABASE_URL
        redis_url = redis_url or settings.REDIS_URL
    except ImportError as e:
        if not database_url or not redis_url:
            raise ValueError(
                "database_url and redis_url must be provided when settings unavailable"
            ) from e

    checkers: list[ServiceChecker] = [
        PostgresChecker(database_url),
        RedisChecker(redis_url),
    ]

    if check_backend_api:
        checkers.append(BackendAPIChecker(backend_url))

    if check_websocket:
        ws_host = backend_url.replace("http://", "").replace("https://", "")
        checkers.append(WebSocketChecker(f"ws://{ws_host}/api/v1/ws"))

    report = PreflightReport()
    for checker in checkers:
        result = await checker.check()
        report.results.append(result)

    return report.is_healthy, report


async def main() -> None:
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(description="Pre-flight service validator")
    parser.add_argument("--backend-only", action="store_true", help="Skip frontend check")
    parser.add_argument("--wait", type=int, default=30, help="Max wait time for services (seconds)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-migrations", action="store_true", help="Skip migration check")
    parser.add_argument("--no-websocket", action="store_true", help="Skip WebSocket check")
    parser.add_argument("--retries", type=int, default=3, help="Number of retries per service")
    parser.add_argument(
        "--retry-delay", type=float, default=2.0, help="Delay between retries (seconds)"
    )
    args = parser.parse_args()

    # Load from environment/settings
    try:
        from app.core.config import settings

        database_url = settings.DATABASE_URL
        redis_url = settings.REDIS_URL
        backend_dir = settings.BACKEND_DIR
    except ImportError:
        # Fall back to environment variables if settings not available
        postgres_host = os.environ.get("POSTGRES_HOST", "localhost")
        postgres_port = os.environ.get("POSTGRES_PORT", "5432")
        postgres_user = os.environ.get("POSTGRES_USER", "postgres")
        postgres_password = os.environ.get("POSTGRES_PASSWORD", "")
        postgres_db = os.environ.get("POSTGRES_DB", "guilde_lite_tdd_sprint")

        database_url = (
            f"postgresql+asyncpg://{postgres_user}:{postgres_password}"
            f"@{postgres_host}:{postgres_port}/{postgres_db}"
        )

        redis_host = os.environ.get("REDIS_HOST", "localhost")
        redis_port = os.environ.get("REDIS_PORT", "6379")
        redis_url = f"redis://{redis_host}:{redis_port}/0"

        backend_dir = Path(__file__).resolve().parent.parent / "backend"

    validator = PreflightValidator(
        database_url=database_url,
        redis_url=redis_url,
        backend_dir=backend_dir,
        backend_only=args.backend_only,
        check_migrations=not args.no_migrations,
        check_websocket=not args.no_websocket,
    )

    report = await validator.run_checks(
        retry_count=args.retries,
        retry_delay=args.retry_delay,
    )
    validator.print_report(report, verbose=args.verbose)

    sys.exit(0 if report.is_healthy else 1)


if __name__ == "__main__":
    asyncio.run(main())
