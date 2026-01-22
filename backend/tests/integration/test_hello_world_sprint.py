"""Integration test for Hello World sprint."""

import asyncio
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.config import settings

# NOTE: This test requires the backend server to be running on localhost:8000
# Run `./scripts/devctl.sh start` before running this test.

@pytest.fixture
async def live_client():
    """Client connected to the live running server."""
    async with AsyncClient(
        base_url="http://localhost:8000",
        timeout=10.0,
    ) as ac:
        yield ac

@pytest.mark.anyio
async def test_hello_world_sprint(live_client: AsyncClient):
    """
    Test a sprint that requests a hello world script.
    """
    # Clean up artifacts dir before test
    artifacts_dir = settings.AUTOCODE_ARTIFACTS_DIR
    if artifacts_dir.exists():
        # Only clean if it looks like a temp dir to be safe
        if "tmp" in str(artifacts_dir) or "guilde-lite-tdd-sprint-filesystem" in str(artifacts_dir):
            shutil.rmtree(artifacts_dir)
    
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # 1. Trigger Sprint
    print("\n[Test] Triggering sprint...")
    try:
        response = await live_client.post(
            f"{settings.API_V1_STR}/sprints",
            json={
                "name": "Hello World Sprint",
                "goal": "Create a python script named 'hello.py' that prints 'hello world'.",
            },
        )
        assert response.status_code == 201, f"Failed to create sprint: {response.text}"
        sprint_data = response.json()
        sprint_id = sprint_data["id"]
        print(f"[Test] Sprint created: {sprint_id}")
    except Exception as e:
        pytest.fail(f"Could not connect to localhost:8000. Is the server running? Error: {e}")

    # 2. Poll for Completion
    max_retries = 60  # Wait up to 5 minutes (5s * 60)
    status = "planned"
    
    print("[Test] Polling for completion...")
    for i in range(max_retries):
        await asyncio.sleep(5)
        try:
            r = await live_client.get(f"{settings.API_V1_STR}/sprints/{sprint_id}")
            assert r.status_code == 200
            data = r.json()
            status = data["status"]
            print(f"[Test] Poll {i+1}/{max_retries}: Status = {status}")
            
            if status == "completed":
                print("[Test] Sprint completed successfully!")
                break
            if status == "failed":
                # Print any error details if available in the future
                pytest.fail("Sprint status reported as 'failed'")
        except Exception as e:
            print(f"[Test] Poll failed (retrying): {e}")
            
    assert status == "completed", f"Sprint timed out with status: {status}"

    # 3. Verify Artifacts
    print(f"[Test] Verifying artifacts in {artifacts_dir}...")
    # Recursively search for hello.py
    found_files = list(artifacts_dir.rglob("hello.py"))
    assert len(found_files) > 0, f"hello.py not found in {artifacts_dir}"
    
    target_file = found_files[0]
    print(f"[Test] Found file at: {target_file}")

    # 4. Verify Execution
    print("[Test] Executing hello.py...")
    result = subprocess.run(
        ["python3", str(target_file)],
        capture_output=True,
        text=True
    )
    
    print(f"[Test] Output: {result.stdout}")
    assert result.returncode == 0, f"Script failed with error: {result.stderr}"
    assert "hello world" in result.stdout.lower()
    print("[Test] Verification passed!")
