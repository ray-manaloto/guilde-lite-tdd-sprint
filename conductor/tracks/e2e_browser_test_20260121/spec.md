# Specification: Implement End-to-End Browser Verification for Sprint Workflow

## Overview
To provide definitive proof that the webapp can build a project from a sprint, we will implement an automated end-to-end (E2E) integration test. This test will use a browser automation tool (likely Playwright via Python or the existing `agent_browser` infrastructure) to simulate a user logging in, triggering a sprint, and waiting for the agent to generate code.

## Functional Requirements
1.  **Browser Simulation:** The test must launch a headless browser or use an API client that mimics browser interactions (if UI isn't ready, we'll hit the API, but the goal is "browser-agent" style).
2.  **Sprint Trigger:** The test must trigger a sprint with the prompt: "Create a simple python app that prints 'hello world'".
3.  **Completion Wait:** The test must poll or wait for the sprint status to reach `completed`.
4.  **Artifact Verification:** The test must verify that the expected file (`hello.py`) exists on the local filesystem in the `AUTOCODE_ARTIFACTS_DIR`.

## Technical Requirements
- **Tooling:** Use `pytest` with `playwright` (or `pytest-asyncio` with the project's `agent_browser` tool if appropriate).
- **Location:** `backend/tests/integration/test_e2e_sprint_flow.py`.
- **Environment:** Must run against the local dev environment (localhost:8000).

## Acceptance Criteria
- A new test file `backend/tests/integration/test_e2e_sprint_flow.py` exists.
- The test passes when run against a running backend.
- The test verifies filesystem side-effects.
