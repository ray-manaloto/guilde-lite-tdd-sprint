# SDLC Hooks Enhancement Specification

## Overview

This document specifies three new hook types for the SDLC Orchestration plugin:

1. **Stop Hook** - Halt workflow on quality gate failures
2. **SubagentStop Hook** - Aggregate results when parallel agents complete
3. **Session Checkpoint Hook** - Save/restore state for crash recovery

## 1. Stop Hook for Quality Gates

### Purpose

Stop workflow execution when critical quality checks fail, preventing bad code from progressing through phases.

### Hook Definition

```json
{
  "PostToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "stop",
          "name": "quality-gate-check",
          "condition": {
            "command_pattern": "(pytest|npm test|ruff|tsc)",
            "exit_code_not": 0
          },
          "action": {
            "stop": true,
            "message": "[SDLC STOP] Quality gate failed: {command}. Exit code: {exit_code}",
            "allow_override": false,
            "log_to": ".claude/sdlc-stops.log"
          }
        }
      ]
    }
  ]
}
```

### Implementation Script

```bash
#!/bin/bash
# hooks/scripts/check_quality_gates.sh

set -e

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
EXIT_CODE=$(echo "$INPUT" | jq -r '.tool_result.exit_code // 0')
OUTPUT=$(echo "$INPUT" | jq -r '.tool_result.stdout // empty')

STATE_FILE="${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-state.json"
STOP_LOG="${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-stops.log"

# Check if this is a quality-related command
is_quality_command() {
    echo "$COMMAND" | grep -qE "(pytest|npm test|npm run test|vitest|jest|ruff|tsc|eslint|mypy)"
}

# Check if command failed
if is_quality_command && [ "$EXIT_CODE" != "0" ]; then
    # Log the failure
    mkdir -p "$(dirname "$STOP_LOG")"
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) STOP: $COMMAND (exit: $EXIT_CODE)" >> "$STOP_LOG"

    # Check if in quality phase (where stops are mandatory)
    if [ -f "$STATE_FILE" ]; then
        PHASE=$(jq -r '.current_phase // empty' "$STATE_FILE" 2>/dev/null)
        if [ "$PHASE" = "quality" ]; then
            # Mandatory stop in quality phase
            echo '{"decision": "stop", "reason": "[SDLC STOP] Quality gate failed in quality phase. Fix issues before proceeding.", "details": {"command": "'"$COMMAND"'", "exit_code": '"$EXIT_CODE"'}}'
            exit 0
        fi
    fi

    # Warning in other phases
    echo '{"addToPrompt": "[SDLC WARNING] Test/lint failure detected. Consider fixing before proceeding: '"$COMMAND"'"}'
fi

exit 0
```

### Stop Hook Behavior

| Scenario | Phase | Action |
|----------|-------|--------|
| Test failure | Quality | **STOP** - Block all further operations |
| Test failure | Implementation | **WARN** - Allow continue with warning |
| Lint failure | Any | **WARN** - Suggest fix |
| Type error | Any | **WARN** - Suggest fix |
| Security scan fail | Quality | **STOP** - Block deployment |

---

## 2. SubagentStop Hook for Aggregation

### Purpose

Collect and synthesize outputs from parallel agents before proceeding to the next phase.

### Hook Definition

```json
{
  "SubagentComplete": [
    {
      "matcher": "sdlc-orchestration:*",
      "hooks": [
        {
          "type": "aggregate",
          "name": "phase-result-aggregator",
          "collect": {
            "agent_type": "$AGENT_TYPE",
            "output": "$AGENT_OUTPUT",
            "execution_time": "$EXECUTION_TIME"
          },
          "until": {
            "condition": "all_phase_agents_complete",
            "timeout": 600
          },
          "then": {
            "command": "bash -c 'aggregate_results.sh'",
            "create_artifact": "{phase}-summary.md"
          }
        }
      ]
    }
  ]
}
```

### Implementation Script

