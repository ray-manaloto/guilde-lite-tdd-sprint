# Workflow Tracking & Checkpointing System

## Overview

This specification defines a comprehensive workflow tracking system that enables:
- Full execution timeline with start/end timestamps for every phase
- Disk-based persistence of all artifacts (specs, questionnaires, judge results, code)
- Logfire trace linking for observability
- Checkpoint-based branching to rewind and adjust workflow at any point

## Goals

1. **Complete Auditability** - Track every step with timestamps and metadata
2. **Reproducibility** - Rewind to any checkpoint and re-execute with different parameters
3. **Observability** - Link all operations to Logfire traces for debugging
4. **Flexibility** - Branch off checkpoints to try different models, judges, or skills

---

## 1. Disk Storage Structure

### Directory Layout

```
{AUTOCODE_ARTIFACTS_DIR}/{sprint_id}/
├── manifest.json                 # Sprint manifest with all references
├── timeline.json                 # Full execution timeline
│
├── spec/
│   ├── spec.json                 # Full spec with all metadata
│   ├── spec.md                   # Human-readable spec document
│   ├── assessment.json           # Complexity assessment
│   └── questionnaire/
│       ├── questions.json        # Generated interview questions
│       ├── candidates/
│       │   ├── openai.json       # OpenAI candidate questions
│       │   └── anthropic.json    # Anthropic candidate questions
│       ├── judge_result.json     # Judge decision on questions
│       ├── answers.json          # User-provided answers
│       └── final_questions.json  # Selected questions after judging
│
├── candidates/
│   ├── discovery/
│   │   ├── openai/
│   │   │   ├── response.json     # Full response
│   │   │   └── metadata.json     # Timestamps, tokens, trace_id
│   │   └── anthropic/
│   │       ├── response.json
│   │       └── metadata.json
│   ├── coding/
│   │   └── ... (same structure)
│   └── verification/
│       └── ... (same structure)
│
├── phases/
│   ├── 01_discovery.json         # Phase execution record
│   ├── 02_coding.json
│   └── 03_verification.json
│
├── checkpoints/
│   ├── cp_001_start.json         # Initial checkpoint
│   ├── cp_002_questions_generated.json
│   ├── cp_003_questions_judged.json
│   ├── cp_004_answers_received.json
│   ├── cp_005_discovery_complete.json
│   ├── cp_006_coding_complete.json
│   └── cp_007_verification_complete.json
│
├── branches/
│   └── {branch_id}/              # Branched execution from checkpoint
│       └── ... (same structure)
│
└── code/
    ├── hello.py                  # Generated code
    ├── test_hello.py             # Generated tests
    └── execution_log.json        # Code execution results
```

### File Formats

#### manifest.json
```json
{
  "version": "1.0.0",
  "sprint_id": "uuid",
  "spec_id": "uuid",
  "created_at": "2026-01-22T01:17:11.154750Z",
  "updated_at": "2026-01-22T01:19:07.284000Z",
  "status": "completed",
  "current_phase": "verification",
  "current_checkpoint": "cp_007_verification_complete",
  "branch_id": null,
  "parent_branch": null,
  "logfire_project_url": "https://logfire-us.pydantic.dev/sortakool/guilde-lite",
  "paths": {
    "spec": "spec/spec.json",
    "timeline": "timeline.json",
    "code": "code/",
    "checkpoints": "checkpoints/"
  }
}
```

