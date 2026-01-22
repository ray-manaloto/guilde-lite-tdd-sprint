# Enhanced QA Automation System Design

**Version:** 1.0
**Date:** 2026-01-22
**Author:** QA Automation Engineer Agent

---

## Executive Summary

This document outlines the design for an enhanced QA automation system to address three critical issues:
1. Bugs found manually that should be caught by automation
2. Sprint status not transitioning (planned -> active) correctly
3. Integration tests not validating full system state

The system consists of three major components:
- **Pre-Flight Service Validator**: Ensures all services are running before tests
- **Enhanced Integration Tests**: Full sprint lifecycle validation with WebSocket support
- **TDD Enforcement Framework**: Hooks to verify tests exist before implementation

---

## 1. Pre-Flight Service Validator

### 1.1 Overview

A standalone Python script and pytest plugin that verifies all required services are operational before test execution begins.

### 1.2 Service Check Matrix

| Service | Check Type | Endpoint/Method | Timeout | Critical |
|---------|------------|-----------------|---------|----------|
| PostgreSQL | TCP + Query | `SELECT 1` | 5s | Yes |
| Redis | TCP + PING | `redis-cli PING` | 2s | Yes |
| Backend API | HTTP GET | `/api/v1/health` | 10s | Yes |
| Frontend | HTTP GET | `http://localhost:3000` | 10s | No* |
| WebSocket | WS Connect | `/api/v1/ws` | 5s | Yes |

*Frontend is optional for backend-only tests.

### 1.3 Script Design: `scripts/preflight.py`

```python
#!/usr/bin/env python
"""Pre-flight service validator for integration tests.

Usage:
    uv run python scripts/preflight.py [--backend-only] [--wait SECONDS] [--verbose]

Exit codes:
    0 - All services healthy
    1 - One or more services failed
    2 - Configuration error
"""

import argparse
import asyncio
import socket
import sys
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

import httpx
from redis.asyncio import Redis


class ServiceStatus(StrEnum):
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
        return all(
            r.status == ServiceStatus.HEALTHY
            for r in self.results
            if r.critical
        )

    @property
    def critical_failures(self) -> list[CheckResult]:
        """List of failed critical services."""
        return [
            r for r in self.results
            if r.critical and r.status != ServiceStatus.HEALTHY
        ]


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
        import time
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        start = time.perf_counter()
        try:
            engine = create_async_engine(self.database_url, pool_timeout=self.timeout)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            latency = (time.perf_counter() - start) * 1000
            await engine.dispose()
            return CheckResult(
                service="postgresql",
                status=ServiceStatus.HEALTHY,
                latency_ms=latency,
                details="Connection successful",
            )
        except asyncio.TimeoutError:
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
        import time

        start = time.perf_counter()
        try:
            client = Redis.from_url(self.redis_url, socket_timeout=self.timeout)
            pong = await asyncio.wait_for(client.ping(), timeout=self.timeout)
            latency = (time.perf_counter() - start) * 1000
            await client.close()
            return CheckResult(
                service="redis",
                status=ServiceStatus.HEALTHY if pong else ServiceStatus.UNHEALTHY,
                latency_ms=latency,
                details="PONG received" if pong else "No PONG response",
            )
        except asyncio.TimeoutError:
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
        import time

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
        import time
        import websockets

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
        except asyncio.TimeoutError:
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
        import time

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url)
                latency = (time.perf_counter() - start) * 1000

                return CheckResult(
                    service="frontend",
                    status=ServiceStatus.HEALTHY if response.status_code < 500 else ServiceStatus.UNHEALTHY,
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

    def __init__(self, database_url: str):
        self.database_url = database_url

    async def check(self) -> CheckResult:
        """Verify all migrations are applied."""
        import subprocess

        try:
            result = subprocess.run(
                ["uv", "run", "alembic", "current"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd="backend",
            )

            if result.returncode == 0 and "(head)" in result.stdout:
                return CheckResult(
                    service="migrations",
                    status=ServiceStatus.HEALTHY,
                    details="All migrations applied",
                )
            else:
                return CheckResult(
                    service="migrations",
                    status=ServiceStatus.UNHEALTHY,
                    details=f"Migrations not at head: {result.stdout}",
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
        backend_only: bool = False,
        check_migrations: bool = True,
    ):
        self.checkers: list[ServiceChecker] = [
            PostgresChecker(database_url),
            RedisChecker(redis_url),
            BackendAPIChecker(backend_url),
            WebSocketChecker(f"ws://{backend_url.replace('http://', '')}/api/v1/ws"),
        ]

        if check_migrations:
            self.checkers.append(MigrationChecker(database_url))

        if not backend_only:
            self.checkers.append(FrontendChecker(frontend_url))

    async def run_checks(self, retry_count: int = 3, retry_delay: float = 2.0) -> PreflightReport:
        """Run all health checks with retry logic."""
        report = PreflightReport()

        for checker in self.checkers:
            for attempt in range(retry_count):
                result = await checker.check()
                if result.status == ServiceStatus.HEALTHY:
                    report.results.append(result)
                    break
                elif attempt < retry_count - 1:
                    await asyncio.sleep(retry_delay)
            else:
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


async def main():
    parser = argparse.ArgumentParser(description="Pre-flight service validator")
    parser.add_argument("--backend-only", action="store_true", help="Skip frontend check")
    parser.add_argument("--wait", type=int, default=30, help="Max wait time for services")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-migrations", action="store_true", help="Skip migration check")
    args = parser.parse_args()

    # Load from environment/settings
    from app.core.config import settings

    validator = PreflightValidator(
        database_url=settings.DATABASE_URL,
        redis_url=settings.REDIS_URL,
        backend_only=args.backend_only,
        check_migrations=not args.no_migrations,
    )

    report = await validator.run_checks()
    validator.print_report(report, verbose=args.verbose)

    sys.exit(0 if report.is_healthy else 1)


if __name__ == "__main__":
    asyncio.run(main())
```