```bash
#!/bin/bash
# hooks/scripts/aggregate_results.sh

set -e

AGENT_TYPE="$1"
AGENT_OUTPUT="$2"

STATE_FILE="${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-state.json"
AGGREGATION_DIR="${CLAUDE_PROJECT_ROOT:-.}/.claude/aggregation"

mkdir -p "$AGGREGATION_DIR"

# Get current phase
PHASE=$(jq -r '.current_phase // "unknown"' "$STATE_FILE" 2>/dev/null)

# Get expected agents for this phase
EXPECTED_AGENTS=$(jq -r ".agents_by_phase.$PHASE | @csv" "$STATE_FILE" 2>/dev/null | tr -d '"')

# Store this agent's output
AGENT_FILE="$AGGREGATION_DIR/${PHASE}_${AGENT_TYPE}.json"
cat > "$AGENT_FILE" << EOF
{
  "agent": "$AGENT_TYPE",
  "phase": "$PHASE",
  "completed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "output": $(echo "$AGENT_OUTPUT" | jq -Rs .)
}
EOF

# Count completed agents
COMPLETED=$(ls -1 "$AGGREGATION_DIR/${PHASE}_"*.json 2>/dev/null | wc -l | tr -d ' ')
EXPECTED=$(echo "$EXPECTED_AGENTS" | tr ',' '\n' | wc -l | tr -d ' ')

echo "[SDLC] Agent $AGENT_TYPE completed ($COMPLETED/$EXPECTED for $PHASE phase)"

# Check if all agents complete
if [ "$COMPLETED" -ge "$EXPECTED" ]; then
    echo "[SDLC] All agents for $PHASE phase complete. Generating summary..."

    # Generate aggregation summary
    SUMMARY_FILE="${CLAUDE_PROJECT_ROOT:-.}/artifacts/${PHASE}-summary.md"
    mkdir -p "$(dirname "$SUMMARY_FILE")"

    cat > "$SUMMARY_FILE" << EOF
# Phase Summary: $PHASE

Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Agent Outputs

EOF

    # Append each agent's output
    for agent_file in "$AGGREGATION_DIR/${PHASE}_"*.json; do
        AGENT=$(jq -r '.agent' "$agent_file")
        OUTPUT=$(jq -r '.output' "$agent_file")
        cat >> "$SUMMARY_FILE" << EOF
### $AGENT

$OUTPUT

---

EOF
    done

    # Add synthesis section
    cat >> "$SUMMARY_FILE" << EOF
## Synthesis

*[To be completed by orchestrator after reviewing agent outputs]*

## Handoff to Next Phase

- [ ] All agent outputs reviewed
- [ ] Conflicts resolved
- [ ] Artifacts validated
- [ ] Ready for next phase
EOF

    # Update state
    jq ".phases.$PHASE.status = \"aggregating\" | .phases.$PHASE.summary_file = \"$SUMMARY_FILE\"" \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

    # Clean up aggregation files
    rm -f "$AGGREGATION_DIR/${PHASE}_"*.json

    echo '{"addToPrompt": "[SDLC AGGREGATION] All '"$PHASE"' phase agents complete. Summary generated at '"$SUMMARY_FILE"'. Review and synthesize before proceeding to next phase."}'
fi

exit 0
```

### Aggregation Flow

```
Phase Start
    │
    ├── Agent 1 ─────┐
    ├── Agent 2 ─────┼──── Parallel Execution
    └── Agent 3 ─────┘
            │
            ▼
    SubagentComplete Hook (each agent)
            │
            ▼
    Store output in .claude/aggregation/
            │
            ▼
    All complete? ─── No ──→ Wait
            │
           Yes
            │
            ▼
    Generate {phase}-summary.md
            │
            ▼
    Prompt for synthesis
            │
            ▼
    Phase Complete
```

---

## 3. Session Checkpoint Hook

### Purpose

Save workflow state at key milestones for crash recovery and session restoration.

### Hook Definition

