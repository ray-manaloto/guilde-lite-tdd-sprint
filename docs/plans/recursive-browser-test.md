# Plan: Recursive Browser E2E Test

## Objective
Verify the entire system loop by simulating a user with a browser (Playwright) who asks the Agent to use *its* browser.
Validate the internal execution via Logfire telemetry.

## User Story
1.  **External Agent (Playwright):** Visits `http://localhost:3000`.
2.  **Action:** Types "Go to google.com and tell me the title" into the Chat UI.
3.  **System Reaction:**
    *   Frontend sends message to Backend (WebSocket).
    *   Backend Agent receives message.
    *   Backend Agent calls `agent_browser` (Internal Browser) to visit Google.
4.  **Observation:** Playwright sees the Agent's response "The page title is Google".
5.  **Validation:** We query Logfire to confirm `agent_browser.cli` executed during this session.

## Implementation Steps

### 1. Create Playwright Test
**File:** `frontend/e2e/recursive-agent.spec.ts`
*   **Test:**
    *   Goto `/`.
    *   Input locator: `textarea[name="message"]` (or similar).
    *   Send button locator.
    *   Expect response locator to contain "Google".

### 2. Create Validation Wrapper (Python)
**File:** `scripts/validate-recursive-flow.py`
*   **Logic:**
    *   Get `start_time`.
    *   Run `npm run test:e2e -- recursive-agent.spec.ts` (via `subprocess`).
    *   Get `end_time`.
    *   Use `LOGFIRE_READ_TOKEN` to query the Logfire API `https://logfire-api.pydantic.dev/v1/query`.
    *   Query: `SELECT * FROM spans WHERE name='agent_browser.cli' AND timestamp BETWEEN start AND end`.
    *   **Assert:** At least one span returned.

### 3. Execution
Run `python scripts/validate-recursive-flow.py`.

## Pre-requisites
*   Frontend running on `:3000`.
*   Backend running on `:8000`.
*   `LOGFIRE_READ_TOKEN` in `.env`.
