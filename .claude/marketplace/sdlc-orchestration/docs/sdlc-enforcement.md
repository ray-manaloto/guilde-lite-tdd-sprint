# SDLC Confirmation Enforcement System

## Overview

The SDLC Confirmation Enforcement System is a hook-based workflow orchestration layer that ensures developers follow structured software development practices. It uses a state-driven approach with user confirmation gates to prevent ad-hoc tool usage for tasks that benefit from parallel agent workflows.

## System Architecture

### Three-Layer Hook System

The enforcement system operates through three hook types that intercept user actions and tool usage:

1. **UserPromptSubmit Hooks** - Detect workflow triggers and manage confirmation flow
2. **PreToolUse Hooks** - Block restricted tools until workflow confirmation or bypass
3. **PostToolUse Hooks** - Validate outputs and enforce quality gates (backpressure)

### State File Management

The system maintains workflow state through JSON files in the `.claude/` directory:

| File | Purpose | Lifecycle |
|------|---------|-----------|
| `.claude/sdlc-pending-confirm.json` | Blocks tools until user confirms workflow choice | Created on detection, deleted on user response |
| `.claude/sdlc-research-active.json` | Indicates research workflow is running | Created on workflow start, persists during research |
| `.claude/sdlc-research-bypass.json` | User opted for manual approach (bypass enabled) | Created on bypass choice, persists for session |
| `.claude/sdlc-state.json` | Tracks current SDLC phase and agent completion | Created on workflow start, updated per phase |
| `.claude/sdlc-activity.log` | Audit log of agent completions and code writes | Append-only log file |

## Confirmation Flow

### 1. Task Detection (UserPromptSubmit)

The system uses regex pattern matching to detect tasks requiring structured workflows:

#### Feature Implementation Detection

**Pattern:** `(implement|build|create|develop|add).*(feature|module|system|service|functionality)`

**Action:** Adds prompt suggesting `/sdlc-orchestration:full-feature` workflow

**Example:**
```
User: "Implement a user authentication module"
System: "[SDLC REQUIRED] Use /sdlc-orchestration:full-feature for structured development."
```

#### Research Task Detection

**Pattern:** `(research|investigate|evaluate|compare|analyze|review|audit|assess).*(technolog|librar|framework|tool|skill|approach|option|solution|pattern)`

**Action:** Creates `sdlc-pending-confirm.json` and prompts user for confirmation

**Example:**
```
User: "Research the best framework for real-time chat"
System: "[SDLC CONFIRMATION REQUIRED]

Research task detected. You MUST ask the user:

> This looks like a research task. I should use /sdlc-orchestration:research to spawn 3 parallel agents
> (Research Scientist, Business Analyst, Software Architect) for comprehensive investigation.
>
> Options:
> 1. Yes, use research workflow (recommended)
> 2. No, I want manual research (creates bypass)
>
> Which do you prefer?

Do NOT proceed with any research tools until user responds."
```

#### Skill/Plugin Discovery Detection

**Pattern:** `(find|search|add|install).*(skill|plugin|agent|mcp)`

**Action:** Creates `sdlc-pending-confirm.json` with type `skill-discovery`

**Example:**
```
User: "Find a skill for web scraping"
System: "[SDLC CONFIRMATION REQUIRED]

Skill/plugin discovery detected. You MUST ask the user:

> This is a skill discovery task. I should use /sdlc-orchestration:research for parallel investigation.
>
> Options:
> 1. Yes, use research workflow (recommended)
> 2. No, I want manual search (creates bypass)
>
> Which do you prefer?

Do NOT proceed until user responds."
```

### 2. User Response Processing

When `sdlc-pending-confirm.json` exists, the system monitors user responses:

#### Option 1: Workflow Confirmation

**User Input Pattern:** `(yes|option 1|use research|recommended)`

**Actions:**
1. Deletes `sdlc-pending-confirm.json`
2. Prompts Claude to invoke `/sdlc-orchestration:research`