```json
{
  "PhaseComplete": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "checkpoint",
          "name": "phase-checkpoint",
          "trigger": ["phase_complete", "gate_passed"],
          "save": {
            "state_file": ".claude/sdlc-state.json",
            "artifacts": "artifacts/{phase}/*",
            "aggregation": ".claude/aggregation/*"
          },
          "storage": {
            "path": ".claude/checkpoints",
            "format": "checkpoint_{timestamp}.tar.gz",
            "retention": {
              "max_count": 10,
              "max_age_hours": 168
            }
          }
        }
      ]
    }
  ],
  "SessionStart": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "checkpoint",
          "name": "session-restore",
          "action": "check_and_offer_restore",
          "prompt": "Found checkpoint from {timestamp}. Resume from phase '{phase}'? (yes/no)"
        }
      ]
    }
  ]
}
```

### Save Checkpoint Script

```bash
#!/bin/bash
# hooks/scripts/save_checkpoint.sh

set -e

PHASE="$1"
TRIGGER="$2"

CHECKPOINT_DIR="${CLAUDE_PROJECT_ROOT:-.}/.claude/checkpoints"
STATE_FILE="${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-state.json"
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
CHECKPOINT_FILE="$CHECKPOINT_DIR/checkpoint_${TIMESTAMP}.tar.gz"

mkdir -p "$CHECKPOINT_DIR"

# Files to include in checkpoint
FILES_TO_SAVE=(
    ".claude/sdlc-state.json"
    ".claude/sdlc-doc-sync.json"
    ".claude/aggregation"
    "artifacts"
)

# Create checkpoint archive
EXISTING_FILES=()
for f in "${FILES_TO_SAVE[@]}"; do
    if [ -e "${CLAUDE_PROJECT_ROOT:-.}/$f" ]; then
        EXISTING_FILES+=("$f")
    fi
done

if [ ${#EXISTING_FILES[@]} -gt 0 ]; then
    cd "${CLAUDE_PROJECT_ROOT:-.}"
    tar -czf "$CHECKPOINT_FILE" "${EXISTING_FILES[@]}" 2>/dev/null

    # Update state with checkpoint reference
    if [ -f "$STATE_FILE" ]; then
        jq ".checkpoint_id = \"chk_$TIMESTAMP\" | .phases.$PHASE.checkpoint_id = \"chk_$TIMESTAMP\"" \
            "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
    fi

    # Cleanup old checkpoints (keep last 10)
    ls -1t "$CHECKPOINT_DIR"/checkpoint_*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm -f

    echo "[SDLC CHECKPOINT] Saved checkpoint: checkpoint_${TIMESTAMP}.tar.gz (phase: $PHASE, trigger: $TRIGGER)"
fi

exit 0
```

### Restore Checkpoint Script

```bash
#!/bin/bash
# hooks/scripts/restore_checkpoint.sh

set -e

CHECKPOINT_ID="$1"

CHECKPOINT_DIR="${CLAUDE_PROJECT_ROOT:-.}/.claude/checkpoints"
STATE_FILE="${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-state.json"

# Find checkpoint file
if [ -n "$CHECKPOINT_ID" ]; then
    CHECKPOINT_FILE="$CHECKPOINT_DIR/checkpoint_${CHECKPOINT_ID#chk_}.tar.gz"
else
    # Get most recent checkpoint
    CHECKPOINT_FILE=$(ls -1t "$CHECKPOINT_DIR"/checkpoint_*.tar.gz 2>/dev/null | head -1)
fi

if [ ! -f "$CHECKPOINT_FILE" ]; then
    echo '{"error": "Checkpoint not found: '"$CHECKPOINT_ID"'"}'
    exit 1
fi

# Extract checkpoint
cd "${CLAUDE_PROJECT_ROOT:-.}"
tar -xzf "$CHECKPOINT_FILE"

# Read restored state
if [ -f "$STATE_FILE" ]; then
    PHASE=$(jq -r '.current_phase // "unknown"' "$STATE_FILE")
    TRACK=$(jq -r '.track_id // "unknown"' "$STATE_FILE")

    echo '{"addToPrompt": "[SDLC RESTORED] Session restored from checkpoint. Track: '"$TRACK"', Phase: '"$PHASE"'. Ready to continue."}'
else
    echo '{"error": "State file not found after restore"}'
    exit 1
fi

exit 0
```

