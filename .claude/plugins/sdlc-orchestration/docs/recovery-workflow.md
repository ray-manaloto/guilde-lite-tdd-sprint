# SDLC Session Recovery Workflow

## Overview

The SDLC orchestration system includes automatic session checkpointing and crash recovery. This document describes the recovery mechanisms, state transitions, and procedures for resuming interrupted workflows.

---

## Checkpoint System

### Automatic Checkpointing

Checkpoints are created automatically in two scenarios:

1. **Session Stop** - When Claude session ends with work in progress
2. **Phase Transition** - When moving between SDLC phases

### Checkpoint File Structure

Location: `.claude/sdlc-checkpoint.json`

```json
{
  "track_id": "user-auth-oauth2",
  "phase": "implementation",
  "recovery_pending": true,
  "checkpoint_at": "2026-01-22T12:00:00Z",
  "session_id": "a1b2c3d4",
  "current_phase": "implementation",
  "started_at": "2026-01-22T10:00:00Z",
  "phases": {
    "requirements": {
      "status": "completed",
      "agents_completed": ["ceo-stakeholder", "business-analyst", "research-scientist"]
    },
    "design": {
      "status": "completed",
      "agents_completed": ["software-architect", "data-scientist"]
    },
    "implementation": {
      "status": "in_progress",
      "agents_completed": ["staff-engineer"],
      "agents_pending": ["senior-engineer", "junior-engineer"]
    },
    "quality": { "status": "pending" },
    "release": { "status": "pending" }
  },
  "last_agent": "senior-engineer",
  "pending_tasks": ["implement OAuth routes", "add user service"]
}
```

---

## Recovery Scenarios

### Scenario 1: Session Timeout/Disconnect

**Trigger:** Claude session ends unexpectedly during active work

**Detection:** SessionStop hook checks for `in_progress` phase

**Recovery:**
1. Checkpoint created automatically
2. On next session start, SessionStart hook detects checkpoint
3. User prompted to resume or start fresh

### Scenario 2: Agent Failure

**Trigger:** A subagent fails mid-execution

**Detection:** SubagentStop hook doesn't receive expected completion

**Recovery:**
1. State file shows incomplete agent list
2. Resume command detects missing agents
3. Only incomplete agents are re-run

### Scenario 3: Manual Interruption

**Trigger:** User stops Claude mid-workflow (Ctrl+C, close terminal)

**Detection:** No SessionStop hook runs, but state file exists

**Recovery:**
1. On next session, state file shows `in_progress`
2. Create checkpoint from current state
3. Prompt for resume

### Scenario 4: System Crash

**Trigger:** System crash, power failure

**Detection:** State file may be corrupted or incomplete

**Recovery:**
1. Validate state file JSON
2. If valid, create checkpoint
3. If invalid, attempt to recover from last valid checkpoint
4. If no recovery possible, prompt for fresh start

---

## Recovery Commands

### Resume from Checkpoint

```
/sdlc-orchestration:resume
```

**Actions:**
1. Load checkpoint file
2. Restore state to sdlc-state.json
3. Clear recovery_pending flag
4. Delete checkpoint file
5. Continue from interrupted phase

### Check Recovery Status

```bash
# View current checkpoint
cat .claude/sdlc-checkpoint.json | jq .

# Check if recovery is pending
jq '.recovery_pending' .claude/sdlc-checkpoint.json
```

### Manual Recovery

```bash
# Restore from checkpoint manually
cp .claude/sdlc-checkpoint.json .claude/sdlc-state.json

# Clear recovery flag
jq 'del(.recovery_pending) | del(.checkpoint_at) | del(.session_id)' \
  .claude/sdlc-state.json > tmp && mv tmp .claude/sdlc-state.json

# Remove checkpoint
rm .claude/sdlc-checkpoint.json
```

### Discard and Start Fresh

```bash
# Remove all state files
rm -f .claude/sdlc-state.json
rm -f .claude/sdlc-checkpoint.json
rm -f .claude/sdlc-agent-outputs.json
rm -f .claude/sdlc-research-results.json

# Start new workflow
# User: /sdlc-orchestration:full-feature "new feature description"
```

---

## State Transitions

### Normal Flow

```
[No State] --start--> [requirements:in_progress]
    |
    v
[requirements:completed] --transition--> [design:in_progress]
    |
    v
[design:completed] --transition--> [implementation:in_progress]
    |
    v
[implementation:completed] --transition--> [quality:in_progress]
    |
    v
[quality:completed] --transition--> [release:in_progress]
    |
    v
[release:completed] --cleanup--> [No State]
```

### Recovery Flow

```
[Phase:in_progress] --session_stop--> [Checkpoint Created]
    |
    v
[New Session Start] --detect--> [Recovery Available]
    |
    +--resume--> [Phase:in_progress] (restored)
    |
    +--discard--> [No State]
```

### Error Recovery Flow

```
[Phase:in_progress] --error--> [Phase:blocked]
    |
    v
[Investigation] --fix--> [Phase:in_progress]
    |
    +--cannot_fix--> [Previous Phase:in_progress] (rollback)
```

---

## Checkpoint Triggers