### 1.4 Pytest Plugin: `conftest.py` Integration

```python
# backend/tests/conftest.py - Add preflight fixture

import pytest
from scripts.preflight import PreflightValidator, PreflightReport

@pytest.fixture(scope="session")
async def preflight_check() -> PreflightReport:
    """Session-scoped preflight check for integration tests.

    Runs once at the start of the test session and fails fast
    if critical services are unavailable.
    """
    from app.core.config import settings

    validator = PreflightValidator(
        database_url=settings.DATABASE_URL,
        redis_url=settings.REDIS_URL,
        backend_only=True,  # Unit tests don't need frontend
    )

    report = await validator.run_checks()

    if not report.is_healthy:
        failures = ", ".join(f.service for f in report.critical_failures)
        pytest.fail(f"Pre-flight check failed: {failures}")

    return report


@pytest.fixture(scope="session")
def require_live_services(preflight_check: PreflightReport):
    """Marker fixture that requires live services for integration tests."""
    return preflight_check
```

### 1.5 CLI Integration with devctl.sh

```bash
# Add to scripts/devctl.sh

preflight() {
  echo "Running pre-flight service checks..."
  cd "${ROOT_DIR}/backend"
  uv run python scripts/preflight.py "$@"
}

case "${cmd}" in
  # ... existing cases ...
  preflight)
    preflight "${@:2}"
    ;;
esac
```

---

## 2. Enhanced Integration Tests

### 2.1 Sprint Lifecycle Test Suite

This test suite validates the complete sprint lifecycle including status transitions.

**File:** `backend/tests/integration/test_sprint_lifecycle.py`

