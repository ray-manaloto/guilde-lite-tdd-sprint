# System Design: Sprint Interview-to-Code Integration Test

**Feature:** Integration test for the sprint interview to code completed and validated workflow
**Priority:** P0
**Target Execution Time:** < 5 minutes

## 1. Overview

This design document describes the architecture for a comprehensive integration test that validates the complete sprint workflow from planning interview through code execution and validation.

### 1.1 Workflow Under Test

```
Planning Interview --> Spec Generation --> Sprint Creation --> PhaseRunner Execution --> Code Validation
        |                    |                   |                     |                      |
   AI Questions        Store Q&A         Link Spec to         Discovery/Coding/       Execute & Verify
   (dual-provider)     Artifacts          Sprint             Verification Loop         Artifacts
```

### 1.2 Test Goals

1. Validate the complete end-to-end sprint workflow using direct service calls
2. Verify dual-provider AI execution (OpenAI + Anthropic) with judge selection
3. Confirm AgentTddService metadata and checkpointing works correctly
4. Ensure file artifacts are created and executable
5. Execute in under 5 minutes

## 2. Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                              INTEGRATION TEST HARNESS                             |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +-------------------------+     +-------------------------+                      |
|  |    Test Orchestrator    |---->|     Cleanup Manager     |                      |
|  |  (pytest fixture setup) |     | (artifacts, DB cleanup) |                      |
|  +-------------------------+     +-------------------------+                      |
|              |                                                                    |
|              v                                                                    |
|  +-----------------------------------------------------------------------------------+
|  |                           TEST EXECUTION PHASES                               |
|  +-----------------------------------------------------------------------------------+
|  |                                                                               |
|  |  Phase 1: Planning Interview                                                  |
|  |  +------------------+     +------------------+     +------------------+        |
|  |  |   SpecService    |---->|  run_planning_   |---->|  Dual Subagent   |        |
|  |  | create_with_     |     |  interview()     |     |  Execution       |        |
|  |  | planning()       |     |                  |     |  (OpenAI +       |        |
|  |  +------------------+     +------------------+     |   Anthropic)     |        |
|  |          |                                         +------------------+        |
|  |          v                                                 |                  |
|  |  +------------------+                              +------------------+        |
|  |  |  Questions       |<-----------------------------| Planning Judge   |        |
|  |  |  Generated       |                              | (LLM selection)  |        |
|  |  +------------------+                              +------------------+        |
|  |          |                                                                    |
|  |          v                                                                    |
|  |  Phase 2: Answer Planning Questions                                           |
|  |  +------------------+     +------------------+                                 |
|  |  | save_planning_   |---->|  Spec Updated    |                                 |
|  |  | answers()        |     |  status=answered |                                 |
|  |  +------------------+     +------------------+                                 |
|  |          |                                                                    |
|  |          v                                                                    |
|  |  Phase 3: Sprint Creation                                                     |
|  |  +------------------+     +------------------+                                 |
|  |  |  SprintService   |---->|  Sprint Created  |                                 |
|  |  |  create()        |     |  (linked to spec)|                                 |
|  |  +------------------+     +------------------+                                 |
|  |          |                                                                    |
|  |          v                                                                    |
|  |  Phase 4: PhaseRunner Execution                                               |
|  |  +------------------+     +------------------+     +------------------+        |
|  |  |  PhaseRunner     |---->| AgentTddService  |---->| SprintAgent      |        |
|  |  |  .start()        |     | .execute()       |     | (filesystem      |        |
|  |  +------------------+     +------------------+     |  tools)          |        |
|  |          |                        |               +------------------+        |
|  |          |                        |                       |                   |
|  |          |                        v                       v                   |
|  |          |               +------------------+     +------------------+        |
|  |          |               | Checkpoints      |     | File Artifacts   |        |
|  |          |               | (start, candidate|     | (hello.py, etc.) |        |
|  |          |               |  decision)       |     +------------------+        |
|  |          |               +------------------+                                 |
|  |          v                                                                    |
|  |  Phase 5: Validation                                                          |
|  |  +------------------+     +------------------+     +------------------+        |
|  |  |  Artifact        |---->|  File Execution  |---->|  Output          |        |
|  |  |  Discovery       |     |  (subprocess)    |     |  Verification    |        |
|  |  +------------------+     +------------------+     +------------------+        |
|  |                                                                               |
|  +-------------------------------------------------------------------------------+
|                                                                                   |
+-----------------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------------+
|                              EXTERNAL DEPENDENCIES                                |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +------------------+     +------------------+     +------------------+           |
|  |  PostgreSQL      |     |  OpenAI API      |     |  Anthropic API   |           |
|  |  (async session) |     |  (real calls)    |     |  (real calls)    |           |
|  +------------------+     +------------------+     +------------------+           |
|                                                                                   |
|  +------------------+     +------------------+                                    |
|  |  Filesystem      |     |  WebSocket       |                                    |
|  |  (artifacts dir) |     |  (ConnectionMgr) |                                    |
|  +------------------+     +------------------+                                    |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