### Session Start Check

```bash
#!/bin/bash
# hooks/scripts/check_for_checkpoint.sh

CHECKPOINT_DIR="${CLAUDE_PROJECT_ROOT:-.}/.claude/checkpoints"
STATE_FILE="${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-state.json"

# Check if there's an active workflow that was interrupted
if [ -f "$STATE_FILE" ]; then
    PHASE=$(jq -r '.current_phase // empty' "$STATE_FILE" 2>/dev/null)
    STATUS=$(jq -r ".phases.$PHASE.status // empty" "$STATE_FILE" 2>/dev/null)
    TRACK=$(jq -r '.track_id // empty' "$STATE_FILE" 2>/dev/null)

    if [ "$STATUS" = "in_progress" ]; then
        # Find matching checkpoint
        CHECKPOINT_ID=$(jq -r '.checkpoint_id // empty' "$STATE_FILE" 2>/dev/null)
        CHECKPOINT_FILE="$CHECKPOINT_DIR/checkpoint_${CHECKPOINT_ID#chk_}.tar.gz"

        if [ -f "$CHECKPOINT_FILE" ]; then
            TIMESTAMP=$(echo "$CHECKPOINT_ID" | sed 's/chk_//' | sed 's/_/ /')
            echo '{"addToPrompt": "[SDLC RECOVERY] Found interrupted workflow.\n\nTrack: '"$TRACK"'\nPhase: '"$PHASE"' (in_progress)\nCheckpoint: '"$CHECKPOINT_ID"'\n\nWould you like to:\n1. Resume from checkpoint\n2. Start fresh (discard progress)\n\nPlease respond with your choice."}'
        fi
    fi
fi

exit 0
```

---

## 4. Pre-flight Validation Hook

### Purpose

Validate service health and environment before running tests in the Quality phase.

### Hook Definition

```json
{
  "PhaseStart": [
    {
      "matcher": "quality",
      "hooks": [
        {
          "type": "preflight",
          "name": "quality-preflight",
          "checks": [
            {
              "name": "database",
              "command": "pg_isready -h ${DB_HOST:-localhost}",
              "timeout": 5,
              "required": true
            },
            {
              "name": "redis",
              "command": "redis-cli ping",
              "timeout": 5,
              "required": false
            },
            {
              "name": "test_fixtures",
              "command": "test -d tests/fixtures",
              "timeout": 2,
              "required": true
            },
            {
              "name": "env_vars",
              "command": "test -n \"$DATABASE_URL\"",
              "timeout": 1,
              "required": true
            }
          ],
          "on_failure": {
            "required_failed": "stop",
            "optional_failed": "warn"
          }
        }
      ]
    }
  ]
}
```

### Preflight Script

