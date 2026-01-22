import os
import shutil

import pytest
from app.agents.assistant import AssistantAgent

pytestmark = pytest.mark.integration

@pytest.mark.anyio
async def test_agent_browser_google_title_flow():
    """
    Integration test to verify the agent can use the agent_browser tool 
    to navigate to a page and retrieve its title.
    
    This tests the full tool-use loop:
    1. Agent receives instruction.
    2. Agent calls 'agent_browser open ...'
    3. Agent calls 'agent_browser get title' (or similar).
    4. Agent returns final answer.
    """
    if not shutil.which("agent-browser"):
        pytest.skip("agent-browser CLI not available")
    if not any(
        [
            os.getenv("OPENAI_API_KEY"),
            os.getenv("ANTHROPIC_API_KEY"),
            os.getenv("OPENROUTER_API_KEY"),
        ]
    ):
        pytest.skip("No LLM API key configured for agent browser test")
    if not any(
        [
            os.getenv("OPENAI_MODEL"),
            os.getenv("ANTHROPIC_MODEL"),
            os.getenv("OPENROUTER_MODEL"),
        ]
    ):
        pytest.skip("No LLM model configured for agent browser test")
    # Use a cheap/fast model if possible, or the one from env
    # Using the class default which pulls from settings
    agent = AssistantAgent(
        system_prompt="You are a helpful assistant with access to a webbrowser. use the agent_browser tool."
    )

    prompt = "Go to https://www.google.com and tell me the title of the page."
    
    from datetime import datetime, timezone
    start_time = datetime.now(timezone.utc)
    print(f"\n--- Test Start: {start_time.isoformat()} ---")

    # Increase timeout for real network calls
    output, tool_events, _ = await agent.run(prompt)
    
    end_time = datetime.now(timezone.utc)
    print(f"--- Test End: {end_time.isoformat()} ---")
    print(f"Duration: {(end_time - start_time).total_seconds()}s")
    
    # Generate a helpful Logfire query link (approximate structure)
    print(f"Logfire Time Range: {start_time.isoformat()}Z - {end_time.isoformat()}Z")
    
    print(f"Agent Output: {output}")
    print(f"Tool Events: {tool_events}")

    # Verification 1: Check if tool was actually called
    tool_names = [e.tool_name for e in tool_events if hasattr(e, 'tool_name')]
    assert 'agent_browser' in tool_names, f"Agent did not call agent_browser. Tools called: {tool_names}"

    import json
    # Verification 2: Check for 'open' command
    # args can be a dict or a JSON string depending on the PydanticAI version/model
    open_calls = []
    for e in tool_events:
        if hasattr(e, 'tool_name') and e.tool_name == 'agent_browser' and hasattr(e, 'args'):
            args_data = e.args
            if isinstance(args_data, str):
                args_data = json.loads(args_data)
            
            if 'open' in args_data.get('command', ''):
                open_calls.append(args_data)

    assert len(open_calls) > 0, "Agent did not use 'open' command"

    # Verification 3: Check final output
    assert "Google" in output, f"Agent failed to find correct title. Output: {output}"
