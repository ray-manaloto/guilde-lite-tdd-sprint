"""Agent-browser integration test for sprint workflow."""

import os
import shutil
import asyncio
import subprocess
from pathlib import Path

import pytest
from app.agents.assistant import AssistantAgent
from app.core.config import settings

# NOTE: This test requires the full stack to be running (backend on 8000, frontend on 3000)
# Run `./scripts/devctl.sh start` before running this test.

@pytest.mark.anyio
async def test_agent_browser_sprint_creation():
    """
    Integration test using the browser agent to create a sprint via the UI
    and verify the build artifacts.
    """
    if not shutil.which("agent-browser"):
        pytest.skip("agent-browser CLI not available")
    
    # Clean up artifacts dir
    artifacts_dir = settings.AUTOCODE_ARTIFACTS_DIR
    if artifacts_dir.exists() and "tmp" in str(artifacts_dir):
        shutil.rmtree(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    agent = AssistantAgent(
        system_prompt=(
            "You are a browser automation agent. Your goal is to use the 'agent_browser' tool "
            "to navigate to the local webapp and trigger a sprint."
        )
    )

    # We need to tell the agent about the URL and the steps
    prompt = (
        "Go to http://localhost:3000/en/sprints. "
        "Find the 'New Sprint' form. "
        "1. Enter 'Browser Agent Sprint' in the name field. "
        "2. Enter 'Create a python script named hello.py that prints hello world.' in the goal field. "
        "3. Set status to 'Planned' (default). "
        "4. Click the 'Create sprint' button. "
        "Wait for the sprint to be created. Then inform me when it is done."
    )

    print("\n[Agent] Starting browser automation...")
    output, tool_events, _ = await agent.run(prompt)
    print(f"[Agent] Output: {output}")

    # Now we poll the filesystem for the artifact
    # We allow some time for the PhaseRunner to pick up the sprint and finish it.
    # The PhaseRunner starts automatically on sprint creation.
    
    print("[Test] Polling filesystem for artifacts...")
    max_wait = 180 # 3 minutes
    found_file = None
    
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < max_wait:
        found_files = list(artifacts_dir.rglob("hello.py"))
        if found_files:
            found_file = found_files[0]
            break
        await asyncio.sleep(10)
        print(f"[Test] Still waiting for hello.py... ({int(asyncio.get_event_loop().time() - start_time)}s)")

    assert found_file is not None, f"hello.py was not created in {artifacts_dir} within {max_wait}s"
    print(f"[Test] Found artifact at: {found_file}")

    # Verify execution
    print("[Test] Executing hello.py...")
    result = subprocess.run(
        ["python3", str(found_file)],
        capture_output=True,
        text=True
    )
    
    print(f"[Test] Output: {result.stdout}")
    assert result.returncode == 0
    assert "hello world" in result.stdout.lower()
    print("[Test] SUCCESS: App built and verified!")