```bash
#!/bin/bash
# hooks/scripts/preflight_validate.sh

set -e

PHASE="$1"
CONFIG_FILE="${CLAUDE_PROJECT_ROOT:-.}/docs/design/SDLC-enhanced-phase-state.json"
STATE_FILE="${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-state.json"

echo "[SDLC PREFLIGHT] Running pre-flight checks for $PHASE phase..."

FAILED_REQUIRED=()
FAILED_OPTIONAL=()
PASSED=()

# Database connectivity
if command -v pg_isready >/dev/null 2>&1; then
    if pg_isready -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -t 5 >/dev/null 2>&1; then
        PASSED+=("database")
        echo "  [PASS] Database connectivity"
    else
        FAILED_REQUIRED+=("database")
        echo "  [FAIL] Database connectivity"
    fi
else
    echo "  [SKIP] Database check (pg_isready not available)"
fi

# Redis connectivity
if command -v redis-cli >/dev/null 2>&1; then
    if redis-cli -h "${REDIS_HOST:-localhost}" ping >/dev/null 2>&1; then
        PASSED+=("redis")
        echo "  [PASS] Redis connectivity"
    else
        FAILED_OPTIONAL+=("redis")
        echo "  [WARN] Redis not available (optional)"
    fi
else
    echo "  [SKIP] Redis check (redis-cli not available)"
fi

# Test fixtures
if [ -d "${CLAUDE_PROJECT_ROOT:-.}/tests/fixtures" ]; then
    PASSED+=("test_fixtures")
    echo "  [PASS] Test fixtures directory exists"
else
    FAILED_OPTIONAL+=("test_fixtures")
    echo "  [WARN] Test fixtures directory not found"
fi

# Environment variables
REQUIRED_VARS=("SECRET_KEY")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -n "${!var}" ]; then
        PASSED+=("env_$var")
        echo "  [PASS] Environment variable: $var"
    else
        FAILED_OPTIONAL+=("env_$var")
        echo "  [WARN] Environment variable not set: $var"
    fi
done

# Update state with preflight results
if [ -f "$STATE_FILE" ]; then
    PREFLIGHT_STATUS="pass"
    if [ ${#FAILED_REQUIRED[@]} -gt 0 ]; then
        PREFLIGHT_STATUS="fail"
    elif [ ${#FAILED_OPTIONAL[@]} -gt 0 ]; then
        PREFLIGHT_STATUS="warn"
    fi

    jq ".phases.$PHASE.preflight_status = \"$PREFLIGHT_STATUS\" | .phases.$PHASE.preflight_passed = $(echo "${PASSED[@]}" | jq -R -s 'split(" ")') | .phases.$PHASE.preflight_failed = $(echo "${FAILED_REQUIRED[@]} ${FAILED_OPTIONAL[@]}" | jq -R -s 'split(" ") | map(select(. != ""))')" \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
fi

# Summary
echo ""
echo "[SDLC PREFLIGHT] Summary:"
echo "  Passed: ${#PASSED[@]}"
echo "  Failed (required): ${#FAILED_REQUIRED[@]}"
echo "  Failed (optional): ${#FAILED_OPTIONAL[@]}"

if [ ${#FAILED_REQUIRED[@]} -gt 0 ]; then
    echo '{"decision": "stop", "reason": "[SDLC PREFLIGHT FAILED] Required checks failed: '"${FAILED_REQUIRED[*]}"'. Fix before proceeding."}'
    exit 1
elif [ ${#FAILED_OPTIONAL[@]} -gt 0 ]; then
    echo '{"addToPrompt": "[SDLC PREFLIGHT WARNING] Optional checks failed: '"${FAILED_OPTIONAL[*]}"'. Proceeding with caution."}'
fi

exit 0
```

---

## 5. TDD Enforcement Hook

### Purpose

Encourage test-first development by detecting implementation without corresponding tests.

### Hook Definition

```json
{
  "PreToolUse": [
    {
      "matcher": "Write",
      "hooks": [
        {
          "type": "tdd",
          "name": "tdd-enforcement",
          "condition": {
            "file_pattern": "\\.(py|ts|tsx|js|jsx)$",
            "exclude_pattern": "(test_|_test\\.|spec\\.|tests/)"
          },
          "check": {
            "content_pattern": "(def |class |function |const .* = \\(|export (function|const|class))",
            "requires_test": true
          },
          "action": {
            "warn": true,
            "message": "[SDLC TDD] Creating implementation without corresponding test file. Consider writing tests first.",
            "suggest_test_file": true
          }
        }
      ]
    }
  ]
}
```

### TDD Enforcement Script