```python
"""Sprint lifecycle integration tests.

Tests the complete sprint workflow from creation through completion,
validating all status transitions and WebSocket updates.
"""

import asyncio
import json
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.db.models.sprint import SprintStatus


class TestSprintLifecycle:
    """Test suite for sprint lifecycle state machine."""

    @pytest.fixture
    async def live_client(self):
        """Client connected to live running server."""
        async with AsyncClient(
            base_url="http://localhost:8000",
            timeout=10.0,
        ) as client:
            yield client

    @pytest.fixture
    async def websocket_client(self):
        """WebSocket client for real-time updates."""
        import websockets

        async with websockets.connect(
            "ws://localhost:8000/api/v1/ws"
        ) as ws:
            yield ws

    @pytest.mark.anyio
    @pytest.mark.integration
    async def test_sprint_status_transitions(self, live_client: AsyncClient):
        """
        TC-001: Sprint Status State Machine

        Validates: planned -> active -> completed transitions
        Priority: High

        Preconditions:
        - Backend server running
        - Database accessible

        Expected Flow:
        1. Create sprint (status = planned)
        2. PhaseRunner starts (status -> active)
        3. Phases complete (status -> completed)
        """
        # 1. Create Sprint - Should be "planned"
        response = await live_client.post(
            f"{settings.API_V1_STR}/sprints",
            json={
                "name": "Lifecycle Test Sprint",
                "goal": "Create a python script that prints 'test'",
            },
        )
        assert response.status_code == 201
        sprint_data = response.json()
        sprint_id = sprint_data["id"]

        # Verify initial status
        assert sprint_data["status"] == "planned", (
            f"Expected initial status 'planned', got '{sprint_data['status']}'"
        )

        # 2. Poll for ACTIVE status (PhaseRunner should update this)
        active_found = False
        for _ in range(30):  # 30 seconds max
            await asyncio.sleep(1)
            response = await live_client.get(
                f"{settings.API_V1_STR}/sprints/{sprint_id}"
            )
            data = response.json()

            if data["status"] == "active":
                active_found = True
                break
            elif data["status"] == "completed":
                # Went straight to completed (fast task)
                active_found = True
                break

        assert active_found, (
            f"Sprint never transitioned to 'active'. "
            f"Current status: {data['status']}"
        )

        # 3. Poll for COMPLETED status
        completed_found = False
        for _ in range(180):  # 3 minutes max
            await asyncio.sleep(1)
            response = await live_client.get(
                f"{settings.API_V1_STR}/sprints/{sprint_id}"
            )
            data = response.json()

            if data["status"] == "completed":
                completed_found = True
                break
            elif data["status"] == "failed":
                pytest.fail(f"Sprint failed instead of completing")

        assert completed_found, (
            f"Sprint never reached 'completed'. "
            f"Final status: {data['status']}"
        )

    @pytest.mark.anyio
    @pytest.mark.integration
    async def test_websocket_status_updates(
        self, live_client: AsyncClient, websocket_client
    ):
        """
        TC-002: WebSocket Real-Time Updates

        Validates: WebSocket broadcasts sprint status changes
        Priority: High

        Expected:
        - Receive sprint_update messages
        - Status changes reflected in real-time
        - Phase transitions broadcast correctly
        """
        # Create sprint
        response = await live_client.post(
            f"{settings.API_V1_STR}/sprints",
            json={
                "name": "WebSocket Test Sprint",
                "goal": "Create hello.py",
            },
        )
        sprint_id = response.json()["id"]

        # Subscribe to sprint room
        await websocket_client.send(json.dumps({
            "type": "subscribe",
            "room": sprint_id,
        }))

        # Collect status updates
        statuses_received = []
        phases_received = []

        try:
            async with asyncio.timeout(120):  # 2 minute timeout
                while True:
                    message = await websocket_client.recv()
                    data = json.loads(message)

                    if data.get("type") == "sprint_update":
                        statuses_received.append(data.get("status"))
                        if data.get("phase"):
                            phases_received.append(data.get("phase"))

                        if data.get("status") in ("completed", "failed"):
                            break
        except asyncio.TimeoutError:
            pass  # Continue with validation

        # Validate we received status updates
        assert "active" in statuses_received, (
            f"Never received 'active' status. Got: {statuses_received}"
        )

        # Validate phase progression
        expected_phases = ["init", "discovery", "coding", "verification"]
        for phase in expected_phases:
            assert any(phase in p for p in phases_received), (
                f"Missing phase '{phase}' in broadcasts. Got: {phases_received}"
            )

    @pytest.mark.anyio
    @pytest.mark.integration
    async def test_sprint_failure_status(self, live_client: AsyncClient):
        """
        TC-003: Sprint Failure Handling

        Validates: Sprint status set to 'failed' on unrecoverable errors
        Priority: Medium

        Expected:
        - Invalid tasks result in 'failed' status after retries
        - Error details available via API
        """
        response = await live_client.post(
            f"{settings.API_V1_STR}/sprints",
            json={
                "name": "Failure Test Sprint",
                # Impossible task that should fail verification
                "goal": "Create a perpetual motion machine simulator that outputs infinite energy",
            },
        )
        sprint_id = response.json()["id"]

        # Wait for failure (max retries exhausted)
        final_status = None
        for _ in range(240):  # 4 minutes max
            await asyncio.sleep(1)
            response = await live_client.get(
                f"{settings.API_V1_STR}/sprints/{sprint_id}"
            )
            data = response.json()
            final_status = data["status"]

            if final_status in ("completed", "failed"):
                break

        # We expect either completed (AI figured it out) or failed
        assert final_status in ("completed", "failed"), (
            f"Sprint stuck in status: {final_status}"
        )
```

