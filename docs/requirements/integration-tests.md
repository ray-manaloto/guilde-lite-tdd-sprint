# Integration Test Requirements

Source of truth for integration test behavior. Keep this file, `docs/project-plan.md`, and `docs/todos.md` in sync.

## Scope

- Must run without the webapp. Reuse backend/service code paths directly.
- Must validate a working solution exists and can be executed.
- Must use SDK APIs (OpenAI + Anthropic) for every AI prompt step.

## End-to-End Flow (Headless)

1. Start sprint interview for the user prompt.
2. Ask follow-up questions until the AI determines there is no ambiguity.
3. Save answers and create the sprint.
4. Automatically run the sprint (no manual run endpoint required).
5. Generate a Python script that prints "hello world".
6. Validate the script:
   - Exists under `AUTOCODE_ARTIFACTS_DIR`
   - Is executable
   - When run via `uv`, prints `hello world`
7. Mark sprint status:
   - `active` once execution starts
   - `completed` once verification passes

## Multi-Agent Requirements (Every AI Step)

For each AI prompt step (interview questions, discovery, coding, verification):

- Send the same prompt to OpenAI and Anthropic SDKs.
- Store each response as a markdown artifact.
- Run a judge (LLM-as-judge) to select the best response.
- Persist the selected response and judge rationale.

## Artifact Requirements (Per Step)

Each step must write a durable artifact bundle containing:

- `openai_response.md`
- `anthropic_response.md`
- `judge_decision.md` (chosen response + rationale)
- `metadata.json` (or markdown) with:
  - model name used for each SDK call
  - token usage for each SDK call
  - tool/skill/hook usage for each SDK call
  - trace IDs and Logfire trace links
  - timestamps and latency per call

Artifacts must be stored under the sprint workspace in `AUTOCODE_ARTIFACTS_DIR`.

## Interview Requirements

- The interview must not use a fixed question count.
- The interviewer continues asking until the AI indicates no ambiguity remains.
- A safety cap is allowed but must be recorded in metadata if reached.

## Test Expectations

The integration test must assert:

- Both SDK calls succeeded for each step.
- Artifacts exist on disk for every step.
- Judge decision is persisted and points to one of the candidates.
- The generated script is executable and prints `hello world`.
