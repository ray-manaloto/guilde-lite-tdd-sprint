# Plan: WebSocket Integration Test with Logfire Validation

## Objective
Verify the full end-to-end flow from the **Web UI (simulated via WebSocket)** to the **Agent** and finally to the **Browser Tool**.
Enable deterministic validation of this flow using **Logfire**.

## User Request Context
> "that is not what we are testing ... we are testing if provided a chat in the web ui, can a browser agent actually be spawned"
> "we should be able to validate via querying logfire"

## Implementation Steps

### 1. Create `backend/tests/integration/test_websocket_agent_flow.py`
This test will use `httpx` and `websockets` (or `starlette.testclient.TestClient` with WebSocket support) to mimic the Frontend.

**Test Logic:**
1.  **Setup:**
    *   Inject `Logfire` instrumentation (via existing `telemetry.py`).
    *   Capture `start_time` (UTC).
2.  **Execution:**
    *   Connect to `ws://localhost:8000/api/v1/ws/agent` (using `TestClient` or `AsyncClient`).
    *   Send Message: `{"message": "Go to google.com and tell me the title."}`.
    *   Receive Events loop:
        *   Wait for `tool_call` event where `tool_name="agent_browser"`.
        *   Wait for `final_result`.
3.  **Telemetry Output:**
    *   Capture `end_time` (UTC).
    *   Print **Logfire SQL Query** and **Dashboard URL** to standard output.
    *   *Note:* Automated API querying is skipped to avoid auth fragility, but the output will provide one-click validation.

### 2. Verification
**Command:**
```bash
uv run --directory backend pytest tests/integration/test_websocket_agent_flow.py -s
```

**Success Criteria:**
*   Test passes (Agent receives message -> calls tool -> returns answer).
*   Test prints "Logfire Time Range: ..." and a valid Logfire Project URL.
*   User can click the link and see the trace of the WebSocket session *and* the `agent_browser.cli` span nested within it.

## Dependencies
*   `starlette` / `fastapi` (already installed)
*   `pytest-asyncio` / `anyio` (already installed)
*   `httpx` (already installed)