### 2.2 API Contract Validation Tests

**File:** `backend/tests/integration/test_api_contracts.py`

```python
"""API contract validation tests.

Validates API responses match expected schemas and business rules.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from pydantic import ValidationError

from app.main import app
from app.schemas.sprint import SprintRead, SprintReadWithItems


class TestSprintAPIContracts:
    """API contract tests for sprint endpoints."""

    @pytest.fixture
    async def client(self, db_session):
        """Client with real database."""
        from app.api.deps import get_db_session

        app.dependency_overrides[get_db_session] = lambda: db_session

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client

        app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_create_sprint_response_schema(self, client: AsyncClient):
        """
        TC-010: Create Sprint Response Schema

        Validates: POST /sprints returns valid SprintRead schema
        """
        response = await client.post(
            "/api/v1/sprints",
            json={
                "name": "Schema Test Sprint",
                "goal": "Test goal",
            },
        )

        assert response.status_code == 201

        # Validate against Pydantic schema
        try:
            sprint = SprintRead.model_validate(response.json())
        except ValidationError as e:
            pytest.fail(f"Response does not match SprintRead schema: {e}")

        # Business rule validations
        assert sprint.status == "planned", "New sprint must have 'planned' status"
        assert sprint.name == "Schema Test Sprint"
        assert sprint.id is not None

    @pytest.mark.anyio
    async def test_get_sprint_includes_items(self, client: AsyncClient):
        """
        TC-011: Get Sprint Response Includes Items

        Validates: GET /sprints/{id} returns items array
        """
        # Create sprint
        create_response = await client.post(
            "/api/v1/sprints",
            json={"name": "Items Test Sprint", "goal": "Test"},
        )
        sprint_id = create_response.json()["id"]

        # Get sprint with items
        response = await client.get(f"/api/v1/sprints/{sprint_id}")

        assert response.status_code == 200

        # Validate against schema with items
        try:
            sprint = SprintReadWithItems.model_validate(response.json())
        except ValidationError as e:
            pytest.fail(f"Response does not match SprintReadWithItems schema: {e}")

        assert hasattr(sprint, "items")
        assert isinstance(sprint.items, list)

    @pytest.mark.anyio
    async def test_list_sprints_pagination(self, client: AsyncClient):
        """
        TC-012: List Sprints Pagination

        Validates: GET /sprints returns paginated response
        """
        response = await client.get("/api/v1/sprints")

        assert response.status_code == 200
        data = response.json()

        # Pagination fields required
        assert "items" in data, "Missing 'items' in paginated response"
        assert "total" in data, "Missing 'total' in paginated response"
        assert "page" in data, "Missing 'page' in paginated response"
        assert "size" in data, "Missing 'size' in paginated response"

    @pytest.mark.anyio
    @pytest.mark.parametrize("status_filter", ["planned", "active", "completed"])
    async def test_list_sprints_status_filter(
        self, client: AsyncClient, status_filter: str
    ):
        """
        TC-013: List Sprints Status Filter

        Validates: GET /sprints?status={filter} filters correctly
        """
        response = await client.get(
            f"/api/v1/sprints?status={status_filter}"
        )

        assert response.status_code == 200
        data = response.json()

        # All returned items should match filter
        for item in data["items"]:
            assert item["status"] == status_filter, (
                f"Item status '{item['status']}' does not match filter '{status_filter}'"
            )
```