**State Transition:**
```
pending-confirm (deleted) → research-active (created on workflow invocation)
```

#### Option 2: Manual Bypass

**User Input Pattern:** `(no|option 2|manual|bypass)`

**Actions:**
1. Deletes `sdlc-pending-confirm.json`
2. Creates `sdlc-research-bypass.json` with timestamp and reason

**State Transition:**
```
pending-confirm (deleted) → research-bypass (created, persists for session)
```

**Bypass State Example:**
```json
{
  "bypassed_at": "2026-01-21T15:30:00Z",
  "reason": "user_requested"
}
```

### 3. Workflow Activation

When Claude invokes a research workflow:

**Trigger Pattern:** `/sdlc-orchestration:research`

**Actions:**
1. Creates `sdlc-research-active.json` with status and timestamp
2. Removes `sdlc-pending-confirm.json` if it exists
3. Adds prompt confirming activation

**Active State Example:**
```json
{
  "started_at": "2026-01-21T15:32:00Z",
  "status": "active"
}
```

## Blocked Operations

### WebSearch Blocking

**Tool:** `WebSearch`

**Blocking Logic:**
```bash
if [ -f "$CONFIRM_FILE" ]; then
  # Block: User has not responded to confirmation prompt
  decision="block"
  reason="Pending user confirmation for research workflow"
elif [ ! -f "$RESEARCH_FILE" ] && [ ! -f "$BYPASS_FILE" ]; then
  # Block: No active workflow and no bypass granted
  decision="block"
  reason="WebSearch requires research workflow. Ask user for confirmation."
fi
```

**Allowed Scenarios:**
- `sdlc-research-active.json` exists (workflow running)
- `sdlc-research-bypass.json` exists (user opted for manual)

**Blocked Scenarios:**
- `sdlc-pending-confirm.json` exists (awaiting user response)
- Neither research-active nor bypass file exists

### WebFetch Blocking (Skill/Plugin URLs)

**Tool:** `WebFetch`

**URL Pattern:** `github.com.*(skill|plugin|agent)`

**Blocking Logic:**
```bash
URL=$(echo "$INPUT" | jq -r ".tool_input.url // empty")
if echo "$URL" | grep -qiE "github.com.*(skill|plugin|agent)"; then
  if [ -f "$CONFIRM_FILE" ]; then
    decision="block"
    reason="Pending user confirmation"
  elif [ ! -f "$RESEARCH_FILE" ] && [ ! -f "$BYPASS_FILE" ]; then
    decision="block"
    reason="Skill/plugin fetch requires research workflow or user bypass"
  fi
fi
```

**Rationale:** Skill discovery benefits from parallel research by multiple agent perspectives.

### Bash Command Blocking

#### Git Clone Restriction (Skills/Plugins)

**Pattern:** `git clone.*(skill|plugin|marketplace)`

**Blocking Logic:**
```bash
CMD=$(echo "$INPUT" | jq -r ".tool_input.command // empty")
if echo "$CMD" | grep -qiE "git clone.*(skill|plugin|marketplace)"; then
  if [ ! -f "$RESEARCH_FILE" ] && [ ! -f "$BYPASS_FILE" ]; then
    decision="block"
    reason="Cloning skills/plugins requires research workflow or user bypass"
  fi
fi
```

#### Deployment Command Restriction

**Patterns:** `(git push|deploy|kubectl apply)`

**Blocking Logic:**
```bash
if echo "$CMD" | grep -qE "(git push|deploy|kubectl apply)"; then
  STATE_FILE=".claude/sdlc-state.json"
  if [ -f "$STATE_FILE" ]; then
    PHASE=$(jq -r ".current_phase" "$STATE_FILE")
    if [ "$PHASE" != "release" ]; then
      decision="block"
      reason="Deployment commands only allowed in release phase. Current: $PHASE"
    fi
  fi
fi
```

