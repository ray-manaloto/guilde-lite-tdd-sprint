# SDLC Hooks and State Persistence Design

## Executive Summary

This document describes the complete hooks and state persistence system for SDLC orchestration. The design provides:

1. **Stop Hook** - Verifies task completion (tests pass, lint clean, docs synced)
2. **SubagentStop Hook** - Aggregates parallel research results
3. **Session Checkpoints** - Enables crash recovery
4. **Pre-commit Validation** - Quality gates before commits
5. **Documentation Sync Tracking** - Keeps code and docs in sync

---

## Design Artifacts

### 1. Enhanced Hooks Configuration

**File:** `.claude/plugins/sdlc-orchestration/hooks/hooks-enhanced.json`

This is the complete hooks.json configuration with all hook types:

| Hook Type | Purpose | Triggers |
|-----------|---------|----------|
| SessionStart | Recovery detection, plugin banner | Session begins |
| SessionStop | Checkpoint creation | Session ends |
| Stop | Task completion validation | Claude response complete |
| SubagentStop | Parallel agent result aggregation | Subagent completes |
| UserPromptSubmit | Workflow detection, phase gates | User sends prompt |
| PreToolUse | Tool blocking, pre-commit checks | Before tool executes |
| PostToolUse | Backpressure validation, state updates | After tool completes |
| PhaseTransition | Checkpoint creation, state updates | Phase changes |

### 2. State File Schemas

**File:** `.claude/plugins/sdlc-orchestration/schemas/state-schemas.json`

Complete JSON schemas for all state files:

| State File | Purpose | Lifecycle |
|------------|---------|-----------|
| sdlc-state.json | Main workflow state | Created on workflow start |
| sdlc-checkpoint.json | Crash recovery snapshot | Created on session end |
| sdlc-stop-validation.json | Task completion checks | Created on Stop hook |
| sdlc-agent-outputs.json | Aggregated agent results | Updated per agent |
| sdlc-research-results.json | Research aggregation | Updated during research |
| sdlc-doc-sync.json | Documentation tracking | Updated on file changes |

### 3. Quality Gates Documentation

**File:** `.claude/plugins/sdlc-orchestration/docs/quality-gates.md`

Comprehensive quality gate configuration:

- Code quality gates (lint, type, format)
- Test gates (unit, coverage, integration)
- Documentation gates (sync, API docs, README)
- Phase gates (requirements -> release)
- Deployment gates (release phase only)

### 4. Recovery Workflow Documentation

**File:** `.claude/plugins/sdlc-orchestration/docs/recovery-workflow.md`

Complete crash recovery procedures:

- Automatic checkpointing
- Recovery scenarios
- State transitions
- Manual recovery procedures
- Troubleshooting guide

---

## Hook Configuration Details

### Stop Hook

The Stop hook runs when Claude completes a response to verify task completion.

**Validation Sequence:**
1. Initialize validation file with timestamp
2. Run backend tests (`uv run pytest`)
3. Run lint check (`ruff check`)
4. Check documentation sync state
5. Aggregate results and inject warnings

**Configuration:**
```json
{
  "Stop": [
    {
      "matcher": "",
      "hooks": [
        { "type": "command", "command": "...", "timeout": 5 },    // Initialize
        { "type": "command", "command": "...", "timeout": 120 },  // Tests
        { "type": "command", "command": "...", "timeout": 30 },   // Lint
        { "type": "command", "command": "...", "timeout": 5 },    // Doc sync
        { "type": "command", "command": "...", "timeout": 5 }     // Aggregate
      ]
    }
  ]
}
```

**Output Example:**
```
[SDLC STOP VALIDATION]

Task completion checks:
- Tests are failing
- Lint issues detected

Recommendation: Address these issues before marking task complete.
```

### SubagentStop Hook

The SubagentStop hook runs when an SDLC agent completes, enabling result aggregation.

**Features:**
1. Track agent completions in state file
2. Aggregate research results (for parallel research)
3. Detect phase completion (all agents done)
4. Prompt for result synthesis

**Configuration:**
```json
{
  "SubagentStop": [
    {
      "matcher": "sdlc-orchestration:.*",
      "hooks": [
        { "type": "command", "command": "..." },  // Track completion
        { "type": "command", "command": "..." },  // Research aggregation
        { "type": "command", "command": "..." }   // Phase completion check
      ]
    }
  ]
}
```

**Research Completion Output:**
```
[SDLC RESEARCH COMPLETE]

All 3 research agents have completed. Ready to aggregate findings:
- Research Scientist
- Business Analyst
- Software Architect

Create a consolidated research summary combining all agent outputs.
```

### Session Checkpoints

Automatic checkpointing on session end when work is in progress.

**SessionStop Hook:**
```json
{
  "SessionStop": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c '... create checkpoint if phase is in_progress ...'",
          "timeout": 10
        }
      ]
    }
  ]
}
```

**SessionStart Hook (Recovery Detection):**
```json
{
  "SessionStart": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c '... detect checkpoint and prompt for recovery ...'",
          "timeout": 5
        }
      ]
    }
  ]
}
```

### Pre-commit Validation

Quality checks before `git commit` commands.

**PreToolUse Bash Hook:**
```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c '... check for git commit and validate quality ...'",
          "timeout": 5
        }
      ]
    }
  ]
}
```

---

## State File Details

### sdlc-state.json

Main workflow state tracking.