## 3. Component Responsibilities

### 3.1 Test Orchestrator

**Purpose:** Manage test lifecycle, coordinate phases, handle timeouts

**Responsibilities:**
- Initialize test fixtures (database session, artifacts directory)
- Execute test phases sequentially with timeout enforcement
- Collect metrics and telemetry from each phase
- Handle cleanup on success and failure

### 3.2 Cleanup Manager

**Purpose:** Ensure clean test environment before and after execution

**Responsibilities:**
- Clear artifacts directory (with safety checks for non-tmp paths)
- Roll back database transactions on test completion
- Clean up any orphaned sprint/spec records

### 3.3 SpecService Integration

**Purpose:** Create specs and run planning interviews

**API Contract:**
```python
async def create_with_planning(
    spec_in: SpecCreate,
    *,
    max_questions: int = 5,
) -> tuple[Spec, dict]:
    """
    Input:
        spec_in.task: str - The task description
        spec_in.title: str | None - Optional title
        max_questions: int - Maximum planning questions to generate

    Output:
        Spec - Created spec with status=DRAFT
        dict - Planning result with keys:
            - status: "needs_answers"
            - questions: list[dict] - Generated questions
            - answers: [] - Empty initially
            - metadata: dict - AI execution metadata
    """
```

### 3.4 Planning Interview (ralph_planner)

**Purpose:** Generate clarifying questions using dual-provider AI

**API Contract:**
```python
async def run_planning_interview(
    prompt: str,
    *,
    max_questions: int = 5,
    provider: str | None = None,
    model_name: str | None = None,
) -> PlanningInterviewResult:
    """
    Input:
        prompt: str - The sprint/task description
        max_questions: int - Maximum questions to generate

    Output:
        PlanningInterviewResult:
            questions: list[dict[str, str]] - Generated questions with rationale
            metadata: dict - Execution metadata including:
                - mode: "dual_subagent" | "single" | "stub"
                - candidates: list[dict] - Per-provider results
                - judge: dict - Judge selection metadata
                - selected_candidate: dict - Winning provider info
    """
```

### 3.5 AgentTddService

**Purpose:** Execute multi-provider AI runs with checkpointing

**API Contract:**
```python
async def execute(
    data: AgentTddRunCreate,
    *,
    user_id: UUID | None,
) -> AgentTddRunResult:
    """
    Input:
        data.message: str - Prompt for the agent
        data.workspace_ref: str | None - Reference for artifact storage
        data.metadata: dict - Additional context (sprint_id, phase, agent_type)
        data.subagents: list[AgentTddSubagentConfig] - Provider configs

    Output:
        AgentTddRunResult:
            run: AgentRunRead - Run record with status, workspace_ref
            candidates: list[AgentCandidateRead] - Per-provider outputs
            decision: AgentDecisionRead | None - Judge selection
            checkpoints: list[AgentCheckpointRead] - Execution checkpoints
            errors: list[AgentTddSubagentError] - Any provider failures
    """
```

### 3.6 PhaseRunner

**Purpose:** Orchestrate sprint execution phases (Discovery, Coding, Verification)

**API Contract:**
```python
@classmethod
async def start(cls, sprint_id: UUID) -> None:
    """
    Input:
        sprint_id: UUID - Sprint to execute

    Side Effects:
        - Updates sprint status: PLANNED -> ACTIVE -> COMPLETED/FAILED
        - Creates files in AUTOCODE_ARTIFACTS_DIR/{workspace_ref}/
        - Broadcasts status via WebSocket (room = sprint_id)

    Phases:
        1. Discovery: Analyze requirements, create implementation_plan.md
        2. Coding: Implement code based on plan (up to MAX_RETRIES attempts)
        3. Verification: Run tests, check for VERIFICATION_SUCCESS
    """
```

### 3.7 SprintAgent