**Rationale:** Prevents premature deployments before quality gates are passed.

### Write Tool Logging

**Tool:** `Write`

**File Pattern:** `\.(py|ts|tsx|js|jsx)$`

**Action:** Logs code writes to activity log (non-blocking)

```bash
echo "[SDLC] Code write: $FILE" >> ".claude/sdlc-activity.log"
```

## Phase Gate Enforcement

### Phase Sequence Validation

**Enforced Sequence:**
```
requirements → design → implementation → quality → release
```

### Phase Jump Detection

**UserPromptSubmit Hook Logic:**
```bash
STATE_FILE=".claude/sdlc-state.json"
PHASE=$(jq -r ".current_phase" "$STATE_FILE")

# Block implementation during requirements phase
if [ "$PHASE" = "requirements" ] && echo "$PROMPT" | grep -qiE "(implement|code|build)"; then
  addToPrompt="[SDLC Gate] Design phase must complete before implementation. Current phase: requirements."
fi

# Block release during design phase
if [ "$PHASE" = "design" ] && echo "$PROMPT" | grep -qiE "(deploy|release|production)"; then
  addToPrompt="[SDLC Gate] Implementation and quality phases must complete before release. Current phase: design."
fi
```

### State File Structure

**Location:** `.claude/sdlc-state.json`

**Schema:**
```json
{
  "track_id": "user-auth-module",
  "current_phase": "implementation",
  "started_at": "2026-01-21T10:00:00Z",
  "phases": {
    "requirements": {
      "status": "completed",
      "started_at": "2026-01-21T10:00:00Z",
      "agents_completed": ["ceo-stakeholder", "business-analyst", "research-scientist"]
    },
    "design": {
      "status": "completed",
      "started_at": "2026-01-21T10:15:00Z",
      "agents_completed": ["software-architect", "data-scientist"]
    },
    "implementation": {
      "status": "in_progress",
      "started_at": "2026-01-21T10:30:00Z",
      "agents_completed": ["staff-engineer"]
    },
    "quality": {
      "status": "pending"
    },
    "release": {
      "status": "pending"
    }
  }
}
```

### State File Initialization

**Trigger:** Invoking `/sdlc-orchestration:full-feature` or `/sdlc-orchestration:phase`

**Hook Logic:**
```bash
if echo "$PROMPT" | grep -qiE "sdlc-orchestration:(full-feature|phase)"; then
  STATE_FILE=".claude/sdlc-state.json"
  FEATURE=$(extract_feature_name)
  TRACK_ID=$(echo "$FEATURE" | tr " " "-" | tr "[:upper:]" "[:lower:]" | head -c 50)

  # Create initial state
  cat > "$STATE_FILE" <<EOF
{
  "track_id": "$TRACK_ID",
  "current_phase": "requirements",
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "phases": {
    "requirements": {"status": "in_progress", "started_at": "$(date)"},
    "design": {"status": "pending"},
    "implementation": {"status": "pending"},
    "quality": {"status": "pending"},
    "release": {"status": "pending"}
  }
}
EOF
fi
```

## Backpressure Validation

Backpressure hooks run **after** tool execution to validate quality and catch errors early.

### PostToolUse: Write Hook (Python)

**Trigger:** Write tool completes for `.py` files

**Validation:** Runs `ruff check` on written file

**Logic:**
```bash
FILE=$(echo "$INPUT" | jq -r ".tool_input.file_path")
if echo "$FILE" | grep -qE "\\.py$"; then
  if command -v ruff >/dev/null 2>&1; then
    ruff check "$FILE" --quiet || echo "{\"addToPrompt\": \"[SDLC Backpressure] Lint issues detected in $FILE. Run ruff check to see details.\"}"
  fi
fi
```

**Effect:** Notifies Claude immediately if code has lint violations

### PostToolUse: Write Hook (TypeScript)

**Trigger:** Write tool completes for `.ts` or `.tsx` files