### 2.3 Database State Validation Helpers

**File:** `backend/tests/integration/helpers/db_validators.py`

```python
"""Database state validation helpers for integration tests."""

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.sprint import Sprint, SprintStatus
from app.db.models.agent_run import AgentRun, AgentCandidate, AgentDecision


@dataclass
class SprintStateSnapshot:
    """Snapshot of sprint database state for validation."""

    sprint_id: UUID
    status: SprintStatus
    run_count: int = 0
    candidate_count: int = 0
    decision_count: int = 0
    has_workspace_ref: bool = False
    phases_executed: list[str] = field(default_factory=list)


class DatabaseStateValidator:
    """Helper for validating database state in integration tests."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_sprint_state(self, sprint_id: UUID) -> SprintStateSnapshot:
        """Get current sprint state from database."""
        # Get sprint
        sprint = await self.db.get(Sprint, sprint_id)
        if not sprint:
            raise ValueError(f"Sprint {sprint_id} not found")

        # Count runs for this sprint
        run_query = select(func.count(AgentRun.id)).where(
            AgentRun.metadata["sprint_id"].astext == str(sprint_id)
        )
        run_count = (await self.db.execute(run_query)).scalar() or 0

        # Get phases executed
        phases_query = select(AgentRun.metadata["phase"].astext).where(
            AgentRun.metadata["sprint_id"].astext == str(sprint_id)
        ).distinct()
        phases = (await self.db.execute(phases_query)).scalars().all()

        # Check workspace ref
        workspace_query = select(AgentRun.workspace_ref).where(
            AgentRun.metadata["sprint_id"].astext == str(sprint_id),
            AgentRun.workspace_ref.isnot(None),
        ).limit(1)
        workspace_ref = (await self.db.execute(workspace_query)).scalar()

        return SprintStateSnapshot(
            sprint_id=sprint_id,
            status=sprint.status,
            run_count=run_count,
            phases_executed=list(phases),
            has_workspace_ref=workspace_ref is not None,
        )

    async def assert_sprint_completed(
        self,
        sprint_id: UUID,
        expected_phases: list[str] | None = None,
    ) -> SprintStateSnapshot:
        """Assert sprint reached completed state with all phases."""
        state = await self.get_sprint_state(sprint_id)

        assert state.status == SprintStatus.COMPLETED, (
            f"Sprint status is '{state.status}', expected 'completed'"
        )

        if expected_phases:
            for phase in expected_phases:
                assert any(phase in p for p in state.phases_executed), (
                    f"Phase '{phase}' not executed. Got: {state.phases_executed}"
                )

        assert state.run_count > 0, "No agent runs recorded for sprint"
        assert state.has_workspace_ref, "No workspace_ref set for sprint runs"

        return state

    async def assert_sprint_active(self, sprint_id: UUID) -> SprintStateSnapshot:
        """Assert sprint is in active state."""
        state = await self.get_sprint_state(sprint_id)

        assert state.status == SprintStatus.ACTIVE, (
            f"Sprint status is '{state.status}', expected 'active'"
        )

        return state


# Pytest fixture
@pytest.fixture
def db_validator(db_session) -> DatabaseStateValidator:
    """Provide database state validator."""
    return DatabaseStateValidator(db_session)
```

