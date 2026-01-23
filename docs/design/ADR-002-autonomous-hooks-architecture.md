# ADR-002: Autonomous Hooks Architecture for Claude Code

## Status
Proposed

## Context

The project uses Claude Code hooks (PreToolUse, PostToolUse, UserPromptSubmit, etc.) to enforce SDLC workflows. The current implementation requires user confirmation for many operations, which interrupts autonomous agent workflows.

**Problem Statement:**
- Current hooks require too much user interaction for routine operations
- Autonomous SDLC agents need to execute without constant approval prompts
- Security-sensitive operations still need human oversight
- Backpressure signals (lint errors, test failures) should be automated

**Requirements:**
1. Minimize user prompts during autonomous operation
2. Maintain security for sensitive operations (secrets, destructive commands)
3. Provide automated quality gates via backpressure
4. Support SDLC phase enforcement without blocking agent work

## Decision

Implement a **Tiered Permission Model** with three trust levels:

### Trust Level 1: Auto-Approve (No User Interaction)
Operations that are inherently safe and reversible.

### Trust Level 2: Warn-and-Proceed (Soft Gate)
Operations that may have side effects but are recoverable.

### Trust Level 3: Require Approval (Hard Gate)
Operations that are destructive, security-sensitive, or irreversible.

---

## Architecture