**Validation:** Runs `tsc --noEmit` on written file

**Logic:**
```bash
FILE=$(echo "$INPUT" | jq -r ".tool_input.file_path")
if echo "$FILE" | grep -qE "\\.(ts|tsx)$"; then
  if command -v tsc >/dev/null 2>&1; then
    cd "$CLAUDE_PROJECT_ROOT" && tsc --noEmit "$FILE" || echo "{\"addToPrompt\": \"[SDLC Backpressure] Type errors detected in $FILE. Run tsc --noEmit to see details.\"}"
  fi
fi
```

**Effect:** Catches type errors immediately after code write

### PostToolUse: Bash Hook

**Trigger:** Bash tool completes

**Validation:** Scans stdout for error indicators

**Logic:**
```bash
OUTPUT=$(echo "$INPUT" | jq -r ".tool_result.stdout")
if echo "$OUTPUT" | grep -qiE "(error|failed|exception)"; then
  echo "{\"addToPrompt\": \"[SDLC Backpressure] Command output contains errors. Review and fix before proceeding.\"}"
fi
```

**Effect:** Alerts Claude to command failures

### PostToolUse: Task Hook (Agent Completion Tracking)

**Trigger:** Task tool completes with SDLC agent

**Validation:** Updates state file with completed agent

**Logic:**
```bash
AGENT=$(echo "$INPUT" | jq -r ".tool_input.subagent_type")
if echo "$AGENT" | grep -q "sdlc-orchestration:"; then
  # Log completion
  echo "$(date) [SDLC] Agent completed: $AGENT" >> ".claude/sdlc-activity.log"

  # Update state file
  ROLE=$(echo "$AGENT" | sed "s/sdlc-orchestration://")
  PHASE=$(jq -r ".current_phase" "$STATE_FILE")

  # Add agent to completed list if not already present
  jq ".phases.$PHASE.agents_completed += [\"$ROLE\"]" "$STATE_FILE" > "${STATE_FILE}.tmp"
  mv "${STATE_FILE}.tmp" "$STATE_FILE"
fi
```

**Effect:** Tracks which agents have completed work in each phase

## Workflow Examples

### Example 1: Research Task with Confirmation

**User Request:**
```
User: "Research the best database for our real-time analytics system"
```

**System Flow:**

1. **UserPromptSubmit Hook** detects research pattern
2. Creates `sdlc-pending-confirm.json`:
   ```json
   {
     "type": "research",
     "detected_at": "2026-01-21T10:00:00Z"
   }
   ```
3. **Adds confirmation prompt** to Claude's context
4. **Claude asks user:**
   ```
   This looks like a research task. I should use /sdlc-orchestration:research to spawn 3 parallel agents.

   Options:
   1. Yes, use research workflow (recommended)
   2. No, I want manual research (creates bypass)

   Which do you prefer?
   ```
5. **User responds:** "Yes, use the research workflow"
6. **UserPromptSubmit Hook** detects confirmation
7. **Deletes** `sdlc-pending-confirm.json`
8. **Prompts Claude** to invoke workflow
9. **Claude invokes:** `/sdlc-orchestration:research "best database for real-time analytics"`
10. **UserPromptSubmit Hook** creates `sdlc-research-active.json`
11. **PreToolUse blocks removed** - WebSearch/WebFetch now allowed
12. **Three parallel agents execute:**
    - Research Scientist
    - Business Analyst
    - Software Architect

### Example 2: Manual Bypass

**User Request:**
```
User: "Find a skill for code formatting"
```

**System Flow:**

1. **UserPromptSubmit Hook** detects skill discovery pattern
2. Creates `sdlc-pending-confirm.json`
3. **Claude asks user for confirmation**
4. **User responds:** "No, I'll search manually"
5. **UserPromptSubmit Hook** detects bypass choice
6. **Deletes** `sdlc-pending-confirm.json`
7. **Creates** `sdlc-research-bypass.json`:
   ```json
   {
     "bypassed_at": "2026-01-21T10:05:00Z",
     "reason": "user_requested"
   }
   ```