```bash
#!/bin/bash
# hooks/scripts/tdd_enforce.sh

set -e

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // empty')

# Skip test files
if echo "$FILE" | grep -qE "(test_|_test\.|\.spec\.|/tests/)"; then
    exit 0
fi

# Skip non-code files
if ! echo "$FILE" | grep -qE "\.(py|ts|tsx|js|jsx)$"; then
    exit 0
fi

# Check if creating new functions/classes
if echo "$CONTENT" | grep -qE "(^def |^class |^function |^export (function|const|class|default function))"; then
    # Determine expected test file
    FILENAME=$(basename "$FILE")
    DIRNAME=$(dirname "$FILE")
    EXT="${FILENAME##*.}"

    case "$EXT" in
        py)
            TEST_FILE="$DIRNAME/test_${FILENAME}"
            ALT_TEST="tests/test_${FILENAME}"
            ;;
        ts|tsx)
            TEST_FILE="${FILE%.${EXT}}.test.${EXT}"
            ALT_TEST="${FILE%.${EXT}}.spec.${EXT}"
            ;;
        js|jsx)
            TEST_FILE="${FILE%.${EXT}}.test.${EXT}"
            ALT_TEST="${FILE%.${EXT}}.spec.${EXT}"
            ;;
    esac

    # Check if test file exists
    if [ ! -f "$TEST_FILE" ] && [ ! -f "$ALT_TEST" ]; then
        echo '{"addToPrompt": "[SDLC TDD] You are creating implementation code without a corresponding test file.\n\nExpected test file: '"$TEST_FILE"'\n\nTDD Best Practice:\n1. Write a failing test first (Red)\n2. Write minimal code to pass (Green)\n3. Refactor with confidence (Refactor)\n\nConsider creating the test file first."}'
    fi
fi

exit 0
```

---

## Integration Points

### Updated hooks.json Structure

The enhanced hooks.json should include all new hook types:

```json
{
  "SessionStart": [...],
  "UserPromptSubmit": [...],
  "PreToolUse": [
    {"matcher": "Write", "hooks": [/* TDD enforcement */]},
    {"matcher": "WebSearch", "hooks": [/* Research workflow */]},
    ...
  ],
  "PostToolUse": [
    {"matcher": "Bash", "hooks": [/* Stop on quality failure */]},
    {"matcher": "Task", "hooks": [/* Subagent aggregation */]},
    {"matcher": "Write", "hooks": [/* Lint/type check */]},
    ...
  ],
  "SubagentComplete": [
    {"matcher": "sdlc-orchestration:*", "hooks": [/* Result aggregation */]}
  ],
  "PhaseStart": [
    {"matcher": "quality", "hooks": [/* Preflight validation */]}
  ],
  "PhaseComplete": [
    {"matcher": "", "hooks": [/* Checkpoint save */]}
  ],
  "GateFailed": [
    {"matcher": "", "hooks": [/* Stop and notify */]}
  ]
}
```

### File Structure for Hook Scripts

```
.claude/plugins/sdlc-orchestration/
├── hooks/
│   ├── hooks.json                 # Hook definitions
│   └── scripts/
│       ├── check_quality_gates.sh # Stop hook
│       ├── aggregate_results.sh   # Subagent aggregation
│       ├── save_checkpoint.sh     # Checkpoint save
│       ├── restore_checkpoint.sh  # Checkpoint restore
│       ├── check_for_checkpoint.sh # Session start check
│       ├── preflight_validate.sh  # Pre-flight checks
│       └── tdd_enforce.sh         # TDD enforcement
```

---

## Summary

| Hook Type | Purpose | Trigger | Action |
|-----------|---------|---------|--------|
| Stop | Quality gate enforcement | PostToolUse (Bash) | Block on failure |
| SubagentStop | Result aggregation | SubagentComplete | Collect & synthesize |
| Checkpoint | Crash recovery | PhaseComplete | Save state |
| Preflight | Service validation | PhaseStart (quality) | Validate health |
| TDD | Test-first enforcement | PreToolUse (Write) | Warn on violation |