---

## 3. TDD Enforcement Framework

### 3.1 Pre-Commit Hook Design

**File:** `.git/hooks/pre-commit` (or via pre-commit framework)

```bash
#!/bin/bash
# TDD Enforcement Pre-Commit Hook
#
# Validates:
# 1. Test files exist for new/modified implementation files
# 2. Test coverage meets minimum threshold
# 3. Tests pass before commit

set -e

echo "Running TDD enforcement checks..."

# Get list of staged Python files
STAGED_PY_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)

if [ -z "$STAGED_PY_FILES" ]; then
    echo "No Python files staged. Skipping TDD checks."
    exit 0
fi

# Check for test files corresponding to implementation files
check_test_exists() {
    local impl_file=$1

    # Skip test files themselves
    if [[ $impl_file == *"test_"* ]] || [[ $impl_file == *"_test.py" ]]; then
        return 0
    fi

    # Skip non-implementation directories
    if [[ $impl_file != backend/app/* ]] && [[ $impl_file != frontend/src/* ]]; then
        return 0
    fi

    # Determine expected test file location
    local test_file=""
    if [[ $impl_file == backend/app/* ]]; then
        # backend/app/services/foo.py -> backend/tests/unit/test_foo.py or backend/tests/test_foo.py
        local basename=$(basename $impl_file .py)
        test_file="backend/tests/**/test_${basename}.py"
    fi

    if [ -n "$test_file" ]; then
        if ! ls $test_file 1> /dev/null 2>&1; then
            echo "WARNING: No test file found for $impl_file"
            echo "  Expected: $test_file"
            return 1
        fi
    fi

    return 0
}

# Track warnings (don't fail on missing tests in first pass)
WARNINGS=0

for file in $STAGED_PY_FILES; do
    if ! check_test_exists "$file"; then
        WARNINGS=$((WARNINGS + 1))
    fi
done

if [ $WARNINGS -gt 0 ]; then
    echo ""
    echo "TDD Warning: $WARNINGS file(s) missing corresponding tests."
    echo "Consider writing tests before implementation (TDD)."
    # Optionally fail here: exit 1
fi

# Run affected tests
echo "Running tests for staged files..."
cd backend

# Get test files to run
TEST_FILES=""
for file in $STAGED_PY_FILES; do
    if [[ $file == *"test_"* ]]; then
        TEST_FILES="$TEST_FILES $file"
    fi
done

if [ -n "$TEST_FILES" ]; then
    uv run pytest $TEST_FILES -v --tb=short
fi

echo "TDD checks passed!"
```

### 3.2 Coverage Gate Configuration

**File:** `backend/pyproject.toml` (additions)

```toml
[tool.pytest.ini_options]
# ... existing config ...
addopts = "--cov=app --cov-report=term-missing --cov-fail-under=80"

[tool.coverage.run]
branch = true
source = ["app"]
omit = [
    "app/db/migrations/*",
    "app/commands/*",
    "**/conftest.py",
]

[tool.coverage.report]
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]
```

### 3.3 CI/CD Integration

**File:** `.github/workflows/test.yml`