### SessionStop Hook

```json
{
  "SessionStop": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'STATE_FILE=\".claude/sdlc-state.json\"; CHECKPOINT_FILE=\".claude/sdlc-checkpoint.json\"; if [ -f \"$STATE_FILE\" ]; then PHASE=$(jq -r \".current_phase\" \"$STATE_FILE\"); STATUS=$(jq -r \".phases.$PHASE.status\" \"$STATE_FILE\"); if [ \"$STATUS\" = \"in_progress\" ]; then jq \". + {recovery_pending: true, checkpoint_at: \\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\", phase: \\\"$PHASE\\\"}\" \"$STATE_FILE\" > \"$CHECKPOINT_FILE\"; fi; fi'",
          "timeout": 10
        }
      ]
    }
  ]
}
```

### SessionStart Hook (Recovery Detection)

```json
{
  "SessionStart": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'CHECKPOINT_FILE=\".claude/sdlc-checkpoint.json\"; if [ -f \"$CHECKPOINT_FILE\" ]; then RECOVERED=$(jq -r \".recovery_pending\" \"$CHECKPOINT_FILE\"); if [ \"$RECOVERED\" = \"true\" ]; then PHASE=$(jq -r \".phase\" \"$CHECKPOINT_FILE\"); TRACK=$(jq -r \".track_id\" \"$CHECKPOINT_FILE\"); echo \"{\\\"addToPrompt\\\": \\\"[SDLC RECOVERY AVAILABLE]\\n\\nPrevious session checkpoint detected:\\n- Track: $TRACK\\n- Phase: $PHASE\\n\\nUse /sdlc-orchestration:resume to continue.\\\"}\"; fi; fi'",
          "timeout": 5
        }
      ]
    }
  ]
}
```

---

## Recovery Procedures

### Procedure 1: Standard Resume

**When:** Checkpoint exists, state is valid

**Steps:**
1. Start new Claude session
2. See recovery prompt
3. Execute `/sdlc-orchestration:resume`
4. Review restored state
5. Continue with current phase

**Expected Output:**
```
[SDLC RECOVERY] Resumed from checkpoint.

- Track: user-auth-oauth2
- Phase: implementation
- Status: Continuing from last checkpoint

Completed agents: staff-engineer
Pending agents: senior-engineer, junior-engineer, devops-engineer

Continuing with senior-engineer...
```

### Procedure 2: Partial Agent Recovery

**When:** Some agents completed, others pending

**Steps:**
1. Resume from checkpoint
2. Review which agents completed
3. Re-run only pending agents
4. Aggregate all results

**Script:**
```bash
# Check completed vs pending agents
STATE_FILE=".claude/sdlc-state.json"
PHASE=$(jq -r '.current_phase' "$STATE_FILE")
COMPLETED=$(jq -r '.phases.'$PHASE'.agents_completed[]' "$STATE_FILE")
EXPECTED="ceo-stakeholder business-analyst research-scientist"  # Example

for agent in $EXPECTED; do
  if ! echo "$COMPLETED" | grep -q "$agent"; then
    echo "Agent pending: $agent"
  fi
done
```

### Procedure 3: Corrupted State Recovery

**When:** State file is invalid JSON or incomplete

**Steps:**
1. Attempt to parse state file
2. If invalid, check for backup
3. If no backup, extract what's possible
4. Create minimal valid state
5. Resume or restart

**Script:**
```bash
# Validate state file
if ! jq empty .claude/sdlc-state.json 2>/dev/null; then
  echo "State file corrupted"

  # Try checkpoint
  if [ -f .claude/sdlc-checkpoint.json ] && jq empty .claude/sdlc-checkpoint.json 2>/dev/null; then
    echo "Restoring from checkpoint..."
    cp .claude/sdlc-checkpoint.json .claude/sdlc-state.json
  else
    echo "No valid recovery source. Starting fresh."
    rm -f .claude/sdlc-state.json
    rm -f .claude/sdlc-checkpoint.json
  fi
fi
```

### Procedure 4: Phase Rollback

**When:** Need to return to previous phase

**Steps:**
1. Update current_phase to previous
2. Set previous phase to in_progress
3. Set rolled-back phase to pending
4. Clear relevant artifacts
5. Continue from rolled-back point

**Script:**
```bash
# Rollback from implementation to design
STATE_FILE=".claude/sdlc-state.json"

jq '.current_phase = "design" |
    .phases.design.status = "in_progress" |
    .phases.implementation.status = "pending" |
    .phases.implementation.agents_completed = []' \
  "$STATE_FILE" > tmp && mv tmp "$STATE_FILE"

echo "Rolled back to design phase"
```

---

## Recovery Data Preservation

### What Gets Preserved

| Data | Preserved | Location |
|------|-----------|----------|
| Track ID | Yes | sdlc-state.json |
| Current phase | Yes | sdlc-state.json |
| Completed phases | Yes | sdlc-state.json |
| Agent completions | Yes | sdlc-state.json |
| Artifacts created | Yes | On disk |
| Research results | Yes | sdlc-research-results.json |
| Activity log | Yes | sdlc-activity.log |