**Purpose:** AI agent with filesystem and test execution tools

**Registered Tools:**
```python
- fs_read_file(path: str) -> str      # Read file from workspace
- fs_write_file(path: str, content: str) -> str  # Write file to workspace
- fs_list_dir(path: str = ".") -> str  # List workspace directory
- run_tests(path: str | None) -> str   # Execute pytest in workspace
```

## 4. State Management

### 4.1 Database State

```
Spec Table:
  - id: UUID (primary key)
  - status: DRAFT | VALIDATED
  - task: str
  - title: str
  - artifacts: JSON {
      assessment: {...},
      planning: {
        status: "needs_answers" | "answered",
        questions: [...],
        answers: [...],
        metadata: {...}
      }
    }

Sprint Table:
  - id: UUID (primary key)
  - spec_id: UUID (foreign key)
  - status: PLANNED | ACTIVE | COMPLETED | FAILED
  - name: str
  - goal: str

AgentRun Table:
  - id: UUID
  - workspace_ref: str (links to filesystem)
  - status: pending | running | completed | failed
  - input_payload: JSON
  - model_config: JSON

AgentCandidate Table:
  - id: UUID
  - run_id: UUID (foreign key)
  - provider: str
  - model_name: str
  - output: str
  - tool_calls: JSON
  - metrics: JSON

AgentCheckpoint Table:
  - id: UUID
  - run_id: UUID (foreign key)
  - sequence: int
  - label: str (start | candidate:{name} | decision)
  - state: JSON
```

### 4.2 Filesystem State

```
AUTOCODE_ARTIFACTS_DIR/
  {workspace_ref}/
    implementation_plan.md    # Created in Discovery phase
    hello.py                  # Created in Coding phase
    test_*.py                 # Optional test files
```

### 4.3 Test State Machine

```
Test Start
    |
    v
[Initialize Fixtures]
    |
    +-- db_session created
    +-- artifacts_dir cleaned
    |
    v
[Phase 1: Planning Interview]
    |
    +-- Spec created
    +-- Planning interview executed (dual-provider)
    +-- Questions generated
    |
    v
[Phase 2: Answer Questions]
    |
    +-- Answers provided
    +-- Spec status = answered
    |
    v
[Phase 3: Create Sprint]
    |
    +-- Sprint created (linked to spec)
    +-- Sprint status = PLANNED
    |
    v
[Phase 4: Execute PhaseRunner]
    |
    +-- Discovery phase
    +-- Coding phase (up to 3 retries)
    +-- Verification phase
    +-- Sprint status = COMPLETED | FAILED
    |
    v
[Phase 5: Validate Artifacts]
    |
    +-- Find generated files
    +-- Execute code
    +-- Verify output
    |
    v
[Cleanup]
    |
    +-- Rollback DB transaction
    +-- (Optional) Clean artifacts
    |
    v
Test Complete
```

## 5. Error Handling and Cleanup Patterns

### 5.1 Test Fixture Cleanup

```python
@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Database session with automatic rollback."""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()  # Always rollback - test isolation
            await session.close()
            await engine.dispose()

@pytest.fixture
def clean_artifacts_dir():
    """Clean artifacts directory with safety checks."""
    artifacts_dir = settings.AUTOCODE_ARTIFACTS_DIR
    if artifacts_dir and artifacts_dir.exists():
        # Safety: Only clean directories that look like test directories
        if "tmp" in str(artifacts_dir) or "guilde-lite-tdd-sprint-filesystem" in str(artifacts_dir):
            shutil.rmtree(artifacts_dir)

    if artifacts_dir:
        artifacts_dir.mkdir(parents=True, exist_ok=True)

    yield artifacts_dir

    # Post-test: Keep artifacts for debugging (optional cleanup)
```

### 5.2 Timeout Handling

```python
@pytest.mark.timeout(300)  # 5 minute hard timeout
async def test_sprint_interview_to_code_workflow(...):
    # Phase-specific soft timeouts via asyncio.wait_for
    planning_result = await asyncio.wait_for(
        spec_service.create_with_planning(spec_in, max_questions=3),
        timeout=60.0  # 1 minute for planning
    )

    # PhaseRunner has internal retry logic (MAX_RETRIES=3)
    # Each phase has implicit timeouts via agent execution limits
```

### 5.3 Error Recovery