```json
{
  "track_id": "user-auth-oauth2",
  "current_phase": "implementation",
  "started_at": "2026-01-22T10:00:00Z",
  "phases": {
    "requirements": {
      "status": "completed",
      "started_at": "2026-01-22T10:00:00Z",
      "completed_at": "2026-01-22T10:30:00Z",
      "agents_completed": ["ceo-stakeholder", "business-analyst", "research-scientist"],
      "artifacts": {},
      "gates_passed": ["all_agents_complete"]
    },
    "design": { "status": "completed", "agents_completed": [...] },
    "implementation": { "status": "in_progress", "agents_completed": ["staff-engineer"] },
    "quality": { "status": "pending", "agents_completed": [] },
    "release": { "status": "pending", "agents_completed": [] }
  },
  "checkpoints": [],
  "handoffs": []
}
```

### sdlc-checkpoint.json

Crash recovery snapshot.

```json
{
  "track_id": "user-auth-oauth2",
  "phase": "implementation",
  "recovery_pending": true,
  "checkpoint_at": "2026-01-22T12:00:00Z",
  "session_id": "a1b2c3d4",
  "current_phase": "implementation",
  "started_at": "2026-01-22T10:00:00Z",
  "phases": { ... },
  "last_agent": "senior-engineer",
  "pending_tasks": ["implement OAuth routes"]
}
```

### sdlc-stop-validation.json

Task completion validation results.

```json
{
  "timestamp": "2026-01-22T12:30:00Z",
  "phase": "implementation",
  "checks": {
    "tests_pass": true,
    "test_output": "42 passed in 3.21s",
    "lint_clean": false,
    "lint_issues": "E501 line too long",
    "docs_synced": true
  },
  "task_complete": false,
  "warnings": "\n- Lint issues detected"
}
```

### sdlc-research-results.json

Parallel research aggregation.

```json
{
  "started_at": "2026-01-22T10:00:00Z",
  "completed_at": "2026-01-22T10:20:00Z",
  "all_complete": true,
  "agents_completed": ["research-scientist", "business-analyst", "software-architect"],
  "findings": {
    "research-scientist": { "completed_at": "...", "technical_feasibility": "..." },
    "business-analyst": { "completed_at": "...", "user_needs": [...] },
    "software-architect": { "completed_at": "...", "architecture_options": [...] }
  },
  "synthesis": {
    "recommendation": "...",
    "next_steps": [...],
    "consensus_score": 95
  }
}
```

---

## Quality Gate Matrix

### Phase Entry Gates

| Phase | Required Gates | Block Level |
|-------|----------------|-------------|
| Design | all_agents_complete, artifacts_validated | Required |
| Implementation | architecture_reviewed, api_contract_approved | Required |
| Quality | code_complete, unit_tests_pass, lint_pass | Required |
| Release | integration_tests_pass, code_review_approved | Required |
| Production | staging_deployed, canary_validated, docs_updated | Required |

### Automatic Gate Passing

| Gate | Auto-Pass Trigger |
|------|-------------------|
| unit_tests_pass | Stop hook tests_pass: true |
| lint_pass | Stop hook lint_clean: true |
| all_agents_complete | SubagentStop count matches expected |
| docs_synced | Doc sync state shows pending_sync: false |

### Manual Gate Approval

| Gate | Approval Required From |
|------|------------------------|
| stakeholder_approved | User confirmation |
| architecture_reviewed | Architect agent |
| code_review_approved | Reviewer agent |
| production_approved | User confirmation |

---

## Recovery Workflow

### Standard Recovery Flow

```
1. Session ends with work in progress
   |
   v
2. SessionStop hook creates checkpoint
   |
   v
3. New session starts
   |
   v
4. SessionStart hook detects checkpoint
   |
   v
5. User prompted: "Recovery available. Use /sdlc-orchestration:resume"
   |
   v
6. User runs resume command
   |
   v
7. State restored, checkpoint deleted
   |
   v
8. Continue from interrupted phase
```

### Recovery Commands

| Command | Purpose |
|---------|---------|
| `/sdlc-orchestration:resume` | Resume from last checkpoint |
| `rm .claude/sdlc-checkpoint.json` | Discard checkpoint |
| `cat .claude/sdlc-checkpoint.json` | View checkpoint details |

---

## Implementation Checklist

### To activate this design:

1. **Replace hooks.json** with hooks-enhanced.json content:
   ```bash
   cp .claude/plugins/sdlc-orchestration/hooks/hooks-enhanced.json \
      .claude/plugins/sdlc-orchestration/hooks/hooks.json
   ```

2. **Create schemas directory** (if not exists):
   ```bash
   mkdir -p .claude/plugins/sdlc-orchestration/schemas
   ```

3. **Verify jq is installed** (required for JSON processing):
   ```bash
   which jq || brew install jq
   ```

4. **Test recovery flow**:
   ```bash
   # Start workflow
   # /sdlc-orchestration:full-feature "test feature"

   # End session mid-phase
   # Start new session
   # Verify recovery prompt appears
   ```

---

## Files Created

| File | Purpose |
|------|---------|
| `hooks/hooks-enhanced.json` | Complete hook configuration |
| `schemas/state-schemas.json` | JSON schemas for all state files |
| `docs/quality-gates.md` | Quality gate documentation |
| `docs/recovery-workflow.md` | Recovery procedures |
| `docs/hooks-state-design.md` | This summary document |

---

## Related Documentation

- [SDLC Enforcement System](sdlc-enforcement.md) - Confirmation-based workflow enforcement
- [SDLC Orchestrator Skill](../skills/sdlc-orchestrator/SKILL.md) - Full workflow documentation
- [Agent Role Definitions](../agents/) - Individual agent responsibilities

---

**Design Version:** 2.0.0
**Created:** 2026-01-22
**Author:** DevOps Engineer Agent