### 1. Permission Rules Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Claude Code Autonomous Permissions",
  "version": "3.0.0",

  "permissions": {
    "auto_approve": {
      "description": "Tools and commands that execute without prompts",
      "tools": [
        "Read",
        "Grep",
        "Glob",
        "Task",
        "WebSearch",
        "WebFetch",
        "NotebookEdit",
        "ListMcpResourcesTool",
        "ReadMcpResourceTool"
      ],
      "bash_patterns": [
        "git status*",
        "git diff*",
        "git log*",
        "git branch*",
        "git show*",
        "git ls-files*",
        "git rev-parse*",
        "cd *",
        "ls *",
        "pwd",
        "which *",
        "echo *",
        "cat *",
        "head *",
        "tail *",
        "wc *",
        "date",
        "uv run pytest*",
        "uv run ruff*",
        "uv run mypy*",
        "uv run bandit*",
        "uv run alembic*",
        "bun run test*",
        "bun run lint*",
        "bun run type-check*",
        "bun run prettier*",
        "npm test*",
        "npm run lint*",
        "npm run build*",
        "docker ps*",
        "docker logs*",
        "docker inspect*",
        "gh pr view*",
        "gh issue view*",
        "gh api*",
        "jq *",
        "curl -s *",
        "curl --silent *"
      ]
    },

    "warn_and_proceed": {
      "description": "Operations that proceed with a warning injected into prompt",
      "bash_patterns": [
        "git add *",
        "git stash*",
        "git checkout -b *",
        "git branch -d *",
        "docker build*",
        "docker run*",
        "npm install*",
        "bun install*",
        "uv add*",
        "uv sync*"
      ],
      "write_patterns": [
        "*.py",
        "*.ts",
        "*.tsx",
        "*.js",
        "*.jsx",
        "*.json",
        "*.yaml",
        "*.yml",
        "*.md",
        "*.sql",
        "*.html",
        "*.css"
      ]
    },

    "require_approval": {
      "description": "Operations that MUST have user confirmation",
      "bash_patterns": [
        "git commit*",
        "git push*",
        "git push --force*",
        "git reset --hard*",
        "git checkout .",
        "git restore .",
        "git clean*",
        "git rebase*",
        "git merge*",
        "rm -rf*",
        "rm -r*",
        "sudo *",
        "chmod 777*",
        "docker rm*",
        "docker rmi*",
        "docker system prune*",
        "kubectl delete*",
        "kubectl apply*",
        "terraform apply*",
        "terraform destroy*"
      ],
      "write_patterns": [
        ".env*",
        "*/.env*",
        "*.pem",
        "*.key",
        "*secret*",
        "*credential*",
        "*password*",
        "config/production*",
        "docker-compose.prod*"
      ],
      "edit_patterns": [
        "*/alembic/versions/*.py",
        "*.lock",
        "bun.lock",
        "package-lock.json",
        "uv.lock"
      ]
    }
  }
}
```

### 2. Enhanced Hooks Configuration Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Autonomous SDLC Hooks Configuration",
  "version": "3.0.0",

  "SessionStart": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "AUTONOMOUS MODE ACTIVE. Auto-approved: Read, Grep, Glob, Task, WebSearch, tests, lint. Approval required: git commit/push, .env writes, destructive ops."
        },
        {
          "type": "command",
          "command": "bash -c 'echo \"{\\\"autonomousMode\\\": true, \\\"started_at\\\": \\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\"}\" > \"${CLAUDE_PROJECT_ROOT:-.}/.claude/autonomous-session.json\"'",
          "timeout": 5
        }
      ]
    }
  ],

  "PreToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); FILE=$(echo \"$INPUT\" | jq -r \".tool_input.file_path // .tool_input.path // empty\" 2>/dev/null); if echo \"$FILE\" | grep -qE \"(\\.env|\\.pem|\\.key|secret|credential|password)\"; then echo \"{\\\"decision\\\": \\\"block\\\", \\\"reason\\\": \\\"[SECURITY] Sensitive file detected. Manual confirmation required for: $FILE\\\"}\"; fi; exit 0'",
          "timeout": 5
        },
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); FILE=$(echo \"$INPUT\" | jq -r \".tool_input.file_path // .tool_input.path // empty\" 2>/dev/null); if echo \"$FILE\" | grep -qE \"(\\.lock|bun\\.lock|package-lock\\.json|uv\\.lock)$\"; then echo \"{\\\"decision\\\": \\\"block\\\", \\\"reason\\\": \\\"[BLOCKED] Lock files modified only via package manager\\\"}\"; fi; exit 0'",
          "timeout": 5
        },
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); FILE=$(echo \"$INPUT\" | jq -r \".tool_input.file_path // .tool_input.path // empty\" 2>/dev/null); if echo \"$FILE\" | grep -qE \"/alembic/versions/.*\\.py$\"; then echo \"{\\\"decision\\\": \\\"block\\\", \\\"reason\\\": \\\"[BLOCKED] Do not edit existing migrations. Create new with alembic revision.\\\"}\"; fi; exit 0'",
          "timeout": 5
        }
      ]
    },
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); CMD=$(echo \"$INPUT\" | jq -r \".tool_input.command // empty\" 2>/dev/null); if echo \"$CMD\" | grep -qE \"^(git commit|git push|git reset --hard|git checkout \\.|git restore \\.|git clean|rm -rf|sudo |kubectl delete|kubectl apply|terraform apply|terraform destroy)\"; then echo \"{\\\"decision\\\": \\\"ask\\\", \\\"reason\\\": \\\"[APPROVAL REQUIRED] Potentially destructive command: $CMD\\\"}\"; fi; exit 0'",
          "timeout": 5
        },
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); CMD=$(echo \"$INPUT\" | jq -r \".tool_input.command // empty\" 2>/dev/null); if echo \"$CMD\" | grep -qE \"^(git push --force|git push -f)\"; then echo \"{\\\"decision\\\": \\\"block\\\", \\\"reason\\\": \\\"[BLOCKED] Force push requires explicit user confirmation via message\\\"}\"; fi; exit 0'",
          "timeout": 5
        },
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); CMD=$(echo \"$INPUT\" | jq -r \".tool_input.command // empty\" 2>/dev/null); STATE_FILE=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-state.json\"; if echo \"$CMD\" | grep -qE \"^(git push|kubectl apply|terraform apply)\"; then if [ -f \"$STATE_FILE\" ]; then PHASE=$(jq -r \".current_phase // empty\" \"$STATE_FILE\" 2>/dev/null); if [ \"$PHASE\" != \"release\" ] && [ -n \"$PHASE\" ]; then echo \"{\\\"decision\\\": \\\"block\\\", \\\"reason\\\": \\\"[SDLC GATE] Deployment only in release phase. Current: $PHASE\\\"}\"; fi; fi; fi; exit 0'",
          "timeout": 5
        }
      ]
    }
  ],

  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); FILE=$(echo \"$INPUT\" | jq -r \".tool_input.file_path // .tool_input.path // empty\" 2>/dev/null); if echo \"$FILE\" | grep -qE \"\\.py$\"; then cd \"${CLAUDE_PROJECT_ROOT:-.}/backend\" 2>/dev/null && uv run ruff format \"$FILE\" 2>/dev/null && LINT=$(uv run ruff check \"$FILE\" 2>&1); if [ -n \"$LINT\" ] && echo \"$LINT\" | grep -qvE \"^All checks passed\"; then echo \"{\\\"addToPrompt\\\": \\\"[BACKPRESSURE:LINT] $LINT\\\"}\"; fi; fi; exit 0'",
          "timeout": 15
        },
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); FILE=$(echo \"$INPUT\" | jq -r \".tool_input.file_path // .tool_input.path // empty\" 2>/dev/null); if echo \"$FILE\" | grep -qE \"\\.py$\"; then cd \"${CLAUDE_PROJECT_ROOT:-.}/backend\" 2>/dev/null && TYPE_ERRORS=$(uv run mypy \"$FILE\" --ignore-missing-imports 2>&1 | grep -v \"^Success\"); if [ -n \"$TYPE_ERRORS\" ]; then echo \"{\\\"addToPrompt\\\": \\\"[BACKPRESSURE:TYPE] $TYPE_ERRORS\\\"}\"; fi; fi; exit 0'",
          "timeout": 20
        },
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); FILE=$(echo \"$INPUT\" | jq -r \".tool_input.file_path // .tool_input.path // empty\" 2>/dev/null); if echo \"$FILE\" | grep -qE \"\\.(ts|tsx)$\"; then cd \"${CLAUDE_PROJECT_ROOT:-.}/frontend\" 2>/dev/null && bun run prettier --write \"$FILE\" 2>/dev/null && TYPE_ERRORS=$(bun run type-check 2>&1 | head -20); if echo \"$TYPE_ERRORS\" | grep -qE \"error TS\"; then echo \"{\\\"addToPrompt\\\": \\\"[BACKPRESSURE:TYPE] $TYPE_ERRORS\\\"}\"; fi; fi; exit 0'",
          "timeout": 30
        },
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); FILE=$(echo \"$INPUT\" | jq -r \".tool_input.file_path // .tool_input.path // empty\" 2>/dev/null); if echo \"$FILE\" | grep -qE \"\\.py$\"; then cd \"${CLAUDE_PROJECT_ROOT:-.}/backend\" 2>/dev/null && SECURITY=$(uv run bandit -q \"$FILE\" 2>&1); if [ -n \"$SECURITY\" ]; then echo \"{\\\"addToPrompt\\\": \\\"[BACKPRESSURE:SECURITY] $SECURITY\\\"}\"; fi; fi; exit 0'",
          "timeout": 15
        },
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); FILE=$(echo \"$INPUT\" | jq -r \".tool_input.file_path // .tool_input.path // empty\" 2>/dev/null); if echo \"$FILE\" | grep -qE \"/backend/app/.*\\.py$\"; then MODULE=$(echo \"$FILE\" | sed \"s|.*/backend/app/||\" | sed \"s|/|.|g\" | sed \"s|\\.py$||\"); TEST_PATTERN=\"test_${MODULE##*.}\"; cd \"${CLAUDE_PROJECT_ROOT:-.}/backend\" 2>/dev/null && TEST_RESULT=$(uv run pytest -x -q -k \"$TEST_PATTERN\" --tb=short 2>&1 | tail -15); if echo \"$TEST_RESULT\" | grep -qE \"(FAILED|ERROR)\"; then echo \"{\\\"addToPrompt\\\": \\\"[BACKPRESSURE:TEST] Related tests failed:\\n$TEST_RESULT\\\"}\"; fi; fi; exit 0'",
          "timeout": 60
        }
      ]
    },
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); STDOUT=$(echo \"$INPUT\" | jq -r \".tool_result.stdout // empty\" 2>/dev/null); STDERR=$(echo \"$INPUT\" | jq -r \".tool_result.stderr // empty\" 2>/dev/null); EXIT_CODE=$(echo \"$INPUT\" | jq -r \".tool_result.exit_code // 0\" 2>/dev/null); if [ \"$EXIT_CODE\" != \"0\" ]; then echo \"{\\\"addToPrompt\\\": \\\"[BACKPRESSURE:COMMAND] Exit code $EXIT_CODE. Review output before proceeding.\\\"}\"; fi; exit 0'",
          "timeout": 5
        }
      ]
    },
    {
      "matcher": "Task",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); AGENT=$(echo \"$INPUT\" | jq -r \".tool_input.subagent_type // empty\" 2>/dev/null); STATE_FILE=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-state.json\"; if [ -n \"$AGENT\" ] && [ -f \"$STATE_FILE\" ]; then ROLE=$(echo \"$AGENT\" | sed \"s/.*://\"); PHASE=$(jq -r \".current_phase\" \"$STATE_FILE\" 2>/dev/null); jq \".phases.$PHASE.agents_completed += [\\\"$ROLE\\\"] | .phases.$PHASE.agents_completed |= unique\" \"$STATE_FILE\" > \"${STATE_FILE}.tmp\" && mv \"${STATE_FILE}.tmp\" \"$STATE_FILE\" 2>/dev/null; echo \"$(date -u +%Y-%m-%dT%H:%M:%SZ) Agent completed: $ROLE\" >> \"${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-activity.log\"; fi; exit 0'",
          "timeout": 5
        }
      ]
    }
  ],

  "UserPromptSubmit": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); PROMPT=$(echo \"$INPUT\" | jq -r \".prompt // empty\" 2>/dev/null); STATE_FILE=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-state.json\"; if [ -f \"$STATE_FILE\" ]; then PHASE=$(jq -r \".current_phase // empty\" \"$STATE_FILE\" 2>/dev/null); case \"$PHASE\" in \"requirements\") if echo \"$PROMPT\" | grep -qiE \"(implement|code|build|write code)\"; then echo \"{\\\"addToPrompt\\\": \\\"[SDLC GATE] Complete design phase before implementation. Current: requirements\\\"}\"; fi ;; \"design\") if echo \"$PROMPT\" | grep -qiE \"(deploy|release|production|ship)\"; then echo \"{\\\"addToPrompt\\\": \\\"[SDLC GATE] Complete implementation+quality phases first. Current: design\\\"}\"; fi ;; \"implementation\") if echo \"$PROMPT\" | grep -qiE \"(deploy|release|production|ship)\"; then echo \"{\\\"addToPrompt\\\": \\\"[SDLC GATE] Complete quality phase (tests, review) first. Current: implementation\\\"}\"; fi ;; esac; fi; exit 0'",
          "timeout": 5
        },
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); PROMPT=$(echo \"$INPUT\" | jq -r \".prompt // empty\" 2>/dev/null); if echo \"$PROMPT\" | grep -qiE \"(implement|build|create|develop|add).*(feature|module|system|service|functionality)\"; then STATE_FILE=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-state.json\"; if [ ! -f \"$STATE_FILE\" ]; then echo \"{\\\"addToPrompt\\\": \\\"[SDLC SUGGESTED] Consider /sdlc-orchestration:full-feature for structured development with proper phase gates.\\\"}\"; fi; fi; exit 0'",
          "timeout": 5
        }
      ]
    }
  ],

  "Stop": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'VALIDATION_FILE=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/stop-validation.json\"; mkdir -p \"${CLAUDE_PROJECT_ROOT:-.}/.claude\"; echo \"{\\\"timestamp\\\": \\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\", \\\"checks\\\": {}}\" > \"$VALIDATION_FILE\"; cd \"${CLAUDE_PROJECT_ROOT:-.}/backend\" 2>/dev/null && if command -v uv >/dev/null 2>&1; then TEST_RESULT=$(uv run pytest -x -q --tb=no 2>&1 | tail -3); PASS=$(echo \"$TEST_RESULT\" | grep -cE \"passed\" || echo 0); jq \".checks.tests = {\\\"passed\\\": $([ $PASS -gt 0 ] && echo true || echo false), \\\"output\\\": \\\"$TEST_RESULT\\\"}\" \"$VALIDATION_FILE\" > \"${VALIDATION_FILE}.tmp\" && mv \"${VALIDATION_FILE}.tmp\" \"$VALIDATION_FILE\"; fi; exit 0'",
          "timeout": 120
        },
        {
          "type": "command",
          "command": "bash -c 'VALIDATION_FILE=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/stop-validation.json\"; cd \"${CLAUDE_PROJECT_ROOT:-.}/backend\" 2>/dev/null && if command -v uv >/dev/null 2>&1; then LINT_RESULT=$(uv run ruff check . --quiet 2>&1 | head -5); CLEAN=$([ -z \"$LINT_RESULT\" ] && echo true || echo false); jq \".checks.lint = {\\\"clean\\\": $CLEAN, \\\"issues\\\": \\\"$LINT_RESULT\\\"}\" \"$VALIDATION_FILE\" > \"${VALIDATION_FILE}.tmp\" && mv \"${VALIDATION_FILE}.tmp\" \"$VALIDATION_FILE\" 2>/dev/null; fi; exit 0'",
          "timeout": 30
        },
        {
          "type": "command",
          "command": "bash -c 'VALIDATION_FILE=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/stop-validation.json\"; if [ -f \"$VALIDATION_FILE\" ]; then TESTS=$(jq -r \".checks.tests.passed // true\" \"$VALIDATION_FILE\" 2>/dev/null); LINT=$(jq -r \".checks.lint.clean // true\" \"$VALIDATION_FILE\" 2>/dev/null); if [ \"$TESTS\" = \"false\" ] || [ \"$LINT\" = \"false\" ]; then WARNINGS=\"\"; [ \"$TESTS\" = \"false\" ] && WARNINGS=\"- Tests failing\"; [ \"$LINT\" = \"false\" ] && WARNINGS=\"$WARNINGS\\n- Lint issues\"; echo \"{\\\"addToPrompt\\\": \\\"[STOP VALIDATION] Issues detected:$WARNINGS\\\"}\"; else echo \"{\\\"addToPrompt\\\": \\\"[STOP VALIDATION] All checks passed.\\\"}\"; fi; fi; exit 0'",
          "timeout": 5
        }
      ]
    }
  ],

  "SubagentStop": [
    {
      "matcher": "sdlc-orchestration:.*",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); AGENT=$(echo \"$INPUT\" | jq -r \".subagent_type // empty\" 2>/dev/null); STATE_FILE=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-state.json\"; AGGREGATION_FILE=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-agent-outputs.json\"; TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ); mkdir -p \"${CLAUDE_PROJECT_ROOT:-.}/.claude\"; [ ! -f \"$AGGREGATION_FILE\" ] && echo \"{\\\"agents\\\":[]}\" > \"$AGGREGATION_FILE\"; ROLE=$(echo \"$AGENT\" | sed \"s/sdlc-orchestration://\"); jq \".agents += [{\\\"agent\\\": \\\"$ROLE\\\", \\\"completed_at\\\": \\\"$TIMESTAMP\\\"}]\" \"$AGGREGATION_FILE\" > \"${AGGREGATION_FILE}.tmp\" && mv \"${AGGREGATION_FILE}.tmp\" \"$AGGREGATION_FILE\"; exit 0'",
          "timeout": 5
        }
      ]
    }
  ],

  "SessionStop": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'STATE_FILE=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-state.json\"; CHECKPOINT_FILE=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-checkpoint.json\"; if [ -f \"$STATE_FILE\" ]; then PHASE=$(jq -r \".current_phase // empty\" \"$STATE_FILE\" 2>/dev/null); STATUS=$(jq -r \".phases.$PHASE.status // empty\" \"$STATE_FILE\" 2>/dev/null); if [ \"$STATUS\" = \"in_progress\" ]; then jq \". + {\\\"recovery_pending\\\": true, \\\"checkpoint_at\\\": \\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\"}\" \"$STATE_FILE\" > \"$CHECKPOINT_FILE\"; fi; fi; exit 0'",
          "timeout": 10
        }
      ]
    }
  ]
}
```