8. **PreToolUse blocks removed** - WebSearch/WebFetch allowed for session
9. **Claude proceeds** with manual search tools

### Example 3: Deployment Blocked

**User Request:**
```
User: "Deploy the authentication module to production"
```

**System Flow:**

1. **State file shows** current phase is `implementation`
2. **UserPromptSubmit Hook** detects deployment keyword
3. **Adds gate warning:**
   ```
   [SDLC Gate] Implementation and quality phases must complete before release.
   Current phase: implementation.
   ```
4. **If user tries:** `kubectl apply -f deploy.yaml`
5. **PreToolUse Bash Hook** blocks command:
   ```
   [SDLC BLOCKED] Deployment commands only allowed in release phase.
   Current: implementation
   ```

### Example 4: Code Quality Backpressure

**User Request:**
```
User: "Create a Python function to validate email addresses"
```

**System Flow:**

1. **Claude writes** `validators.py`
2. **PostToolUse Write Hook** triggers
3. **Runs** `ruff check validators.py`
4. **Lint error detected:** Missing import
5. **Adds prompt:**
   ```
   [SDLC Backpressure] Lint issues detected in validators.py.
   Run ruff check to see details.
   ```
6. **Claude fixes** lint issues before proceeding

## Configuration and Customization

### Adjusting Detection Patterns

**File:** `.claude/plugins/sdlc-orchestration/hooks/hooks.json`

**Feature Implementation Pattern:**
```bash
# Current pattern
"(implement|build|create|develop|add).*(feature|module|system|service|functionality)"

# Add new keywords
"(implement|build|create|develop|add|construct).*(feature|module|system|service|functionality|component)"
```

**Research Pattern:**
```bash
# Current pattern
"(research|investigate|evaluate|compare|analyze|review|audit|assess).*(technolog|librar|framework|tool|skill|approach|option|solution|pattern)"

# Add new contexts
"(research|investigate|evaluate|compare|analyze|review|audit|assess|explore).*(technolog|librar|framework|tool|skill|approach|option|solution|pattern|architecture)"
```

### Disabling Enforcement Temporarily

**Method 1: Delete state files**
```bash
rm .claude/sdlc-pending-confirm.json
rm .claude/sdlc-research-active.json
rm .claude/sdlc-research-bypass.json
```

**Method 2: Create permanent bypass**
```bash
echo '{"bypassed_at":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","reason":"testing"}' > .claude/sdlc-research-bypass.json
```

**Method 3: Modify hooks.json**
```json
{
  "PreToolUse": [
    {
      "matcher": "WebSearch",
      "hooks": []  // Empty hooks = no blocking
    }
  ]
}
```

### Adding Custom Phase Gates

**Example: Prevent database changes outside migration phase**

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); CMD=$(echo \"$INPUT\" | jq -r \".tool_input.command // empty\"); if echo \"$CMD\" | grep -qE \"(alembic|migrate|schema)\"; then STATE_FILE=\".claude/sdlc-state.json\"; PHASE=$(jq -r \".current_phase\" \"$STATE_FILE\"); if [ \"$PHASE\" != \"implementation\" ]; then echo \"{\\\"decision\\\": \\\"block\\\", \\\"reason\\\": \\\"Database migrations only allowed in implementation phase\\\"}\"; fi; fi'",
          "timeout": 5
        }
      ]
    }
  ]
}
```

## Troubleshooting

### Issue: Workflow Not Triggering

**Symptoms:** User says "research X" but no confirmation prompt appears

**Diagnosis:**
```bash
# Check if state files exist
ls -la .claude/sdlc-*.json

# Check hooks.json syntax
jq . .claude/plugins/sdlc-orchestration/hooks/hooks.json

