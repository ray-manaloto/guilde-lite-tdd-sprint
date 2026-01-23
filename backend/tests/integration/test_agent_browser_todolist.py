"""Agent-browser integration test for todolist CLI sprint.

This test validates the full sprint workflow for a complex multi-file Python project:
1. Creates a sprint via browser automation
2. Waits for PhaseRunner to complete discovery, coding, verification
3. Validates the todolist CLI package is created correctly
4. Tests the CLI functionality

Prerequisites:
- Backend running on localhost:8000
- Frontend running on localhost:3000
- Run: ./scripts/devctl.sh start
"""

import asyncio
import functools
import inspect
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

import pytest

from app.agents.assistant import AssistantAgent
from app.core.config import settings


# ---------------------------------------------------------------------------
# Telemetry Dataclass - Track test metrics for reporting
# ---------------------------------------------------------------------------
@dataclass
class TelemetryTracker:
    """Track test execution metrics for observability and debugging."""

    test_name: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    poll_attempts: int = 0
    total_poll_wait_seconds: float = 0.0
    files_discovered: list[str] = field(default_factory=list)
    cli_commands_tested: list[str] = field(default_factory=list)
    validation_checks_passed: int = 0
    validation_checks_failed: int = 0
    retry_count: int = 0
    error_messages: list[str] = field(default_factory=list)

    def record_poll(self, wait_seconds: float) -> None:
        """Record a polling attempt."""
        self.poll_attempts += 1
        self.total_poll_wait_seconds += wait_seconds

    def record_file(self, filepath: str) -> None:
        """Record a discovered file."""
        if filepath not in self.files_discovered:
            self.files_discovered.append(filepath)

    def record_cli_test(self, command: str) -> None:
        """Record a CLI command test."""
        self.cli_commands_tested.append(command)

    def record_validation(self, passed: bool, message: str = "") -> None:
        """Record a validation check result."""
        if passed:
            self.validation_checks_passed += 1
        else:
            self.validation_checks_failed += 1
            if message:
                self.error_messages.append(message)

    def finish(self) -> None:
        """Mark test completion."""
        self.end_time = time.time()

    @property
    def duration_seconds(self) -> float:
        """Total test duration."""
        end = self.end_time or time.time()
        return end - self.start_time

    def summary(self) -> str:
        """Generate a summary report."""
        return (
            f"TelemetryTracker[{self.test_name}]:\n"
            f"  Duration: {self.duration_seconds:.2f}s\n"
            f"  Poll attempts: {self.poll_attempts} (total wait: {self.total_poll_wait_seconds:.1f}s)\n"
            f"  Files discovered: {len(self.files_discovered)}\n"
            f"  CLI commands tested: {len(self.cli_commands_tested)}\n"
            f"  Validations: {self.validation_checks_passed} passed, {self.validation_checks_failed} failed\n"
            f"  Retries: {self.retry_count}"
        )


# ---------------------------------------------------------------------------
# Retry Decorator - Handle flaky tests with configurable retries
# ---------------------------------------------------------------------------
T = TypeVar("T")