### 3. Decision Matrix

| Operation | Trust Level | Decision | Rationale |
|-----------|-------------|----------|-----------|
| **Read Tools** |
| Read, Grep, Glob | 1 | Auto-approve | Read-only, no side effects |
| WebSearch, WebFetch | 1 | Auto-approve | External fetch, no local changes |
| Task (subagents) | 1 | Auto-approve | Sandboxed, logged |
| **Write Tools** |
| Edit/Write .py, .ts, .tsx | 2 | Warn-proceed | Core development, backpressure validates |
| Edit/Write .md, .json | 2 | Warn-proceed | Documentation/config |
| Edit/Write .env, secrets | 3 | Block | Security-sensitive |
| Edit/Write *.lock | 3 | Block | Managed by package managers |
| Edit migrations | 3 | Block | Create new instead |
| **Bash - Git** |
| git status/diff/log | 1 | Auto-approve | Read-only |
| git add | 2 | Warn-proceed | Staging, reversible |
| git commit | 3 | Require approval | Creates history |
| git push | 3 | Require approval | Remote changes |
| git push --force | 3 | Block | Destructive |
| git reset --hard | 3 | Block | Destructive |
| git checkout . | 3 | Block | Destructive |
| **Bash - Tests/Lint** |
| pytest, ruff, mypy | 1 | Auto-approve | Validation only |
| bun test, npm test | 1 | Auto-approve | Validation only |
| bandit (security scan) | 1 | Auto-approve | Validation only |
| **Bash - Package Mgmt** |
| npm/bun install | 2 | Warn-proceed | Modifies deps |
| uv add/sync | 2 | Warn-proceed | Modifies deps |
| **Bash - Docker** |
| docker ps/logs | 1 | Auto-approve | Read-only |
| docker build/run | 2 | Warn-proceed | Creates containers |
| docker rm/rmi | 3 | Require approval | Destructive |
| **Bash - Deployment** |
| kubectl apply | 3 | Require approval | Production changes |
| terraform apply | 3 | Require approval | Infrastructure |
| **SDLC Phase Gates** |
| Implementation before Design | N/A | Soft block | SDLC workflow |
| Release before Quality | N/A | Soft block | SDLC workflow |
| Deploy before Release phase | 3 | Block | SDLC enforcement |