```python
# Planning interview failure
if not planning.get("questions"):
    pytest.fail("Planning interview produced no questions")

# PhaseRunner failure
sprint = await sprint_service.get_by_id(sprint_id)
if sprint.status == SprintStatus.FAILED:
    # Collect diagnostics
    checkpoints = await collect_checkpoints(sprint_id)
    artifacts = list(artifacts_dir.rglob("*"))
    pytest.fail(f"Sprint failed. Checkpoints: {checkpoints}, Artifacts: {artifacts}")

# Code execution failure
result = subprocess.run(["python3", hello_path], capture_output=True, text=True, timeout=10)
if result.returncode != 0:
    pytest.fail(f"Code execution failed: {result.stderr}")
```

## 6. Test Fixtures and Setup Requirements

### 6.1 Required Fixtures

```python
# conftest.py additions

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Real database session with rollback."""
    # Existing implementation

@pytest.fixture
def clean_artifacts_dir():
    """Clean and provide artifacts directory."""
    # As described above

@pytest.fixture
def validate_dual_provider_config():
    """Ensure dual-provider settings are configured."""
    if not settings.DUAL_SUBAGENT_ENABLED:
        pytest.skip("DUAL_SUBAGENT_ENABLED must be True")

    settings.validate_dual_subagent_settings()  # Raises if misconfigured
    yield
```

### 6.2 Test Data Factories

```python
def create_hello_world_spec() -> SpecCreate:
    """Standard hello world spec for testing."""
    return SpecCreate(
        task="Create a Python script that prints 'hello world' to stdout.",
        title="Hello World Integration Test",
    )

def create_simple_answers(questions: list[dict]) -> list[SpecPlanningAnswer]:
    """Generate simple answers for planning questions."""
    answers = []
    for q in questions:
        question_text = q.get("question", "")
        # Deterministic answer mapping based on keywords
        if "user" in question_text.lower() or "audience" in question_text.lower():
            answer = "The user is a developer testing the system."
        elif "success" in question_text.lower():
            answer = "Success is when the script prints 'hello world' when executed."
        elif "scope" in question_text.lower():
            answer = "Only printing 'hello world' is in scope."
        elif "constraint" in question_text.lower():
            answer = "No constraints. Standard Python 3 only."
        else:
            answer = "Keep it simple - just print 'hello world'."

        answers.append(SpecPlanningAnswer(question=question_text, answer=answer))
    return answers
```

## 7. Validation Assertions

### 7.1 Planning Interview Validation

```python
# Dual-provider execution
assert len(planning_metadata.get("candidates", [])) >= 2
providers = [c.get("provider") for c in planning_metadata.get("candidates", [])]
assert "openai" in providers, "OpenAI candidate missing"
assert "anthropic" in providers, "Anthropic candidate missing"

# Judge selection
judge = planning_metadata.get("judge", {})
assert judge.get("model_name") is not None, "Judge model not recorded"

# Selected candidate
selected = planning_metadata.get("selected_candidate", {})
assert selected.get("provider") in ["openai", "anthropic"]
```

### 7.2 AgentTddService Validation

```python
# Checkpoints exist
assert len(result.checkpoints) > 0
labels = [cp.label for cp in result.checkpoints]
assert "start" in labels
assert any(l.startswith("candidate:") for l in labels)
if result.decision:
    assert "decision" in labels

# Candidates have required fields
for candidate in result.candidates:
    assert candidate.provider is not None
    assert candidate.model_name is not None
    assert candidate.metrics is not None
    assert "duration_ms" in candidate.metrics
```

### 7.3 Artifact Validation

```python
# File exists
hello_files = list(artifacts_dir.rglob("hello.py"))
assert len(hello_files) > 0, "hello.py not found"

# File is executable
result = subprocess.run(
    ["python3", str(hello_files[0])],
    capture_output=True,
    text=True,
    timeout=10
)
assert result.returncode == 0
assert "hello world" in result.stdout.lower()
```

## 8. Performance Considerations

### 8.1 Time Budget (Target: < 5 minutes)

| Phase | Target Time | Notes |
|-------|-------------|-------|
| Planning Interview | 60s | Dual-provider + judge selection |
| Answer Questions | 5s | Simple database operation |
| Create Sprint | 5s | Database + validation |
| PhaseRunner Discovery | 45s | Single AI call |
| PhaseRunner Coding | 45s per attempt | Up to 3 attempts = 135s max |
| PhaseRunner Verification | 30s per attempt | Up to 3 attempts = 90s max |
| Artifact Validation | 5s | File I/O + subprocess |
| **Total** | **~300s (5 min)** | With retry overhead |

