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
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.agents.assistant import AssistantAgent
from app.core.config import settings


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


@pytest.mark.anyio
@pytest.mark.integration
@pytest.mark.slow
async def test_todolist_sprint_via_browser(temp_artifacts_dir, monkeypatch):
    """
    Integration test: Create todolist sprint via browser and verify build.

    This test:
    1. Uses browser agent to navigate to sprint creation page
    2. Creates a sprint with the todolist goal
    3. Waits for PhaseRunner to build the project
    4. Validates the package structure
    5. Tests the CLI works
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
    output, tool_events, _ = await agent.run(create_prompt)
    print(f"[Agent] Output: {output}")

    # Give PhaseRunner time to pick up the sprint
    print("[Test] Waiting for PhaseRunner to start...")
    await asyncio.sleep(5)

    # Step 2: Poll for the todo package to be created
    print(f"[Test] Polling {temp_artifacts_dir} for todo package...")
    max_wait = 300  # 5 minutes for complex project
    poll_interval = 15
    found_package = None

    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < max_wait:
        # Look for the todo package structure
        found_dirs = list(temp_artifacts_dir.rglob("todo/__init__.py"))
        if found_dirs:
            found_package = found_dirs[0].parent
            break

        # Also check for __main__.py directly
        found_mains = list(temp_artifacts_dir.rglob("todo/__main__.py"))
        if found_mains:
            found_package = found_mains[0].parent
            break

        elapsed = int(asyncio.get_event_loop().time() - start_time)
        print(f"[Test] Still waiting for todo package... ({elapsed}s)")

        # List what we have so far
        all_files = list(temp_artifacts_dir.rglob("*.py"))
        if all_files:
            print(f"[Test] Found files so far: {[str(f) for f in all_files[:5]]}")

        await asyncio.sleep(poll_interval)

    assert found_package is not None, (
        f"todo package not created in {temp_artifacts_dir} within {max_wait}s. "
        f"Files found: {list(temp_artifacts_dir.rglob('*'))}"
    )
    print(f"[Test] Found todo package at: {found_package}")

    # Step 3: Validate package structure
    expected_files = ["__init__.py", "cli.py", "store.py"]
    for filename in expected_files:
        filepath = found_package / filename
        assert filepath.exists(), f"Missing expected file: {filepath}"
        print(f"[Test] ✓ Found {filename}")

    # Check for __main__.py (required for python -m todo)
    main_file = found_package / "__main__.py"
    assert main_file.exists(), f"Missing __main__.py for package execution"
    print("[Test] ✓ Found __main__.py")

    # Step 4: Test the CLI
    workspace_dir = found_package.parent
    print(f"[Test] Testing CLI from {workspace_dir}...")

    # Test: python -m todo add "Test task"
    result = subprocess.run(
        ["python", "-m", "todo", "add", "Test task"],
        cwd=workspace_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(f"[Test] Add command output: {result.stdout} {result.stderr}")
    assert result.returncode == 0, f"Add command failed: {result.stderr}"

    # Test: python -m todo list
    result = subprocess.run(
        ["python", "-m", "todo", "list"],
        cwd=workspace_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(f"[Test] List command output: {result.stdout}")
    assert result.returncode == 0, f"List command failed: {result.stderr}"
    assert "Test task" in result.stdout or "test task" in result.stdout.lower(), (
        f"Task not found in list output: {result.stdout}"
    )

    print("[Test] ✓ SUCCESS: Todolist CLI built and verified!")


@pytest.mark.anyio
@pytest.mark.integration
async def test_todolist_sprint_api_direct(temp_artifacts_dir, monkeypatch):
    """
    Integration test: Create todolist sprint via API (no browser).

    Faster alternative that uses the API directly to create a sprint,
    then validates the PhaseRunner output.
    """
    import httpx

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

        # Poll for completion
        max_wait = 300
        poll_interval = 10
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < max_wait:
            status_response = await client.get(f"{base_url}/sprints/{sprint_id}")
            status = status_response.json()["status"]

            if status == "completed":
                print("[Test] Sprint completed successfully!")
                break
            elif status == "failed":
                pytest.fail("Sprint failed during execution")

            elapsed = int(asyncio.get_event_loop().time() - start_time)
            print(f"[Test] Sprint status: {status} ({elapsed}s)")
            await asyncio.sleep(poll_interval)
        else:
            pytest.fail(f"Sprint did not complete within {max_wait}s")

        # Validate the package was created
        found_packages = list(temp_artifacts_dir.rglob("todo/__init__.py"))
        assert found_packages, f"No todo package found in {temp_artifacts_dir}"

        print("[Test] ✓ SUCCESS: Todolist sprint completed via API!")