### 4. Backpressure Signal Types

| Signal Type | Source | Severity | Agent Response |
|-------------|--------|----------|----------------|
| `[BACKPRESSURE:LINT]` | ruff check | Warning | Fix before continuing |
| `[BACKPRESSURE:TYPE]` | mypy/tsc | Warning | Fix type errors |
| `[BACKPRESSURE:TEST]` | pytest/jest | Error | Must fix failing tests |
| `[BACKPRESSURE:SECURITY]` | bandit | Critical | Must address vulnerabilities |
| `[BACKPRESSURE:COMMAND]` | Non-zero exit | Warning | Review command output |
| `[SDLC GATE]` | Phase check | Block | Cannot skip phases |
| `[STOP VALIDATION]` | Stop hook | Info | Summary before response |

### 5. Implementation Priority

**Phase 1: Core Permissions (Week 1)**
1. Implement trust level classification in PreToolUse
2. Add auto-approve rules for safe operations
3. Block destructive git commands and sensitive file writes

**Phase 2: Backpressure Integration (Week 2)**
1. PostToolUse lint/format hooks
2. PostToolUse type check hooks
3. Related test execution on file changes
4. Security scan integration

**Phase 3: SDLC Phase Enforcement (Week 3)**
1. Phase gate validation in UserPromptSubmit
2. State tracking across sessions
3. SubagentStop aggregation
4. Session checkpoint/recovery

