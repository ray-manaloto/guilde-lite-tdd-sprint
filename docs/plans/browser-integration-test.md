# Plan: Browser Agent Integration Test

## Objective
Create a reliable integration test that verifies the `AssistantAgent` can successfully use the `agent_browser` tool to navigate to a website (Google) and extract information (Doodle/Title).

## Problem Analysis
The user reported: "I can’t reliably read the doodle from this view."
*   **Root Cause:** The `agent_browser` tool is a CLI wrapper. The agent likely calls `agent-browser open <url>`, which might return success but *not* the full page content (to save tokens).
*   **Solution:** The agent needs to know it can run subsequent commands like `agent-browser get html` or `agent-browser snapshot` to "see" the page.

## Implementation Steps

### 1. Enhance Tool Documentation (Code Change)
Update the docstring in `backend/app/agents/assistant.py` for the `agent_browser` tool.
*   **Current:** "Run an agent-browser command for live web interactions."
*   **Proposed:** Explicitly list available subcommands (`open`, `get`, `click`, etc.) so the LLM knows how to "read" the page after opening it.

### 2. Create Integration Test
**File:** `backend/tests/integration/test_agent_browser_flow.py`

**Test Logic:**
1.  **Setup:** Instantiate `AssistantAgent` with a real provider (using `openai-responses:gpt-4o-mini` or similar for cost/speed).
2.  **Prompt:** "Go to https://www.google.com. First open the page, then get the page title."
3.  **Execution:** Run the agent loop.
4.  **Verification:**
    *   Check `tool_events` to ensure `agent_browser` was called with `open ...` and then `get title` (or similar).
    *   Assert the final response contains "Google".

### 3. Validation
Run the test using `pytest backend/tests/integration/test_agent_browser_flow.py`.

## Success Criteria
*   The agent autonomously chains commands: `open` -> `get`.
*   The test passes against a live site (Google or Example.com).