### What Gets Lost

| Data | Lost | Mitigation |
|------|------|------------|
| In-flight agent output | Yes | Re-run agent |
| Unsaved code changes | Yes | Git stash/commit frequently |
| Terminal state | Yes | Re-establish context |

### Artifact Preservation

Ensure artifacts are written to disk before session end:

```json
{
  "PostToolUse": [
    {
      "matcher": "Task",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); AGENT=$(echo \"$INPUT\" | jq -r \".subagent_type\"); OUTPUT=$(echo \"$INPUT\" | jq -r \".result\"); # Save agent output to artifacts ARTIFACT_DIR=\".claude/artifacts\"; mkdir -p \"$ARTIFACT_DIR\"; TIMESTAMP=$(date +%Y%m%d_%H%M%S); echo \"$OUTPUT\" > \"$ARTIFACT_DIR/${AGENT}_${TIMESTAMP}.md\"'",
          "timeout": 5
        }
      ]
    }
  ]
}
```

---

## Monitoring Recovery

### Check Recovery Status

```bash
# View current state
echo "=== SDLC State ===" && \
cat .claude/sdlc-state.json | jq '{
  track: .track_id,
  phase: .current_phase,
  status: .phases[.current_phase].status,
  agents_done: .phases[.current_phase].agents_completed
}'

# View checkpoint
echo "=== Checkpoint ===" && \
cat .claude/sdlc-checkpoint.json | jq '{
  track: .track_id,
  phase: .phase,
  recovery_pending: .recovery_pending,
  checkpoint_at: .checkpoint_at
}' 2>/dev/null || echo "No checkpoint"
```

### Activity Log Analysis

```bash
# Recent SDLC activity
tail -20 .claude/sdlc-activity.log

# Agent completions
grep "Agent completed" .claude/sdlc-activity.log | tail -10

# Checkpoints created
grep "checkpoint" .claude/sdlc-activity.log
```

---

## Best Practices

### 1. Frequent Commits

Commit code changes frequently to preserve work:

```
# After each significant change
git add -A && git commit -m "WIP: checkpoint"
```

### 2. Phase Checkpoints

Create explicit checkpoints at phase boundaries:

```bash
# Before phase transition
git add -A && git commit -m "conductor(checkpoint): End of design phase"
git notes add -m "Phase checkpoint: design complete"
```

### 3. Artifact Documentation

Document what artifacts exist for each phase:

```json
{
  "phases": {
    "requirements": {
      "artifacts": {
        "user_stories": "docs/requirements/user-stories.md",
        "acceptance_criteria": "docs/requirements/acceptance.md"
      }
    }
  }
}
```

### 4. Recovery Testing

Periodically test recovery:

```bash
# Simulate session end
# 1. Copy current state
cp .claude/sdlc-state.json .claude/sdlc-state.backup.json

# 2. Create checkpoint
jq '. + {recovery_pending: true}' .claude/sdlc-state.json > .claude/sdlc-checkpoint.json

# 3. Clear state
rm .claude/sdlc-state.json

# 4. Start new session and verify recovery prompt appears
# 5. Resume and verify state restored correctly
```

---

## Troubleshooting

### Issue: Recovery prompt not appearing

**Cause:** Checkpoint file missing or invalid

**Solution:**
```bash
# Check checkpoint exists
ls -la .claude/sdlc-checkpoint.json

# Validate JSON
jq . .claude/sdlc-checkpoint.json

# Check recovery_pending flag
jq '.recovery_pending' .claude/sdlc-checkpoint.json
```

### Issue: Resume fails with "No checkpoint found"

**Cause:** Checkpoint was deleted or never created

**Solution:**
```bash
# If state file exists, create checkpoint from it
if [ -f .claude/sdlc-state.json ]; then
  jq '. + {recovery_pending: true, checkpoint_at: "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"}' \
    .claude/sdlc-state.json > .claude/sdlc-checkpoint.json
  echo "Checkpoint created manually"
fi
```

### Issue: Agents not re-running after resume

**Cause:** Agents already marked as complete in state

**Solution:**
```bash
# Clear specific agent from completed list
STATE_FILE=".claude/sdlc-state.json"
PHASE=$(jq -r '.current_phase' "$STATE_FILE")
AGENT="senior-engineer"

jq ".phases.$PHASE.agents_completed -= [\"$AGENT\"]" \
  "$STATE_FILE" > tmp && mv tmp "$STATE_FILE"

echo "Agent $AGENT cleared, will re-run"
```

### Issue: State file and checkpoint out of sync

**Cause:** Manual edits or partial writes

**Solution:**
```bash
# Compare timestamps
STATE_TIME=$(jq -r '.started_at' .claude/sdlc-state.json)
CHECKPOINT_TIME=$(jq -r '.checkpoint_at' .claude/sdlc-checkpoint.json)

echo "State started: $STATE_TIME"
echo "Checkpoint at: $CHECKPOINT_TIME"

# Use more recent as source of truth
# If checkpoint newer, restore from checkpoint
# If state newer, regenerate checkpoint
```

---

**Last Updated:** 2026-01-22
**Version:** 2.0.0