### 8.2 Optimization Strategies

1. **Limit planning questions to 3**: Reduces AI call overhead
2. **Use focused prompts**: Simple hello world task minimizes AI reasoning time
3. **Single retry for tests**: Override MAX_RETRIES=1 for test speed (optional)
4. **Parallel candidate execution**: AgentTddService already uses asyncio.gather

## 9. Mock vs Real Service Boundaries

### 9.1 Real Services (No Mocking)

| Service | Justification |
|---------|---------------|
| SpecService | Core business logic under test |
| SprintService | Core business logic under test |
| AgentTddService | Multi-provider orchestration under test |
| PhaseRunner | Workflow coordination under test |
| Database (PostgreSQL) | State persistence critical |
| Filesystem | Artifact creation is a key requirement |
| OpenAI API | Real AI behavior needed for validation |
| Anthropic API | Real AI behavior needed for validation |

### 9.2 Mocked/Stubbed (Optional)

| Component | When to Mock |
|-----------|--------------|
| WebSocket manager | If connection broadcast is not under test |
| Telemetry/Logfire | For faster execution, disable telemetry |

### 9.3 Configuration for Test Mode

```python
# Settings overrides for test execution
PLANNING_INTERVIEW_MODE = "live"  # NOT "stub" - we want real AI
DUAL_SUBAGENT_ENABLED = True      # Required for dual-provider test
AGENT_FS_ENABLED = True           # Required for file creation
```

## 10. Test Implementation Outline

```python
@pytest.mark.anyio
@pytest.mark.timeout(300)
async def test_sprint_interview_to_code_complete_workflow(
    db_session: AsyncSession,
    clean_artifacts_dir: Path,
    validate_dual_provider_config,
):
    """
    Complete integration test: Planning Interview -> Code Validated

    Requirements validated:
    1. Planning interview generates questions with dual-provider execution
    2. Spec stores planning questions and answers
    3. Sprint links to spec and executes via PhaseRunner
    4. AgentTddService creates checkpoints and tracks metadata
    5. Code artifacts are created and executable
    """
    spec_service = SpecService(db_session)
    sprint_service = SprintService(db_session)

    # === Phase 1: Planning Interview ===
    spec, planning = await spec_service.create_with_planning(
        create_hello_world_spec(),
        max_questions=3,
    )
    await db_session.commit()

    assert_planning_dual_provider(planning)

    # === Phase 2: Answer Questions ===
    answers = create_simple_answers(planning.get("questions", []))
    spec, updated_planning = await spec_service.save_planning_answers(spec.id, answers)
    await db_session.commit()

    assert updated_planning.get("status") == "answered"

    # === Phase 3: Create Sprint ===
    sprint = await sprint_service.create(
        SprintCreate(
            name="Integration Test Sprint",
            goal="Create a Python script that prints 'hello world'",
            spec_id=spec.id,
        )
    )
    await db_session.commit()

    assert sprint.spec_id == spec.id

    # === Phase 4: Execute PhaseRunner ===
    await PhaseRunner.start(sprint.id)

    # Refresh sprint to get final status
    await db_session.refresh(sprint)

    # === Phase 5: Validate ===
    if sprint.status != SprintStatus.COMPLETED:
        collect_and_fail_with_diagnostics(sprint, clean_artifacts_dir)

    assert_artifacts_valid(clean_artifacts_dir)
```

## 11. Appendix: Schema Definitions

### AgentTddRunCreate

```python
class AgentTddRunCreate(BaseSchema):
    message: str
    history: list[dict[str, str]] = []
    run_id: UUID | None = None
    checkpoint_id: UUID | None = None
    subagents: list[AgentTddSubagentConfig] = []
    judge: AgentTddJudgeConfig | None = None
    workspace_ref: str | None = None
    metadata: dict[str, Any] = {}
    fork_label: str | None = None
    fork_reason: str | None = None
```

### AgentTddRunResult

```python
class AgentTddRunResult(BaseSchema):
    run: AgentRunRead
    candidates: list[AgentCandidateRead]
    decision: AgentDecisionRead | None = None
    checkpoints: list[AgentCheckpointRead] = []
    errors: list[AgentTddSubagentError] = []
```

### SpecPlanningAnswer

```python
class SpecPlanningAnswer(BaseSchema):
    question: str
    answer: str
```

### SprintStatus

```python
class SprintStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
```
