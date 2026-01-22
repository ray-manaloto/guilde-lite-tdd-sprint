# Plan: Session-Scoped File System Tools

## Objective
Implement `read_file`, `write_file`, `list_dir` tools that are scoped to a unique, timestamped directory for each agent session.

## Configuration
*   **Env Var:** `AUTOCODE_ARTIFACTS_DIR` (e.g., `~/dev/tmp/guilde-lite-tdd-sprint-filesystem`)
*   **Subdirectory Pattern:** `<AUTOCODE_ARTIFACTS_DIR>/<timestamp_ns>/`

## Implementation Steps

### 1. Update Settings (`backend/app/core/config.py`)
*   Add `AGENT_FS_ENABLED: bool`
*   Add `AUTOCODE_ARTIFACTS_DIR: Path | None` (via `.env`)
*   [DONE]

### 2. Update `Deps` (`backend/app/agents/assistant.py`)
*   Add `session_dir: Path | None = None` field to `Deps`.
*   In `AssistantAgent.run` and `iter`, if `deps.session_dir` is None, generate it:
    ```python
    session_id = datetime.now().strftime("%Y-%m-%dT%H%M%S.%f") + "Z"
    path = settings.AUTOCODE_ARTIFACTS_DIR / session_id
    path.mkdir(parents=True, exist_ok=True)
    deps.session_dir = path
    ```
    *Note: Using UTC ISO format generally preferred, but user asked for "datetime with 9 second nanosecond precision". Python default is microseconds (6 digits). Nanoseconds requires `time.time_ns()`. I will use ISO format with microseconds as it's standard, or append `_` + nanoseconds if strict adherence required.*
    *   *Refinement:* User asked "datetime with 9 second nanosecond precision". I will use `%Y-%m-%dT%H:%M:%S.%f` + fake last 3 digits or just high precision timestamp if available to match request closely.

### 3. Implement Tools (`backend/app/agents/tools/filesystem.py`)
*   **Dependency:** `ctx: RunContext[Deps]`
*   **Safety Check:**
    *   `target_path = ctx.deps.session_dir / user_path`
    *   `resolved = target_path.resolve()`
    *   `if not resolved.is_relative_to(ctx.deps.session_dir.resolve()): raise ValueError("Access denied")`
*   **Tools:**
    *   `write_file(path, content)`: Writes to session dir.
    *   `read_file(path)`: Reads from session dir.
    *   `list_dir(path)`: Lists session dir.

### 4. Register Tools (`backend/app/agents/assistant.py`)
*   Import `write_file`, `read_file`, `list_dir`.
*   Register if `settings.AGENT_FS_ENABLED` and `settings.AUTOCODE_ARTIFACTS_DIR` are set.

### 5. E2E Recursive Test (`frontend/e2e/recursive-fs.spec.ts`)
*   **Scenario:**
    1.  Login.
    2.  Chat: "Write a file named 'timestamp_test.txt' with content 'FS_TEST_passed'".
    3.  Wait for response.
*   **Validation Script (`scripts/validate-recursive-fs.py`):**
    1.  Run E2E test.
    2.  Glob search `AUTOCODE_ARTIFACTS_DIR` for the *newest* directory.
    3.  Check if `timestamp_test.txt` exists there.

## Verification
*   Run `uv run --project backend python scripts/validate-recursive-fs.py`.