#### timeline.json
```json
{
  "sprint_id": "uuid",
  "total_duration_ms": 140250,
  "events": [
    {
      "sequence": 1,
      "event_type": "sprint_started",
      "timestamp": "2026-01-22T01:17:11.154750Z",
      "state": "planned",
      "checkpoint_id": "cp_001_start",
      "trace_id": "019be4923b07d7969a638ca9400c624c",
      "trace_url": "https://logfire-us.pydantic.dev/sortakool/guilde-lite/trace/019be4923b07d7969a638ca9400c624c",
      "metadata": {}
    },
    {
      "sequence": 2,
      "event_type": "phase_started",
      "phase": "questionnaire",
      "timestamp": "2026-01-22T01:17:11.200000Z",
      "state": "active",
      "trace_id": "...",
      "metadata": {
        "model_config": {
          "openai": "openai-responses:gpt-5.2-codex",
          "anthropic": "anthropic:claude-opus-4-5-20251101"
        }
      }
    },
    {
      "sequence": 3,
      "event_type": "candidates_generated",
      "phase": "questionnaire",
      "timestamp": "2026-01-22T01:17:25.000000Z",
      "duration_ms": 13800,
      "candidates": [
        {"provider": "openai", "success": false, "error": "Exceeded max retries"},
        {"provider": "anthropic", "success": true, "questions_count": 1}
      ],
      "trace_id": "..."
    },
    {
      "sequence": 4,
      "event_type": "judge_decision",
      "phase": "questionnaire",
      "timestamp": "2026-01-22T01:17:30.000000Z",
      "checkpoint_id": "cp_003_questions_judged",
      "judge": {
        "model": "openai-responses:gpt-5.2-codex",
        "winner": "anthropic",
        "score": 0.42,
        "rationale": "..."
      },
      "trace_id": "..."
    },
    // ... more events
  ]
}
```

#### Phase Record (phases/01_discovery.json)
```json
{
  "phase": "discovery",
  "sequence": 1,
  "start_time": "2026-01-22T01:17:33.000000Z",
  "end_time": "2026-01-22T01:18:15.000000Z",
  "duration_ms": 42000,
  "status": "completed",
  "checkpoint_before": "cp_004_answers_received",
  "checkpoint_after": "cp_005_discovery_complete",
  "model_config": {
    "model": "anthropic:claude-opus-4-5-20251101",
    "temperature": 0.7
  },
  "input": {
    "task": "Create a Python script...",
    "context": "..."
  },
  "output": {
    "summary": "...",
    "files_planned": ["hello.py", "test_hello.py"]
  },
  "candidates": {
    "openai": {
      "trace_id": "...",
      "start_time": "...",
      "end_time": "...",
      "tokens": {"input": 500, "output": 200}
    },
    "anthropic": {
      "trace_id": "...",
      "start_time": "...",
      "end_time": "...",
      "tokens": {"input": 500, "output": 180}
    }
  },
  "judge_result": {
    "winner": "anthropic",
    "score": 0.85,
    "rationale": "..."
  },
  "trace_id": "019be4923b0b8e8d9586a72164287856",
  "trace_url": "https://logfire-us.pydantic.dev/sortakool/guilde-lite/trace/..."
}
```

#### Checkpoint (checkpoints/cp_003_questions_judged.json)
```json
{
  "checkpoint_id": "cp_003_questions_judged",
  "sequence": 3,
  "label": "questions_judged",
  "created_at": "2026-01-22T01:17:30.000000Z",
  "sprint_state": {
    "status": "active",
    "current_phase": "questionnaire",
    "phases_completed": []
  },
  "spec_snapshot": {
    "id": "uuid",
    "artifacts": { /* full artifacts at this point */ }
  },
  "model_config": {
    "openai_model": "openai-responses:gpt-5.2-codex",
    "anthropic_model": "anthropic:claude-opus-4-5-20251101",
    "judge_model": "openai-responses:gpt-5.2-codex"
  },
  "can_branch": true,
  "branch_options": [
    "change_judge_model",
    "change_candidate_models",
    "regenerate_questions",
    "skip_to_phase"
  ],
  "trace_id": "...",
  "trace_url": "..."
}
```

---

## 2. Timestamp Tracking

### Required Timestamps

Every operation must track:
- `start_time` - ISO 8601 timestamp when operation began
- `end_time` - ISO 8601 timestamp when operation completed
- `duration_ms` - Computed duration in milliseconds

### Implementation Points

1. **Phase Runner** - Track each phase start/end
2. **Candidate Generation** - Track each provider's execution time
3. **Judge Execution** - Track judge model execution time
4. **File Operations** - Track code generation and test execution