```yaml
name: Test Suite

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  preflight:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: guilde_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        working-directory: backend
        run: uv sync

      - name: Run migrations
        working-directory: backend
        run: uv run alembic upgrade head
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: guilde_test

      - name: Run pre-flight checks
        working-directory: backend
        run: uv run python scripts/preflight.py --backend-only --no-migrations
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PASSWORD: postgres
          REDIS_URL: redis://localhost:6379

  unit-tests:
    needs: preflight
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        working-directory: backend
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          uv sync

      - name: Run unit tests with coverage
        working-directory: backend
        run: |
          uv run pytest tests/unit tests/api \
            --cov=app \
            --cov-report=xml \
            --cov-fail-under=80

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: backend/coverage.xml
          fail_ci_if_error: true

  integration-tests:
    needs: unit-tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: guilde_test
        ports:
          - 5432:5432
      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        working-directory: backend
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          uv sync

      - name: Run migrations
        working-directory: backend
        run: uv run alembic upgrade head
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PASSWORD: postgres

      - name: Start backend server
        working-directory: backend
        run: |
          uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
          sleep 5
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PASSWORD: postgres
          REDIS_URL: redis://localhost:6379
          PLANNING_INTERVIEW_MODE: stub

      - name: Run integration tests
        working-directory: backend
        run: |
          uv run pytest tests/integration \
            -v \
            --tb=short \
            -m "not slow"
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PASSWORD: postgres

  e2e-tests:
    needs: integration-tests
    runs-on: ubuntu-latest
    # ... (frontend E2E config)
```

### 3.4 Mutation Testing Integration (Optional)

**File:** `backend/mutmut_config.py`

```python
"""Mutation testing configuration."""

def pre_mutation(context):
    """Skip mutations in test files and migrations."""
    if "test_" in context.filename:
        context.skip = True
    if "migrations" in context.filename:
        context.skip = True

def init():
    """Initialize mutation testing."""
    return {
        "paths_to_mutate": "app/",
        "runner": "pytest",
        "tests_dir": "tests/",
    }
```

---

## 4. Implementation Plan

### 4.1 Phase 1: Pre-Flight Validator (Week 1)

| Task | Effort | Priority |
|------|--------|----------|
| Create `scripts/preflight.py` | 4h | P0 |
| Add pytest fixture integration | 2h | P0 |
| Integrate with `devctl.sh` | 1h | P1 |
| Write unit tests for validators | 2h | P1 |

### 4.2 Phase 2: Enhanced Integration Tests (Week 2)

| Task | Effort | Priority |
|------|--------|----------|
| Create `test_sprint_lifecycle.py` | 4h | P0 |
| Create `test_api_contracts.py` | 3h | P0 |
| Add WebSocket test support | 2h | P1 |
| Database state validators | 2h | P1 |

### 4.3 Phase 3: TDD Enforcement (Week 3)

| Task | Effort | Priority |
|------|--------|----------|
| Pre-commit hook setup | 2h | P1 |
| Coverage gate configuration | 1h | P0 |
| CI/CD workflow updates | 3h | P0 |
| Documentation updates | 2h | P2 |

---

## 5. Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Test Coverage | ~60% | 80%+ | pytest-cov |
| Sprint Status Bug Detection | Manual | Automated | Integration tests |
| Pre-flight Check Time | N/A | <30s | Script timing |
| False Positive Rate | N/A | <5% | Test reliability tracking |
| CI Pipeline Time | ~5min | <10min | GitHub Actions |

---

## 6. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Flaky integration tests | High | Add retry logic, use deterministic fixtures |
| Slow CI pipeline | Medium | Parallel test execution, caching |
| Over-mocking hides bugs | High | Balance unit/integration test ratio |
| WebSocket tests timing | Medium | Use async timeouts with generous buffers |

---

## Appendix A: Test Markers

```python
# pytest markers for test categorization
pytest.mark.unit        # Fast, isolated unit tests
pytest.mark.integration # Requires database/services
pytest.mark.e2e         # Full system end-to-end
pytest.mark.slow        # Tests > 30 seconds
pytest.mark.websocket   # WebSocket-specific tests
pytest.mark.api         # API contract tests
```

---

## Appendix B: File Summary

| File | Purpose |
|------|---------|
| `scripts/preflight.py` | Pre-flight service validator |
| `backend/tests/integration/test_sprint_lifecycle.py` | Sprint lifecycle tests |
| `backend/tests/integration/test_api_contracts.py` | API schema validation |
| `backend/tests/integration/helpers/db_validators.py` | Database state helpers |
| `.github/workflows/test.yml` | CI/CD test pipeline |
| `backend/pyproject.toml` | Coverage configuration |