---

## Consequences

### Positive
- Autonomous agents can execute common operations without interruption
- Security-sensitive operations remain protected
- Backpressure catches issues immediately
- SDLC phases are enforced programmatically

### Negative
- More complex hook configuration to maintain
- Potential for false positives in pattern matching
- Increased hook execution time (mitigated by timeouts)

### Risks
- Pattern matching may miss edge cases
- Timeout values may need tuning
- State files could become stale

### Mitigations
- Comprehensive pattern testing
- Configurable timeouts
- State file cleanup hooks

---

## Alternatives Considered

### 1. Blanket Auto-Approve All
**Rejected:** Too permissive, security risk for destructive operations.

### 2. Blanket Require Approval
**Rejected:** Current state, too many interruptions for autonomous work.

### 3. Allowlist-Only Approach
**Rejected:** Too restrictive, would block legitimate new operations.

### 4. External Permission Service
**Rejected:** Added complexity, network dependency, latency.

---

## Related Skills

The following installed skills provide implementation guidance:

- `skills/pytest-testing/` - Test execution patterns
- `skills/code-auditor/` - Security scanning integration
- `skills/git-pushing/` - Safe git operation patterns

Read with: `cat skills/<skill-name>/SKILL.md`

---

## Appendix: Complete settings.json Integration