### Database Schema Updates

```sql
-- Add to agent_runs table
ALTER TABLE agent_runs ADD COLUMN started_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE agent_runs ADD COLUMN completed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE agent_runs ADD COLUMN duration_ms INTEGER;

-- Add to agent_checkpoints table
ALTER TABLE agent_checkpoints ADD COLUMN phase_start_time TIMESTAMP WITH TIME ZONE;
ALTER TABLE agent_checkpoints ADD COLUMN phase_end_time TIMESTAMP WITH TIME ZONE;
```

---

## 3. Logfire Trace Linking

### Trace ID Propagation

Every artifact must include:
```json
{
  "trace_id": "019be4923b07d7969a638ca9400c624c",
  "span_id": "10dfbbf529a28867",
  "trace_url": "https://logfire-us.pydantic.dev/{project}/trace/{trace_id}"
}
```

### Implementation

```python
from app.core.logfire_setup import get_trace_url

def get_current_trace_info() -> dict:
    """Get current trace context for linking."""
    import logfire
    ctx = logfire.get_current_span_context()
    return {
        "trace_id": ctx.trace_id if ctx else None,
        "span_id": ctx.span_id if ctx else None,
        "trace_url": get_trace_url(ctx.trace_id) if ctx else None
    }
```

---

## 4. Checkpoint & Branching System

### Checkpoint Types

| Checkpoint | Description | Can Branch |
|------------|-------------|------------|
| `start` | Sprint initialized | Yes |
| `questions_generated` | Interview questions created | Yes |
| `questions_judged` | Judge selected winner | Yes |
| `answers_received` | User provided answers | Yes |
| `phase_complete` | Any phase completed | Yes |
| `code_generated` | Code files created | Yes |
| `tests_passed` | Verification complete | No |

### Branching API

```python
class CheckpointService:
    async def create_checkpoint(
        self,
        sprint_id: UUID,
        label: str,
        state: dict,
        can_branch: bool = True
    ) -> Checkpoint:
        """Create a checkpoint at current state."""

    async def branch_from_checkpoint(
        self,
        checkpoint_id: UUID,
        branch_config: BranchConfig
    ) -> Sprint:
        """Create new sprint branch from checkpoint."""

    async def list_checkpoints(
        self,
        sprint_id: UUID
    ) -> list[Checkpoint]:
        """List all checkpoints for a sprint."""

    async def rewind_to_checkpoint(
        self,
        sprint_id: UUID,
        checkpoint_id: UUID
    ) -> Sprint:
        """Rewind sprint to checkpoint state."""
```

### Branch Configuration

```python
@dataclass
class BranchConfig:
    """Configuration for branching from a checkpoint."""
    branch_name: str
    reason: str

    # Model overrides
    openai_model: str | None = None
    anthropic_model: str | None = None
    judge_model: str | None = None

    # Behavior overrides
    skip_phases: list[str] | None = None
    retry_phase: str | None = None
    custom_prompt: str | None = None
```

### Branch Workflow

```
Original Sprint
    │
    ├── cp_001_start
    │
    ├── cp_002_questions_generated
    │
    ├── cp_003_questions_judged ──────┐
    │                                  │
    ├── cp_004_answers_received        │ Branch: "try-gpt4o-judge"
    │                                  │
    ├── cp_005_discovery_complete      ▼
    │                            Branch Sprint
    └── cp_006_coding_complete         │
                                       ├── cp_003_questions_judged (branched)
                                       │   └── judge_model: "openai:gpt-4o"
                                       │
                                       └── ... (continues independently)
```

---

## 5. Services to Implement

### WorkflowTracker Service

