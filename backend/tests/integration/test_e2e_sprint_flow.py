"End-to-end integration test for the sprint workflow."

import asyncio
import os
import shutil
from pathlib import Path
from uuid import UUID

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
        timeout=10.0, # Fast timeout for API calls, polling handles the long wait
    ) as ac:
        yield ac

@pytest.mark.anyio
async def test_e2e_sprint_execution(live_client: AsyncClient):
    """
    End-to-end test of the sprint workflow against a running server.
    
    Steps:
    1. Create a sprint via API with a coding task.
    2. Poll the sprint status until it completes.
    3. Verify the generated artifacts exist on the filesystem.
    """
    # Clean up artifacts dir before test
    # Note: We assume the running server shares the same filesystem and config
    if settings.AUTOCODE_ARTIFACTS_DIR.exists():
        # Only clean if we are sure it's safe (e.g., in tmp)
        if "tmp" in str(settings.AUTOCODE_ARTIFACTS_DIR):
            shutil.rmtree(settings.AUTOCODE_ARTIFACTS_DIR)
    
    settings.AUTOCODE_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Trigger Sprint
    print("\n[E2E] Triggering sprint...")
    try:
        response = await live_client.post(
            f"{settings.API_V1_STR}/sprints",
            json={
                "name": "E2E Hello World",
                "goal": "Create a python script named 'hello.py' that prints 'hello world'.",
            },
        )
        assert response.status_code == 201, f"Failed to create sprint: {response.text}"
        sprint_data = response.json()
        sprint_id = sprint_data["id"]
        print(f"[E2E] Sprint created: {sprint_id}")
    except Exception as e:
        pytest.fail(f"Could not connect to localhost:8000. Is the server running? Error: {e}")

    # 2. Poll for Completion
    # We poll the sprint status every 5 seconds for up to 3 minutes
    max_retries = 36 
    status = "planned"
    
    print("[E2E] Polling for completion...")
    for i in range(max_retries):
        await asyncio.sleep(5)
        try:
            r = await live_client.get(f"{settings.API_V1_STR}/sprints/{sprint_id}")
            assert r.status_code == 200
            data = r.json()
            status = data["status"]
            print(f"[E2E] Poll {i+1}/{max_retries}: Status = {status}")
            
            if status == "completed":
                print("[E2E] Sprint completed successfully!")
                break
            if status == "failed":
                pytest.fail("Sprint status reported as 'failed'")
        except Exception as e:
            print(f"[E2E] Poll failed: {e}")
            
    assert status == "completed", f"Sprint timed out with status: {status}"

    # 3. Verify Artifacts
    # We look for hello.py in the artifacts directory
    print(f"[E2E] Verifying artifacts in {settings.AUTOCODE_ARTIFACTS_DIR}...")
    found_files = list(settings.AUTOCODE_ARTIFACTS_DIR.rglob("hello.py"))
    assert len(found_files) > 0, f"hello.py not found in {settings.AUTOCODE_ARTIFACTS_DIR}"
    
    # Verify content
    content = found_files[0].read_text()
    assert "hello world" in content.lower()
    print(f"[E2E] Artifact verification passed. Found: {found_files[0]}")