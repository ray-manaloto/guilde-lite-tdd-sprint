# User Stories: Todolist Sprint Prompt Improvements

**Epic:** Improve "todolist - 001" sprint prompt for agentic-browser automated integration testing

**Date:** 2026-01-22

**Context:**
- The PhaseRunner executes 3 phases: discovery (creates implementation_plan.md), coding (creates files), verification (tests the code)
- Integration test (`test_agent_browser_todolist.py`) uses browser automation to create a sprint, then validates the built package
- The sprint goal must produce a working Python CLI todo list manager that passes automated verification

---

## User Story 1: Working Todolist CLI from Sprint Goal

### US-001: Produce a Working Todolist CLI

**As a** developer using the sprint system
**I want** the sprint goal to produce a fully working todolist CLI package
**So that** the automated build system can create functional software without manual intervention

### Acceptance Criteria

#### AC-001.1: Package Structure Created
**Given** a sprint with the todolist CLI goal is started
**When** the coding phase completes
**Then** the following package structure must exist:
- `todo/__init__.py` - Package marker with version
- `todo/cli.py` - Argparse-based command interface
- `todo/store.py` - JSON file persistence layer
- `todo/__main__.py` - Entry point for `python -m todo`

#### AC-001.2: Add Command Works
**Given** the todolist package is created
**When** running `python -m todo add "Test task"`
**Then** the command exits with code 0
**And** a JSON file is created/updated at `~/.todo_test.json`
**And** the task is stored with a unique ID, title, and `done=False` status

#### AC-001.3: List Command Works
**Given** at least one task exists in storage
**When** running `python -m todo list`
**Then** the command exits with code 0
**And** all tasks are displayed with their ID, title, and status
**And** the output includes the previously added task text

#### AC-001.4: Done Command Works
**Given** a task exists with a known ID
**When** running `python -m todo done <ID>`
**Then** the command exits with code 0
**And** the task's `done` status is updated to `True`
**And** subsequent `list` shows the task as completed

#### AC-001.5: No External Dependencies
**Given** the sprint goal specifies "no external deps"
**When** the package is created
**Then** only Python standard library modules are used (argparse, json, pathlib, etc.)
**And** no `requirements.txt` or `pyproject.toml` with dependencies is created

### Notes

- The storage file path (`~/.todo_test.json`) must be consistent so tests can verify content
- Edge case: `list` on empty storage should not error, just show empty/no tasks
- Edge case: `done` with invalid ID should print error message but not crash
- The `__main__.py` file must properly import and call the CLI entry point

### Priority

**Must Have** - Core functionality required for integration test validation

---

## User Story 2: Automated Browser Test Verification

### US-002: Verify CLI via Automated Browser Tests

**As a** tester running integration tests
**I want** to verify the todolist CLI through automated browser-based sprint creation
**So that** the end-to-end sprint workflow is validated without manual intervention

### Acceptance Criteria

#### AC-002.1: Sprint Creation via Browser
**Given** the frontend is running at localhost:3000
**And** the backend is running at localhost:8000
**When** the browser automation agent navigates to `/en/sprints`
**And** clicks "New Sprint" or "Create Sprint" button
**And** fills in the sprint name and goal
**And** submits the form
**Then** a new sprint is created in the database
**And** the sprint ID is accessible for polling

#### AC-002.2: PhaseRunner Execution Triggered
**Given** a sprint is created with the todolist goal
**When** the sprint is started (manually or via API)
**Then** PhaseRunner begins the discovery phase within 5 seconds
**And** WebSocket events are broadcast for phase transitions

#### AC-002.3: Package Detection via Polling
**Given** PhaseRunner is executing the sprint
**When** the integration test polls the artifacts directory
**Then** the `todo/__init__.py` or `todo/__main__.py` file is detected within 300 seconds (5 minutes)
**And** the complete package structure is present

#### AC-002.4: CLI Execution Test
**Given** the todo package is detected in the artifacts directory
**When** the test runs `python -m todo add "Test task"` from the workspace directory
**Then** the command completes successfully (exit code 0)
**And** when running `python -m todo list`
**Then** the output contains "Test task" (case-insensitive)

#### AC-002.5: Test Timeout Handling
**Given** the PhaseRunner is executing
**When** 300 seconds elapse without package detection
**Then** the test fails with a descriptive error message
**And** the error includes the list of files found (if any)
**And** the error helps diagnose what went wrong

### Notes

- The test uses `temp_artifacts_dir` fixture to isolate test artifacts
- `agent-browser` CLI must be available for browser tests (skip if not installed)
- Alternative API-based test (`test_todolist_sprint_api_direct`) provides faster validation path
- Out of scope: Testing multiple concurrent sprint executions

### Priority

**Must Have** - Required for CI/CD validation of sprint workflow