# View activity log
tail -20 .claude/sdlc-activity.log
```

**Solutions:**
- Verify regex pattern matches user input
- Check `CLAUDE_PROJECT_ROOT` environment variable
- Ensure hooks.json is valid JSON

### Issue: Tools Blocked Even After Confirmation

**Symptoms:** WebSearch blocked after user confirmed workflow

**Diagnosis:**
```bash
# Check state files
cat .claude/sdlc-pending-confirm.json  # Should not exist
cat .claude/sdlc-research-active.json  # Should exist
```

**Solutions:**
```bash
# Manually clean pending confirm
rm .claude/sdlc-pending-confirm.json

# Manually activate research
echo '{"started_at":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","status":"active"}' > .claude/sdlc-research-active.json
```

### Issue: Lint Backpressure Not Working

**Symptoms:** Code written but no lint warnings appear

**Diagnosis:**
```bash
# Check if ruff is installed
which ruff

# Test lint manually
ruff check path/to/file.py
```

**Solutions:**
```bash
# Install ruff
pip install ruff

# Or disable backpressure validation in hooks.json
# Remove PostToolUse Write hooks for linting
```

### Issue: State File Corruption

**Symptoms:** Phase transitions fail or gates don't work

**Diagnosis:**
```bash
# Validate JSON
jq . .claude/sdlc-state.json
```

**Solutions:**
```bash
# Backup and reset
cp .claude/sdlc-state.json .claude/sdlc-state.json.bak
rm .claude/sdlc-state.json