```python
class WorkflowTracker:
    """Tracks workflow execution and persists to disk."""

    def __init__(self, sprint_id: UUID, artifacts_dir: Path):
        self.sprint_id = sprint_id
        self.base_dir = artifacts_dir / str(sprint_id)
        self.timeline: list[TimelineEvent] = []

    async def start_sprint(self) -> None:
        """Initialize sprint tracking."""

    async def record_event(
        self,
        event_type: str,
        phase: str | None = None,
        metadata: dict | None = None
    ) -> TimelineEvent:
        """Record a timeline event."""

    async def start_phase(self, phase: str) -> PhaseContext:
        """Start tracking a phase."""

    async def end_phase(self, phase: str, result: dict) -> None:
        """End phase tracking and save."""

    async def create_checkpoint(self, label: str) -> Checkpoint:
        """Create checkpoint at current state."""

    async def save_spec(self, spec: Spec) -> None:
        """Save spec to disk."""

    async def save_questionnaire(self, questions: list, answers: list, judge: dict) -> None:
        """Save questionnaire artifacts."""

    async def save_timeline(self) -> None:
        """Persist timeline to disk."""

    async def get_timeline(self) -> Timeline:
        """Load timeline from disk."""
```

### SpecExporter Service

```python
class SpecExporter:
    """Exports specs to disk in multiple formats."""

    async def export_json(self, spec: Spec, path: Path) -> None:
        """Export spec as JSON."""

    async def export_markdown(self, spec: Spec, path: Path) -> None:
        """Export spec as human-readable Markdown."""

    async def export_questionnaire(
        self,
        questions: list,
        candidates: dict,
        judge_result: dict,
        answers: list,
        path: Path
    ) -> None:
        """Export full questionnaire with all artifacts."""
```

---

## 6. Implementation Plan

### Phase 1: Core Infrastructure
- [ ] Add timestamp columns to database
- [ ] Create WorkflowTracker service
- [ ] Create SpecExporter service
- [ ] Update PhaseRunner to use WorkflowTracker

### Phase 2: Disk Persistence
- [ ] Implement directory structure creation
- [ ] Implement spec export (JSON + Markdown)
- [ ] Implement questionnaire export
- [ ] Implement phase record export

### Phase 3: Timeline & Tracing
- [ ] Implement timeline event recording
- [ ] Add Logfire trace URL generation
- [ ] Implement timeline.json generation
- [ ] Add trace linking to all artifacts

### Phase 4: Checkpointing
- [ ] Implement checkpoint creation
- [ ] Implement checkpoint listing
- [ ] Implement checkpoint state snapshots
- [ ] Add branch configuration schema

### Phase 5: Branching
- [ ] Implement branch creation from checkpoint
- [ ] Implement model override on branch
- [ ] Implement rewind functionality
- [ ] Add branch comparison tools

---

## 7. API Endpoints

### Timeline API

```
GET  /api/v1/sprints/{sprint_id}/timeline
GET  /api/v1/sprints/{sprint_id}/timeline/events
GET  /api/v1/sprints/{sprint_id}/checkpoints
POST /api/v1/sprints/{sprint_id}/checkpoints/{checkpoint_id}/branch
POST /api/v1/sprints/{sprint_id}/rewind/{checkpoint_id}
```

### Artifacts API

```
GET  /api/v1/sprints/{sprint_id}/artifacts
GET  /api/v1/sprints/{sprint_id}/artifacts/spec
GET  /api/v1/sprints/{sprint_id}/artifacts/questionnaire
GET  /api/v1/sprints/{sprint_id}/artifacts/phases/{phase}
GET  /api/v1/sprints/{sprint_id}/artifacts/code
```

---

## 8. Success Criteria

1. **Auditability**: Can reconstruct exact workflow from disk artifacts
2. **Traceability**: Every operation links to Logfire trace
3. **Reproducibility**: Can rewind to any checkpoint and re-execute
4. **Flexibility**: Can branch and try different models/configurations
5. **Persistence**: All artifacts survive process restart

---

## References

- Logfire Documentation: https://logfire.pydantic.dev/docs
- PydanticAI Agents: https://ai.pydantic.dev/agents
- Current PhaseRunner: `backend/app/runners/phase_runner.py`
- Current Spec Service: `backend/app/services/spec.py`
