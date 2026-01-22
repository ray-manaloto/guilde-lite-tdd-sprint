"""Agent-browser integration test for requesting a python script."""

import asyncio
import subprocess
import shutil
import pytest
from app.agents.assistant import AssistantAgent
from app.core.config import settings

# NOTE: This test requires the full stack to be running (backend on 8000, frontend on 3000)

@pytest.mark.anyio
async def test_agent_browser_request_hello_world():
    """
    Integration test using the browser agent to create a sprint via the UI
    that results in a python script 'hello.py' being created in the artifacts dir.
    """
    if not shutil.which("agent-browser"):
        pytest.skip("agent-browser CLI not available")
    
    artifacts_dir = settings.AUTOCODE_ARTIFACTS_DIR
    print(f"\n[Test] Using artifacts directory: {artifacts_dir}")
    
    # Ensure directory exists
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    # Remove existing hello.py to ensure a clean test
    target_file = artifacts_dir / "hello.py"
    if target_file.exists():
        print(f"[Test] Removing existing {target_file}")
        target_file.unlink()

    # Find ANY hello.py in subdirectories and remove them too (recursive cleanup for this specific file)
    for f in artifacts_dir.rglob("hello.py"):
        print(f"[Test] Removing existing {f}")
        f.unlink()

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
        "1. Enter 'Hello World Request Sprint' in the name field. "
        "2. Enter 'Create a python script named hello.py that prints hello world.' in the goal field. "
        "3. Set status to 'Planned' (default). "
        "4. Click the 'Create sprint' button. "
        "Wait for the sprint to be created. Then inform me when it is done."
    )

    print("\n[Agent] Starting browser automation...")
    # Run the agent
    # We iterate over the stream to get real-time feedback if supported, 
    # but AssistantAgent.run() currently returns the full result at once.
    # To get better visibility, we inspect tool_events after execution.
    output, tool_events, _ = await agent.run(prompt)
    
    print(f"\n[Agent] Finished run. Result: {output}")
    print("\n[Agent] Tool Execution History:")
    for event in tool_events:
        # PydanticAI tool events usually have 'tool_name', 'args', and 'result'
        # Adjust access based on the actual object structure if needed.
        # Assuming event is a ModelResponse or similar structure from pydantic_ai
        if hasattr(event, 'parts'):
            for part in event.parts:
                if hasattr(part, 'tool_call'):
                    print(f"  -> Tool Call: {part.tool_call}")
                if hasattr(part, 'tool_return'):
                    print(f"  <- Tool Return: {part.tool_return}")
        else:
             print(f"  Event: {event}")

    # Now we poll the filesystem for the artifact
    print("[Test] Polling filesystem for artifacts...")
    max_wait = 180 # 3 minutes
    found_file = None
    
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < max_wait:
        # Search recursively because the backend might create a subdir for the sprint/session
        found_files = list(artifacts_dir.rglob("hello.py"))
        if found_files:
            found_file = found_files[0]
            break
        await asyncio.sleep(5)
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
    print("[Test] SUCCESS: Script created and verified!")