# Reinitialize by invoking workflow again
# Or manually create valid state:
cat > .claude/sdlc-state.json <<EOF
{
  "track_id": "new-feature",
  "current_phase": "requirements",
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "phases": {
    "requirements": {"status": "in_progress", "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"},
    "design": {"status": "pending"},
    "implementation": {"status": "pending"},
    "quality": {"status": "pending"},
    "release": {"status": "pending"}
  }
}
EOF
```

## Best Practices

### For Users

1. **Respond clearly to confirmation prompts**
   - Use explicit "yes" or "no" rather than ambiguous responses
   - If unsure, choose workflow option (Option 1) for comprehensive results

2. **Trust the phase gates**
   - Don't try to skip phases (requirements → release)
   - Complete each phase's objectives before advancing

3. **Review backpressure warnings**
   - Fix lint/type errors immediately rather than accumulating technical debt
   - Investigate bash command errors before proceeding

4. **Clean up state files between sessions**
   ```bash
   # After completing a feature
   rm .claude/sdlc-*.json
   ```

### For System Administrators

1. **Monitor activity logs**
   ```bash
   tail -f .claude/sdlc-activity.log
   ```

2. **Audit state file transitions**
   ```bash
   # Track state changes with git
   git add .claude/sdlc-state.json
   git commit -m "Phase transition: design → implementation"
   ```

3. **Customize patterns for team workflow**
   - Adjust regex patterns to match team vocabulary
   - Add domain-specific phase gates

4. **Document bypass decisions**
   ```bash
   # Add reason when creating bypass
   echo '{"bypassed_at":"'$(date)'","reason":"urgent hotfix","ticket":"JIRA-123"}' > .claude/sdlc-research-bypass.json
   ```

## Security Considerations

### 1. State File Tampering

**Risk:** User manually edits state files to bypass gates

**Mitigation:**
- Use file permissions to restrict write access
- Implement cryptographic signatures on state files
- Audit state file changes via git history

### 2. Bypass Abuse

**Risk:** User creates permanent bypass file to avoid workflows

**Mitigation:**
- Set TTL on bypass files (auto-delete after N hours)
- Log bypass creation with user attribution
- Require approval for bypass in team environments

### 3. Hook Injection

**Risk:** Malicious hooks.json modifications

**Mitigation:**
- Validate hooks.json syntax on startup
- Sign hooks.json with trusted key
- Use file integrity monitoring (FIM) tools

## Future Enhancements

### Planned Features

1. **Workflow Templates**
   - Predefined workflows for common tasks (API endpoint, background job, etc.)
   - Template-based state file initialization

2. **Agent Performance Metrics**
   - Track agent completion times
   - Quality metrics per agent type

3. **Phase Transition Automation**
   - Auto-advance phases when all agents complete
   - Notification system for phase milestones

4. **Enhanced Backpressure**
   - Security scanning (Bandit, Semgrep)
   - Dependency vulnerability checks
   - Test coverage requirements

5. **Team Collaboration**
   - Multi-user state synchronization
   - Role-based access control for phases
   - Approval workflows for phase gates

## Documentation Sync Enforcement

The documentation sync system ensures that code, requirements, and documentation stay in sync throughout development.

### State File

**Location:** `.claude/sdlc-doc-sync.json`

**Schema:**
```json
{
  "code_changes": [
    {"file": "backend/app/services/auth.py", "timestamp": "2026-01-21T10:00:00Z"}
  ],
  "requirements_changes": [
    {"file": "docs/requirements.md", "timestamp": "2026-01-21T10:05:00Z"}
  ],
  "pending_sync": true,
  "last_doc_update": null,
  "skipped_at": null
}
```

### Triggers

#### Code File Changes
**Pattern:** `\.(py|ts|tsx|js|jsx)$`

**Behavior:**
1. Adds file to `code_changes` array (max 20 entries)
2. After 5+ code files modified without doc update, sets `pending_sync = true`
3. Prompts: "Consider invoking documentation-engineer agent to update docs"

#### Requirements/Plan Changes
**Pattern:** `(requirements|user.?stor|spec|plan|task|IMPLEMENTATION_PLAN)\.md$`

**Behavior:**
1. Adds file to `requirements_changes` array
2. Immediately sets `pending_sync = true`
3. Prompts: "Documentation should be updated to stay in sync"

#### Documentation Updates
**Pattern:** `(README|CHANGELOG|docs/.*|documentation)\.md$`

**Behavior:**
1. Clears `code_changes` and `requirements_changes` arrays
2. Sets `pending_sync = false`
3. Updates `last_doc_update` timestamp
4. Prompts: "Documentation updated. Sync state cleared."

### Release Gate

When `pending_sync = true` and user mentions commit/deploy/release:

```
[SDLC DOC-SYNC REQUIRED]

Documentation is out of sync:
- Code files changed: 5
- Requirements/plan files changed: 1

Before proceeding with commit/deploy/release, you SHOULD:
1. Invoke documentation-engineer agent to update relevant docs
2. Or explicitly acknowledge: "skip doc sync" to proceed without updating
```

### Skip Acknowledgment

User can bypass with: "skip doc sync"

**Behavior:**
1. Sets `pending_sync = false`
2. Records `skipped_at` timestamp
3. Prompts: "Documentation sync skipped by user acknowledgment"

### Documentation Agent Integration

When documentation agents complete (via Task tool):
- Patterns: `sdlc-orchestration:docs`, `documentation-engineer`, `technical-writer`
- Behavior: Clears sync state, sets `last_doc_update`

## Related Documentation

- [SDLC Orchestrator Skill](../skills/sdlc-orchestrator/SKILL.md) - Full workflow documentation
- [Agent Role Definitions](../agents/) - Individual agent responsibilities
- [Hooks Reference](../hooks/hooks.json) - Complete hook configurations
- [State Templates](../templates/) - JSON schemas for state files

## Support

For issues or questions about the enforcement system:

1. Check [Troubleshooting](#troubleshooting) section above
2. Review activity log: `.claude/sdlc-activity.log`
3. Validate state files with `jq` command
4. Open an issue with state file contents and error messages

---

**Last Updated:** 2026-01-21
**Version:** 1.0.0
**Maintainer:** SDLC Orchestration Plugin Team