---

## User Story 3: Discovery Phase Plan Quality

### US-003: Generate Complete Implementation Plan

**As a** PhaseRunner agent
**I want** the discovery phase to produce a comprehensive implementation plan
**So that** the coding phase has clear instructions for file creation

### Acceptance Criteria

#### AC-003.1: Implementation Plan File Created
**Given** a sprint goal is provided
**When** the discovery phase completes
**Then** `implementation_plan.md` exists in the workspace
**And** the file is created using `fs_write_file` tool

#### AC-003.2: File List Specification
**Given** the implementation plan is created
**When** the plan content is read
**Then** it contains a complete list of files to be created
**And** each file has its full path relative to workspace root
**And** the list includes at minimum: `todo/__init__.py`, `todo/cli.py`, `todo/store.py`, `todo/__main__.py`

#### AC-003.3: Implementation Order
**Given** the implementation plan is created
**When** the plan content is read
**Then** it specifies the order in which files should be created
**And** dependencies are respected (e.g., `store.py` before `cli.py` if cli imports store)

#### AC-003.4: Function/Class Specifications
**Given** the implementation plan is created
**When** the plan content is read
**Then** each file has key functions/classes listed
**And** `store.py` includes: `load_tasks()`, `save_tasks()`, `add_task()`, `mark_done()`
**And** `cli.py` includes: `main()`, argparse setup with subcommands

### Notes

- The plan quality directly impacts coding phase success
- Edge case: If goal is ambiguous, plan should make reasonable assumptions and document them
- The plan should be readable by both the coding agent and human reviewers

### Priority

**Should Have** - Improves coding phase success rate

---

## User Story 4: Coding Phase File Creation

### US-004: Create All Planned Files

**As a** PhaseRunner coding agent
**I want** to create all files specified in the implementation plan
**So that** the todolist package is complete and functional

### Acceptance Criteria

#### AC-004.1: Plan Reading
**Given** the coding phase starts
**When** the agent begins execution
**Then** it reads `implementation_plan.md` using `fs_read_file`
**And** extracts the list of files to create

#### AC-004.2: Package Directory Structure
**Given** the plan specifies a `todo/` package
**When** files are created
**Then** the `todo/` directory is created first
**And** `__init__.py` is created to mark it as a package

#### AC-004.3: Complete File Contents
**Given** each file in the plan
**When** the file is created using `fs_write_file`
**Then** the file contains complete, working implementation
**And** imports are correct and resolve within the package
**And** no placeholder or TODO comments are left unimplemented

#### AC-004.4: Verification of Creation
**Given** all files are created
**When** the agent runs `fs_list_dir`
**Then** all planned files are confirmed to exist
**And** the agent reports "Coding Complete" only after verification

### Notes

- The coding prompt truncates long goals to 500 chars - ensure key requirements are in first 500 chars
- The agent should handle file creation errors gracefully
- Edge case: If a file already exists, it should be overwritten with the new implementation

### Priority

**Must Have** - Core functionality for package creation

---

## User Story 5: Verification Phase Validation

### US-005: Verify Package Functionality

**As a** PhaseRunner verification agent
**I want** to verify the created package works correctly
**So that** only functional code passes the sprint

### Acceptance Criteria

#### AC-005.1: File Existence Check
**Given** the verification phase starts
**When** the agent runs `fs_list_dir`
**Then** all expected files from the implementation plan are present
**And** the package structure matches the goal requirements

#### AC-005.2: Plan Comparison
**Given** the files are listed
**When** the agent reads `implementation_plan.md`
**Then** it compares the created files against the planned files
**And** identifies any missing files

#### AC-005.3: CLI Execution Test
**Given** the package exists
**When** the agent creates and runs a test script
**Then** the test exercises `python -m todo add "Test"`, `python -m todo list`, `python -m todo done 1`
**And** each command's success/failure is recorded

#### AC-005.4: Success/Failure Reporting
**Given** verification tests are complete
**When** all tests pass
**Then** the agent returns "VERIFICATION_SUCCESS"
**When** any test fails
**Then** the agent returns "VERIFICATION_FAILURE" with details about what failed

#### AC-005.5: Evaluator Integration
**Given** the verification phase produces output
**When** evaluators run on the workspace
**Then** `RuffLintEvaluator` checks for Python syntax/style issues
**And** `PytestEvaluator` runs any test files (if present)
**And** both agent verification AND evaluators must pass for sprint success

### Notes

- The verification prompt is truncated to 300 chars for goal context - critical requirements must be early
- Retry loop (MAX_RETRIES=3) provides multiple attempts on failure
- Feedback from failed evaluators is fed back to the next attempt via `FeedbackMemory`

### Priority

**Must Have** - Quality gate for sprint completion

---

## User Story 6: Improved Sprint Goal Prompt