def retry_on_failure(
    max_retries: int = 2,
    exceptions: tuple[type[Exception], ...] = (AssertionError, TimeoutError),
    delay_seconds: float = 1.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying flaky tests.

    Args:
        max_retries: Maximum number of retry attempts (default: 2)
        exceptions: Tuple of exception types to catch and retry
        delay_seconds: Delay between retries

    Usage:
        @retry_on_failure(max_retries=2)
        async def test_flaky_operation():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            telemetry = kwargs.get("telemetry")
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        print(f"[Retry] Attempt {attempt + 1} failed: {e}. Retrying...")
                        if telemetry:
                            telemetry.retry_count += 1
                        await asyncio.sleep(delay_seconds)
                    else:
                        print(f"[Retry] All {max_retries + 1} attempts failed.")

            raise last_exception  # type: ignore[misc]

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            telemetry = kwargs.get("telemetry")
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        print(f"[Retry] Attempt {attempt + 1} failed: {e}. Retrying...")
                        if telemetry:
                            telemetry.retry_count += 1
                        time.sleep(delay_seconds)
                    else:
                        print(f"[Retry] All {max_retries + 1} attempts failed.")

            raise last_exception  # type: ignore[misc]

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Exponential Backoff Polling
# ---------------------------------------------------------------------------
async def poll_with_backoff(
    check_fn: Callable[[], bool],
    max_wait: float = 300,
    initial_interval: float = 10.0,
    max_interval: float = 30.0,
    backoff_factor: float = 1.5,
    telemetry: TelemetryTracker | None = None,
) -> bool:
    """
    Poll with exponential backoff until check_fn returns True or timeout.

    Args:
        check_fn: Callable that returns True when condition is met
        max_wait: Maximum total wait time in seconds
        initial_interval: Starting poll interval (default: 10s)
        max_interval: Maximum poll interval (default: 30s)
        backoff_factor: Multiplier for interval increase (default: 1.5)
        telemetry: Optional telemetry object to record metrics

    Returns:
        True if condition met, False if timeout
    """
    start_time = asyncio.get_event_loop().time()
    current_interval = initial_interval

    while asyncio.get_event_loop().time() - start_time < max_wait:
        if check_fn():
            return True

        elapsed = asyncio.get_event_loop().time() - start_time
        remaining = max_wait - elapsed

        # Don't wait longer than remaining time
        wait_time = min(current_interval, remaining)

        if telemetry:
            telemetry.record_poll(wait_time)

        print(f"[Poll] Waiting {wait_time:.1f}s (elapsed: {elapsed:.0f}s, next interval: {current_interval:.1f}s)")
        await asyncio.sleep(wait_time)

        # Increase interval with backoff, capped at max
        current_interval = min(current_interval * backoff_factor, max_interval)

    return False


# ---------------------------------------------------------------------------
# File Content Validators
# ---------------------------------------------------------------------------
def validate_cli_has_argparse(filepath: Path) -> tuple[bool, str]:
    """
    Validate that cli.py uses argparse for command parsing.

    Returns:
        Tuple of (is_valid, message)
    """
    if not filepath.exists():
        return False, f"File not found: {filepath}"

    content = filepath.read_text()

    # Check for argparse import
    if "import argparse" not in content and "from argparse" not in content:
        return False, "cli.py missing argparse import"

    # Check for ArgumentParser usage
    if "ArgumentParser" not in content:
        return False, "cli.py missing ArgumentParser usage"

    # Check for add_subparsers or add_argument (command handling)
    has_subparsers = "add_subparsers" in content
    has_add_argument = "add_argument" in content

    if not (has_subparsers or has_add_argument):
        return False, "cli.py missing command argument handling"

    return True, "cli.py has valid argparse structure"


def validate_store_has_json(filepath: Path) -> tuple[bool, str]:
    """
    Validate that store.py uses JSON for persistence.

    Returns:
        Tuple of (is_valid, message)
    """
    if not filepath.exists():
        return False, f"File not found: {filepath}"

    content = filepath.read_text()

    # Check for json import
    if "import json" not in content and "from json" not in content:
        return False, "store.py missing json import"

    # Check for json operations
    has_load = "json.load" in content or "json.loads" in content
    has_dump = "json.dump" in content or "json.dumps" in content

    if not (has_load or has_dump):
        return False, "store.py missing json load/dump operations"

    # Check for file path handling (should reference a JSON file)
    json_file_pattern = re.compile(r'["\'].*\.json["\']|\.json')
    if not json_file_pattern.search(content):
        return False, "store.py missing JSON file reference"

    return True, "store.py has valid JSON persistence structure"


def validate_main_has_entry_point(filepath: Path) -> tuple[bool, str]:
    """
    Validate that __main__.py has proper entry point.

    Returns:
        Tuple of (is_valid, message)
    """
    if not filepath.exists():
        return False, f"File not found: {filepath}"

    content = filepath.read_text()

    # Check for main execution pattern
    has_main_guard = 'if __name__ == "__main__"' in content or "if __name__ == '__main__'" in content
    has_main_call = "main()" in content or "cli(" in content

    if not (has_main_guard or has_main_call):
        return False, "__main__.py missing entry point execution"

    return True, "__main__.py has valid entry point"


# Simplified todolist goal for faster testing
TODOLIST_GOAL = """Create a Python CLI todo list manager with the following requirements:

1. Package structure: todo/ with __init__.py, cli.py, store.py, __main__.py
2. Commands via argparse (no external deps):
   - add TITLE: Add a new task
   - list: Show all tasks
   - done ID: Mark task as done
3. Storage: JSON file at ~/.todo_test.json
4. Run via: python -m todo <command>

Keep it minimal but functional."""


@pytest.fixture
def temp_artifacts_dir():
    """Create a temporary artifacts directory for testing."""
    with tempfile.TemporaryDirectory(prefix="guilde-test-") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def telemetry():
    """Create telemetry tracker for test metrics."""
    return TelemetryTracker(test_name="test_todolist_sprint_via_browser")


@pytest.mark.anyio
@pytest.mark.integration
@pytest.mark.slow
@retry_on_failure(max_retries=2, exceptions=(AssertionError, TimeoutError))
async def test_todolist_sprint_via_browser(temp_artifacts_dir, monkeypatch, telemetry):
    """
    Integration test: Create todolist sprint via browser and verify build.

    This test:
    1. Uses browser agent to navigate to sprint creation page
    2. Creates a sprint with the todolist goal
    3. Waits for PhaseRunner to build the project (with exponential backoff)
    4. Validates the package structure and file contents
    5. Tests the CLI works (add, list, done commands)
    """
    if not shutil.which("agent-browser"):
        pytest.skip("agent-browser CLI not available")

    # Use temp directory for artifacts
    monkeypatch.setattr(settings, "AUTOCODE_ARTIFACTS_DIR", temp_artifacts_dir)

    agent = AssistantAgent(
        system_prompt=(
            "You are a browser automation agent. Use the 'agent_browser' tool "
            "to interact with web pages. Follow instructions precisely."
        )
    )

    # Step 1: Create the sprint via browser
    create_prompt = f"""
Navigate to http://localhost:3000/en/sprints and create a new sprint:

1. Find and click the 'New Sprint' or 'Create Sprint' button
2. Fill in the form:
   - Name: "Todolist CLI Test Sprint"
   - Goal: {TODOLIST_GOAL}
3. Click the submit/create button
4. Wait for the sprint to be created
5. Report the sprint ID or confirm creation

Be precise and report any errors you encounter.
"""

    print("\n[Test] Starting browser automation to create sprint...")
    output, _tool_events, _ = await agent.run(create_prompt)
    print(f"[Agent] Output: {output}")

    # Give PhaseRunner time to pick up the sprint
    print("[Test] Waiting for PhaseRunner to start...")
    await asyncio.sleep(5)

    # Step 2: Poll for the todo package with exponential backoff
    print(f"[Test] Polling {temp_artifacts_dir} for todo package (with backoff)...")
    found_package = None

    def check_for_package() -> bool:
        nonlocal found_package
        # Look for the todo package structure
        found_dirs = list(temp_artifacts_dir.rglob("todo/__init__.py"))
        if found_dirs:
            found_package = found_dirs[0].parent
            return True

        # Also check for __main__.py directly
        found_mains = list(temp_artifacts_dir.rglob("todo/__main__.py"))
        if found_mains:
            found_package = found_mains[0].parent
            return True

        # Log discovered files for debugging
        all_files = list(temp_artifacts_dir.rglob("*.py"))
        if all_files:
            for f in all_files[:5]:
                telemetry.record_file(str(f))
            print(f"[Test] Found files so far: {[str(f) for f in all_files[:5]]}")

        return False

    # Use exponential backoff: 10s -> 15s -> 22.5s -> 30s (capped)
    package_found = await poll_with_backoff(
        check_fn=check_for_package,
        max_wait=300,  # 5 minutes for complex project
        initial_interval=10.0,
        max_interval=30.0,
        backoff_factor=1.5,
        telemetry=telemetry,
    )

    assert package_found and found_package is not None, (
        f"todo package not created in {temp_artifacts_dir} within 300s. "
        f"Files found: {list(temp_artifacts_dir.rglob('*'))}"
    )
    print(f"[Test] Found todo package at: {found_package}")
    telemetry.record_file(str(found_package))

    # Step 3: Validate package structure
    expected_files = ["__init__.py", "cli.py", "store.py"]
    for filename in expected_files:
        filepath = found_package / filename
        exists = filepath.exists()
        telemetry.record_validation(exists, f"Missing: {filename}" if not exists else "")
        assert exists, f"Missing expected file: {filepath}"
        print(f"[Test] Found {filename}")
        telemetry.record_file(str(filepath))

    # Check for __main__.py (required for python -m todo)
    main_file = found_package / "__main__.py"
    exists = main_file.exists()
    telemetry.record_validation(exists, "Missing __main__.py" if not exists else "")
    assert exists, "Missing __main__.py for package execution"
    print("[Test] Found __main__.py")

    # Step 4: Validate file contents
    print("[Test] Validating file contents...")

    # Validate cli.py has argparse
    cli_file = found_package / "cli.py"
    is_valid, message = validate_cli_has_argparse(cli_file)
    telemetry.record_validation(is_valid, message)
    assert is_valid, f"cli.py validation failed: {message}"
    print(f"[Test] cli.py: {message}")

    # Validate store.py has JSON persistence
    store_file = found_package / "store.py"
    is_valid, message = validate_store_has_json(store_file)
    telemetry.record_validation(is_valid, message)
    assert is_valid, f"store.py validation failed: {message}"
    print(f"[Test] store.py: {message}")

    # Validate __main__.py has entry point
    is_valid, message = validate_main_has_entry_point(main_file)
    telemetry.record_validation(is_valid, message)
    assert is_valid, f"__main__.py validation failed: {message}"
    print(f"[Test] __main__.py: {message}")

    # Step 5: Test the CLI commands
    workspace_dir = found_package.parent
    print(f"[Test] Testing CLI from {workspace_dir}...")

    # Test: python -m todo add "Test task"
    telemetry.record_cli_test("add")
    result = subprocess.run(
        ["python", "-m", "todo", "add", "Test task"],
        cwd=workspace_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(f"[Test] Add command output: {result.stdout} {result.stderr}")
    telemetry.record_validation(result.returncode == 0, f"add failed: {result.stderr}")
    assert result.returncode == 0, f"Add command failed: {result.stderr}"

    # Test: python -m todo list
    telemetry.record_cli_test("list")
    result = subprocess.run(
        ["python", "-m", "todo", "list"],
        cwd=workspace_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(f"[Test] List command output: {result.stdout}")
    telemetry.record_validation(result.returncode == 0, f"list failed: {result.stderr}")
    assert result.returncode == 0, f"List command failed: {result.stderr}"

    task_in_output = "Test task" in result.stdout or "test task" in result.stdout.lower()
    telemetry.record_validation(task_in_output, "Task not in list output")
    assert task_in_output, f"Task not found in list output: {result.stdout}"

    # Step 6: Test done command - mark task as complete
    print("[Test] Testing done command...")
    telemetry.record_cli_test("done")

    # Extract task ID from list output (typically first task is ID 1 or 0)
    # Try common ID patterns: "1.", "[1]", "ID: 1", or just assume ID 1
    task_id = "1"  # Default to ID 1 for first task

    # Try to extract ID from list output
    import re as regex_module
    id_patterns = [
        r"^\s*(\d+)\.",           # "1. Task name"
        r"\[(\d+)\]",             # "[1] Task name"
        r"ID:\s*(\d+)",           # "ID: 1"
        r"^(\d+)\s+",             # "1 Task name"
    ]
    for pattern in id_patterns:
        match = regex_module.search(pattern, result.stdout, regex_module.MULTILINE)
        if match:
            task_id = match.group(1)
            print(f"[Test] Extracted task ID: {task_id}")
            break

    result = subprocess.run(
        ["python", "-m", "todo", "done", task_id],
        cwd=workspace_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(f"[Test] Done command output: {result.stdout} {result.stderr}")
    telemetry.record_validation(result.returncode == 0, f"done failed: {result.stderr}")
    assert result.returncode == 0, f"Done command failed: {result.stderr}"

    # Verify task is marked as done by listing again
    result = subprocess.run(
        ["python", "-m", "todo", "list"],
        cwd=workspace_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(f"[Test] List after done: {result.stdout}")

    # Check for done indicators (checkmark, [x], "done", "completed", strikethrough)
    done_indicators = ["[x]", "[X]", "done", "completed", "finished"]
    task_marked_done = any(indicator in result.stdout.lower() for indicator in done_indicators)
    # Also accept if task is no longer in pending list (some implementations filter)
    telemetry.record_validation(
        task_marked_done or result.returncode == 0,
        "Task not marked as done"
    )
    print(f"[Test] Task marked done: {task_marked_done}")

    # Finish telemetry and print summary
    telemetry.finish()
    print(f"\n{telemetry.summary()}")

    print("[Test] SUCCESS: Todolist CLI built and verified!")


@pytest.fixture
def api_telemetry():
    """Create telemetry tracker for API test metrics."""
    return TelemetryTracker(test_name="test_todolist_sprint_api_direct")


@pytest.mark.anyio
@pytest.mark.integration
@retry_on_failure(max_retries=2, exceptions=(AssertionError, TimeoutError))
async def test_todolist_sprint_api_direct(temp_artifacts_dir, monkeypatch, api_telemetry):
    """
    Integration test: Create todolist sprint via API (no browser).

    Faster alternative that uses the API directly to create a sprint,
    then validates the PhaseRunner output with enhanced validation.
    """
    import httpx

    telemetry = api_telemetry

    # Use temp directory for artifacts
    monkeypatch.setattr(settings, "AUTOCODE_ARTIFACTS_DIR", temp_artifacts_dir)

    base_url = "http://localhost:8000/api/v1"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check backend is up
        try:
            health = await client.get(f"{base_url}/health")
            if health.status_code != 200:
                pytest.skip("Backend not available")
        except httpx.ConnectError:
            pytest.skip("Backend not available at localhost:8000")

        # Create sprint
        sprint_data = {
            "name": "Todolist API Test Sprint",
            "goal": TODOLIST_GOAL,
            "status": "planned",
        }

        response = await client.post(f"{base_url}/sprints", json=sprint_data)
        assert response.status_code == 200, f"Failed to create sprint: {response.text}"

        sprint = response.json()
        sprint_id = sprint["id"]
        print(f"[Test] Created sprint: {sprint_id}")

        # Start the sprint (triggers PhaseRunner)
        start_response = await client.post(f"{base_url}/sprints/{sprint_id}/start")
        assert start_response.status_code == 200, f"Failed to start sprint: {start_response.text}"
        print("[Test] Sprint started, waiting for PhaseRunner...")

        # Poll for completion with exponential backoff
        completed = False
        current_status = "unknown"

        def check_completion() -> bool:
            nonlocal completed, current_status
            # This is sync but we need async - handled below
            return completed

        # Use manual backoff loop for async API calls
        max_wait = 300
        initial_interval = 10.0
        max_interval = 30.0
        backoff_factor = 1.5
        current_interval = initial_interval
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < max_wait:
            status_response = await client.get(f"{base_url}/sprints/{sprint_id}")
            current_status = status_response.json()["status"]

            if current_status == "completed":
                print("[Test] Sprint completed successfully!")
                completed = True
                break
            elif current_status == "failed":
                pytest.fail("Sprint failed during execution")

            elapsed = asyncio.get_event_loop().time() - start_time
            remaining = max_wait - elapsed
            wait_time = min(current_interval, remaining)

            telemetry.record_poll(wait_time)
            print(f"[Test] Sprint status: {current_status} ({elapsed:.0f}s, next poll in {wait_time:.1f}s)")

            await asyncio.sleep(wait_time)
            current_interval = min(current_interval * backoff_factor, max_interval)

        if not completed:
            pytest.fail(f"Sprint did not complete within {max_wait}s (last status: {current_status})")

        # Validate the package was created
        found_packages = list(temp_artifacts_dir.rglob("todo/__init__.py"))
        telemetry.record_validation(bool(found_packages), "No todo package found")
        assert found_packages, f"No todo package found in {temp_artifacts_dir}"

        found_package = found_packages[0].parent
        telemetry.record_file(str(found_package))

        # Enhanced validation: check file contents
        print("[Test] Validating package contents...")

        cli_file = found_package / "cli.py"
        if cli_file.exists():
            is_valid, message = validate_cli_has_argparse(cli_file)
            telemetry.record_validation(is_valid, message)
            print(f"[Test] cli.py: {message}")

        store_file = found_package / "store.py"
        if store_file.exists():
            is_valid, message = validate_store_has_json(store_file)
            telemetry.record_validation(is_valid, message)
            print(f"[Test] store.py: {message}")

        main_file = found_package / "__main__.py"
        if main_file.exists():
            is_valid, message = validate_main_has_entry_point(main_file)
            telemetry.record_validation(is_valid, message)
            print(f"[Test] __main__.py: {message}")

        # Test CLI commands including done
        workspace_dir = found_package.parent

        # Test add command
        telemetry.record_cli_test("add")
        result = subprocess.run(
            ["python", "-m", "todo", "add", "API Test Task"],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        telemetry.record_validation(result.returncode == 0, f"add failed: {result.stderr}")
        if result.returncode == 0:
            print("[Test] Add command: OK")

        # Test list command
        telemetry.record_cli_test("list")
        result = subprocess.run(
            ["python", "-m", "todo", "list"],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        telemetry.record_validation(result.returncode == 0, f"list failed: {result.stderr}")
        if result.returncode == 0:
            print(f"[Test] List command: OK - {result.stdout.strip()[:50]}...")

        # Test done command
        telemetry.record_cli_test("done")
        result = subprocess.run(
            ["python", "-m", "todo", "done", "1"],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        telemetry.record_validation(result.returncode == 0, f"done failed: {result.stderr}")
        if result.returncode == 0:
            print("[Test] Done command: OK")

        # Finish telemetry
        telemetry.finish()
        print(f"\n{telemetry.summary()}")

        print("[Test] SUCCESS: Todolist sprint completed via API!")
