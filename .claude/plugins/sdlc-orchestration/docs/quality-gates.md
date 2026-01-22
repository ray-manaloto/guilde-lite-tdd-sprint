# SDLC Quality Gates Configuration

## Overview

Quality gates are automated checkpoints that verify task completion before allowing progression. They are enforced through the Stop hook and pre-commit validation hooks.

## Gate Categories

### 1. Code Quality Gates

| Gate | Trigger | Check | Block Level |
|------|---------|-------|-------------|
| Lint Check | PostToolUse:Write (*.py) | `ruff check` | Warning |
| Type Check | PostToolUse:Write (*.ts/*.tsx) | `tsc --noEmit` | Warning |
| Format Check | PostToolUse:Write | ruff format / prettier | Auto-fix |
| Security Scan | Stop | `bandit` (Python) | Warning |

### 2. Test Gates

| Gate | Trigger | Check | Block Level |
|------|---------|-------|-------------|
| Unit Tests | Stop | `pytest -x -q` | Warning |
| Test Coverage | Phase transition | Coverage report | Advisory |
| Integration Tests | Quality phase | Full test suite | Required |

### 3. Documentation Gates

| Gate | Trigger | Check | Block Level |
|------|---------|-------|-------------|
| Doc Sync | Stop / Pre-commit | sdlc-doc-sync.json | Warning |
| API Docs | Release phase | OpenAPI spec exists | Advisory |
| README Updated | Release phase | Recent modification | Advisory |

### 4. Phase Gates

| Gate | Phase | Requirements | Block Level |
|------|-------|--------------|-------------|
| Requirements Complete | Design entry | All agents complete | Required |
| Design Approved | Implementation entry | Architecture reviewed | Required |
| Code Complete | Quality entry | Lint + basic tests pass | Required |
| Quality Approved | Release entry | All tests + review pass | Required |
| Production Ready | Release complete | Canary validated | Required |

---

## Stop Hook Validation

The Stop hook runs comprehensive validation when Claude completes a task response.

### Validation Sequence

```
Stop Hook Triggered
    |
    v
[1] Initialize validation file
    |
    v
[2] Run pytest (backend)
    |
    +-- Pass -> tests_pass: true
    |
    +-- Fail -> tests_pass: false, capture output
    |
    v
[3] Run ruff check (backend)
    |
    +-- Clean -> lint_clean: true
    |
    +-- Issues -> lint_clean: false, capture issues
    |
    v
[4] Check doc sync state
    |
    +-- Synced -> docs_synced: true
    |
    +-- Pending -> docs_synced: false
    |
    v
[5] Aggregate results
    |
    +-- All pass -> task_complete: true
    |
    +-- Any fail -> task_complete: false, warnings generated
    |
    v
[6] Inject prompt with validation results
```

### Validation File Structure

Location: `.claude/sdlc-stop-validation.json`

```json
{
  "timestamp": "2026-01-22T12:30:00Z",
  "phase": "implementation",
  "checks": {
    "tests_pass": true,
    "test_output": "42 passed in 3.21s",
    "lint_clean": false,
    "lint_issues": "backend/app/services/auth.py:15 E501",
    "type_check_pass": true,
    "docs_synced": true,
    "security_scan_pass": true
  },
  "task_complete": false,
  "warnings": "\n- Lint issues detected"
}
```

### Timeout Configuration

| Check | Timeout | Rationale |
|-------|---------|-----------|
| pytest | 120s | Full test suite may be slow |
| ruff check | 30s | Fast linting |
| tsc --noEmit | 15s | Type checking |
| doc sync check | 5s | File existence check |

---

## Pre-Commit Validation

Pre-commit hooks run before `git commit` commands to catch issues early.

### Hook Configuration

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); CMD=$(echo \"$INPUT\" | jq -r \".tool_input.command // empty\" 2>/dev/null); if echo \"$CMD\" | grep -qE \"git commit\"; then STOP_FILE=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-stop-validation.json\"; if [ -f \"$STOP_FILE\" ]; then TESTS=$(jq -r \".checks.tests_pass // true\" \"$STOP_FILE\" 2>/dev/null); LINT=$(jq -r \".checks.lint_clean // true\" \"$STOP_FILE\" 2>/dev/null); if [ \"$TESTS\" = \"false\" ] || [ \"$LINT\" = \"false\" ]; then echo \"{\\\"addToPrompt\\\": \\\"[SDLC PRE-COMMIT WARNING]\\n\\nQuality checks failed. Consider fixing issues before committing.\\\"}\"; fi; fi; fi; exit 0'",
          "timeout": 5
        }
      ]
    }
  ]
}
```

### Pre-Commit Check Matrix

| Check | When Triggered | Blocks Commit |
|-------|----------------|---------------|
| Tests failing | Always | No (warning only) |
| Lint issues | Always | No (warning only) |
| Type errors | TypeScript files changed | No (warning only) |
| Security issues | Always | No (warning only) |
| Docs out of sync | Always | No (warning only) |

### Strict Mode (Optional)

To enforce strict pre-commit blocking:

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); CMD=$(echo \"$INPUT\" | jq -r \".tool_input.command\"); if echo \"$CMD\" | grep -qE \"git commit\"; then STOP_FILE=\".claude/sdlc-stop-validation.json\"; if [ -f \"$STOP_FILE\" ]; then TESTS=$(jq -r \".checks.tests_pass\" \"$STOP_FILE\"); if [ \"$TESTS\" = \"false\" ]; then echo \"{\\\"decision\\\": \\\"block\\\", \\\"reason\\\": \\\"[SDLC BLOCKED] Tests must pass before committing\\\"}\"; fi; fi; fi'",
          "timeout": 5
        }
      ]
    }
  ]
}
```

---

## Phase Gate Configuration

### Gate Definitions

```json
{
  "gates": {
    "requirements": [
      "all_agents_complete",
      "artifacts_validated",
      "stakeholder_approved"
    ],
    "design": [
      "architecture_reviewed",
      "api_contract_approved",
      "security_reviewed"
    ],
    "implementation": [
      "code_complete",
      "unit_tests_pass",
      "lint_pass",
      "type_check_pass"
    ],
    "quality": [
      "integration_tests_pass",
      "code_review_approved",
      "performance_validated",
      "security_scan_pass"
    ],
    "release": [
      "staging_deployed",
      "canary_validated",
      "docs_updated",
      "production_approved"
    ]
  }
}
```

### Gate Verification Logic

```bash
# Check if phase can transition
verify_phase_gate() {
  PHASE=$1
  STATE_FILE=".claude/sdlc-state.json"

  # Get required gates for phase
  REQUIRED_GATES=$(jq -r ".gates.$PHASE[]" templates/phase-state.json)

  # Get passed gates
  PASSED_GATES=$(jq -r ".phases.$PHASE.gates_passed[]" "$STATE_FILE")

  # Compare
  for gate in $REQUIRED_GATES; do
    if ! echo "$PASSED_GATES" | grep -q "$gate"; then
      echo "Gate not passed: $gate"
      return 1
    fi
  done

  return 0
}
```

### Automatic Gate Passing

Some gates are automatically marked as passed based on hook results:

| Gate | Auto-Pass Condition |
|------|---------------------|
| `unit_tests_pass` | Stop hook shows tests_pass: true |
| `lint_pass` | Stop hook shows lint_clean: true |
| `type_check_pass` | No TypeScript errors |
| `all_agents_complete` | SubagentStop count matches expected |

### Manual Gate Approval

Some gates require explicit approval:

| Gate | Approval Method |
|------|-----------------|
| `stakeholder_approved` | User confirms requirements |
| `architecture_reviewed` | Code reviewer agent completes |
| `code_review_approved` | Reviewer marks approved |
| `production_approved` | User confirms deployment |

---

## Phase Transition Rules

### Allowed Transitions

```
requirements -> design
design -> implementation
implementation -> quality
quality -> release
release -> (complete)

# Backward transitions (for fixes)
quality -> implementation (fix issues)
implementation -> design (architecture change)
design -> requirements (scope change)
```

### Transition Validation

```json
{
  "PhaseTransition": [
    {
      "matcher": ".*",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); FROM=$(echo \"$INPUT\" | jq -r \".from_phase\"); TO=$(echo \"$INPUT\" | jq -r \".to_phase\"); STATE_FILE=\".claude/sdlc-state.json\"; # Verify all gates passed for from_phase GATES_PASSED=$(jq \".phases.$FROM.gates_passed | length\" \"$STATE_FILE\"); GATES_REQUIRED=$(jq \".gates.$FROM | length\" templates/phase-state.json); if [ \"$GATES_PASSED\" -lt \"$GATES_REQUIRED\" ]; then echo \"{\\\"decision\\\": \\\"block\\\", \\\"reason\\\": \\\"Phase $FROM has unmet gate requirements\\\"}\"; else # Allow transition and create checkpoint jq \".current_phase = \\\"$TO\\\"\" \"$STATE_FILE\" > \"${STATE_FILE}.tmp\" && mv \"${STATE_FILE}.tmp\" \"$STATE_FILE\"; fi'",
          "timeout": 5
        }
      ]
    }
  ]
}
```

---

## Deployment Gate Configuration

### Phase-Based Deployment Control

Deployment commands are only allowed in the release phase.

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); CMD=$(echo \"$INPUT\" | jq -r \".tool_input.command\"); if echo \"$CMD\" | grep -qE \"(git push|deploy|kubectl apply|docker push)\"; then STATE_FILE=\".claude/sdlc-state.json\"; PHASE=$(jq -r \".current_phase\" \"$STATE_FILE\"); if [ \"$PHASE\" != \"release\" ]; then echo \"{\\\"decision\\\": \\\"block\\\", \\\"reason\\\": \\\"Deployment commands only allowed in release phase. Current: $PHASE\\\"}\"; fi; fi'",
          "timeout": 5
        }
      ]
    }
  ]
}
```

### Deployment Checklist

Before allowing deployment, verify:

```json
{
  "deployment_prerequisites": {
    "required": [
      "all_tests_pass",
      "lint_clean",
      "code_review_approved",
      "docs_synced"
    ],
    "recommended": [
      "performance_validated",
      "security_scan_pass",
      "coverage_threshold_met"
    ]
  }
}
```

---

## Custom Gate Configuration

### Adding Custom Gates

1. Define gate in phase-state.json:

```json
{
  "gates": {
    "implementation": [
      "code_complete",
      "unit_tests_pass",
      "lint_pass",
      "my_custom_gate"  // Add here
    ]
  }
}
```

2. Add hook to mark gate as passed:

```json
{
  "PostToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); CMD=$(echo \"$INPUT\" | jq -r \".tool_input.command\"); if echo \"$CMD\" | grep -q \"my_validation_command\"; then OUTPUT=$(echo \"$INPUT\" | jq -r \".tool_result.stdout\"); if echo \"$OUTPUT\" | grep -q \"PASSED\"; then STATE_FILE=\".claude/sdlc-state.json\"; PHASE=$(jq -r \".current_phase\" \"$STATE_FILE\"); jq \".phases.$PHASE.gates_passed += [\\\"my_custom_gate\\\"]\" \"$STATE_FILE\" > tmp && mv tmp \"$STATE_FILE\"; fi; fi'",
          "timeout": 10
        }
      ]
    }
  ]
}
```

### Gate Override (Emergency)

For emergency bypasses:

```bash
# Mark gate as passed manually
jq '.phases.implementation.gates_passed += ["blocked_gate"]' .claude/sdlc-state.json > tmp && mv tmp .claude/sdlc-state.json

# Document override in activity log
echo "$(date) [SDLC] OVERRIDE: Gate 'blocked_gate' manually passed - reason: emergency fix" >> .claude/sdlc-activity.log
```

---

## Monitoring and Reporting

### Gate Status Dashboard

Query current gate status:

```bash
# Show all gate status
jq '{
  phase: .current_phase,
  gates_passed: .phases[.current_phase].gates_passed,
  gates_required: .phases[.current_phase].gates_required
}' .claude/sdlc-state.json
```

### Gate History

Track gate passage over time in activity log:

```
2026-01-22T10:30:00 [SDLC] Gate passed: unit_tests_pass (implementation)
2026-01-22T10:31:00 [SDLC] Gate passed: lint_pass (implementation)
2026-01-22T10:35:00 [SDLC] Gate FAILED: security_scan (implementation) - 2 issues
2026-01-22T10:45:00 [SDLC] Gate passed: security_scan (implementation) - issues resolved
```

---

## Integration with CI/CD

### GitHub Actions Integration

```yaml
# .github/workflows/sdlc-gates.yml
name: SDLC Gate Validation

on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  gates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate SDLC State
        run: |
          if [ -f ".claude/sdlc-state.json" ]; then
            PHASE=$(jq -r '.current_phase' .claude/sdlc-state.json)
            GATES=$(jq '.phases.'$PHASE'.gates_passed | length' .claude/sdlc-state.json)
            echo "Current phase: $PHASE"
            echo "Gates passed: $GATES"
          fi

      - name: Run Quality Checks
        run: |
          cd backend
          uv run pytest
          uv run ruff check .
```

---

## Best Practices

### 1. Gate Granularity

- Keep gates atomic and verifiable
- Avoid compound gates that check multiple things
- Name gates clearly (verb_noun format)

### 2. Timeout Tuning

- Set realistic timeouts for each check
- Consider CI environment performance
- Add buffer for network operations

### 3. Error Handling

- Always capture and log gate failures
- Provide actionable error messages
- Allow graceful degradation

### 4. Recovery Procedures

- Document how to recover from gate failures
- Provide manual override mechanisms
- Track overrides for audit purposes

---

**Last Updated:** 2026-01-22
**Version:** 2.0.0