```json
{
  "permissions": {
    "allow": [
      "Read(*)",
      "Grep(*)",
      "Glob(*)",
      "Task(*)",
      "WebSearch(*)",
      "WebFetch(*)",
      "Bash(git status*)",
      "Bash(git diff*)",
      "Bash(git log*)",
      "Bash(git branch*)",
      "Bash(git show*)",
      "Bash(cd *)",
      "Bash(ls *)",
      "Bash(pwd)",
      "Bash(cat *)",
      "Bash(head *)",
      "Bash(tail *)",
      "Bash(wc *)",
      "Bash(date)",
      "Bash(which *)",
      "Bash(echo *)",
      "Bash(jq *)",
      "Bash(curl -s *)",
      "Bash(curl --silent *)",
      "Bash(uv run pytest*)",
      "Bash(uv run ruff*)",
      "Bash(uv run mypy*)",
      "Bash(uv run bandit*)",
      "Bash(uv run alembic*)",
      "Bash(cd backend && uv run pytest*)",
      "Bash(cd backend && uv run ruff*)",
      "Bash(cd backend && uv run mypy*)",
      "Bash(cd backend && uv run bandit*)",
      "Bash(cd backend && uv run alembic*)",
      "Bash(bun run test*)",
      "Bash(bun run lint*)",
      "Bash(bun run type-check*)",
      "Bash(bun run prettier*)",
      "Bash(cd frontend && bun run*)",
      "Bash(npm test*)",
      "Bash(npm run lint*)",
      "Bash(npm run build*)",
      "Bash(docker ps*)",
      "Bash(docker logs*)",
      "Bash(docker inspect*)",
      "Bash(gh pr view*)",
      "Bash(gh issue view*)",
      "Bash(gh api*)"
    ],
    "deny": [
      "Edit(.env*)",
      "Edit(*/.env*)",
      "Edit(*.pem)",
      "Edit(*.key)",
      "Edit(*secret*)",
      "Edit(*credential*)",
      "Edit(*/alembic/versions/*.py)",
      "Edit(*.lock)",
      "Edit(bun.lock)",
      "Edit(package-lock.json)",
      "Edit(uv.lock)",
      "Write(.env*)",
      "Write(*/.env*)",
      "Write(*.pem)",
      "Write(*.key)",
      "Bash(git push --force*)",
      "Bash(git push -f*)",
      "Bash(git reset --hard*)",
      "Bash(git checkout .)",
      "Bash(git restore .)",
      "Bash(git clean*)",
      "Bash(rm -rf*)",
      "Bash(sudo *)",
      "Bash(chmod 777*)"
    ]
  },
  "hooks": {
    "PreToolUse": [],
    "PostToolUse": [],
    "UserPromptSubmit": [],
    "Stop": [],
    "SubagentStop": [],
    "SessionStart": [],
    "SessionStop": []
  }
}
```

**Note:** The full hooks configuration from Section 2 should be merged into the `hooks` section. The permissions array provides the fast-path approval/denial, while hooks handle complex conditional logic and backpressure.