### US-006: Optimize Sprint Goal for Agent Success

**As a** product owner
**I want** the sprint goal to be optimized for AI agent comprehension
**So that** the success rate of automated builds increases

### Acceptance Criteria

#### AC-006.1: Clear Package Structure
**Given** the sprint goal text
**When** read by the discovery agent
**Then** the package name and structure are unambiguous
**And** the goal explicitly states: `todo/` directory with `__init__.py`, `cli.py`, `store.py`, `__main__.py`

#### AC-006.2: Command Specification
**Given** the sprint goal text
**When** read by the coding agent
**Then** each CLI command is clearly defined:
- `add TITLE` - Add a new task
- `list` - Show all tasks
- `done ID` - Mark task as done

#### AC-006.3: Storage Specification
**Given** the sprint goal text
**When** read by the coding agent
**Then** the storage location is explicit: `~/.todo_test.json`
**And** the format is specified: JSON file

#### AC-006.4: Execution Method
**Given** the sprint goal text
**When** read by the coding agent
**Then** the execution method is clear: `python -m todo <command>`
**And** this implies `__main__.py` is required

#### AC-006.5: No External Dependencies Constraint
**Given** the sprint goal text
**When** read by the coding agent
**Then** the constraint "no external deps" is explicit
**And** this means only Python standard library is used

### Recommended Sprint Goal Format

```
Create a Python CLI todo list manager with the following requirements:

1. Package structure: todo/ with __init__.py, cli.py, store.py, __main__.py
2. Commands via argparse (no external deps):
   - add TITLE: Add a new task
   - list: Show all tasks
   - done ID: Mark task as done
3. Storage: JSON file at ~/.todo_test.json
4. Run via: python -m todo <command>

Keep it minimal but functional.
```

### Notes

- The current `TODOLIST_GOAL` in the test file is already well-structured
- Key information must appear in first 300-500 chars due to prompt truncation
- Avoid ambiguous terms; be explicit about file names and paths

### Priority

**Should Have** - Improves success rate without code changes

---

## Requirements Summary

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-001 | Package creates `todo/__init__.py` | Must Have |
| FR-002 | Package creates `todo/cli.py` with argparse | Must Have |
| FR-003 | Package creates `todo/store.py` with JSON persistence | Must Have |
| FR-004 | Package creates `todo/__main__.py` for module execution | Must Have |
| FR-005 | CLI `add` command adds task to storage | Must Have |
| FR-006 | CLI `list` command displays all tasks | Must Have |
| FR-007 | CLI `done` command marks task complete | Must Have |
| FR-008 | Storage file at `~/.todo_test.json` | Must Have |
| FR-009 | No external dependencies required | Must Have |
| FR-010 | Discovery creates `implementation_plan.md` | Must Have |

### Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-001 | Sprint completes within 300 seconds | Must Have |
| NFR-002 | All CLI commands exit with code 0 on success | Must Have |
| NFR-003 | Code passes Ruff lint checks | Should Have |
| NFR-004 | Verification phase retries up to 3 times | Must Have |
| NFR-005 | WebSocket events broadcast phase transitions | Should Have |

### Constraints

- PhaseRunner truncates goal to 500 chars in coding prompt, 300 chars in verification
- Only Python standard library modules allowed
- Browser automation requires `agent-browser` CLI installed
- Backend must be running at localhost:8000
- Frontend must be running at localhost:3000

### Assumptions

- Python 3.10+ is available in the execution environment
- The workspace directory has write permissions
- Home directory exists and is writable for `~/.todo_test.json`
- Network connectivity exists for backend/frontend communication

### Dependencies

- PhaseRunner (`backend/app/runners/phase_runner.py`)
- Evaluators (`backend/app/runners/evaluators/`)
- Agent filesystem tools (`fs_write_file`, `fs_read_file`, `fs_list_dir`)
- AssistantAgent for browser automation
- WebSocket manager for event broadcasting

### Out of Scope

- GUI/web interface for the todo list
- Database storage (SQLite, PostgreSQL)
- User authentication
- Task priorities, due dates, or categories
- Multiple todo lists
- Task editing (only add, list, done)
- Cross-platform path handling beyond basic home directory

---

## Test Validation Checklist

Before marking sprint prompt improvements complete:

- [ ] `TODOLIST_GOAL` contains all 4 required files explicitly
- [ ] Storage path `~/.todo_test.json` is specified
- [ ] Commands `add`, `list`, `done` are clearly defined
- [ ] "No external deps" constraint is included
- [ ] Execution method `python -m todo` is specified
- [ ] Integration test `test_todolist_sprint_via_browser` passes
- [ ] Integration test `test_todolist_sprint_api_direct` passes
- [ ] All CLI commands return exit code 0
- [ ] `list` output contains added task text
