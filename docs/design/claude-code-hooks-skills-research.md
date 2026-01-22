# Research Report: Claude Code Hooks, Skills, and Automation Best Practices

## Executive Summary

This report analyzes Claude Code hooks, skills, and automation capabilities based on official Anthropic documentation, community best practices, and the project's existing implementation. The project already has a sophisticated hook system in place through the SDLC Orchestration plugin. This report provides recommendations for enhancements and additional patterns to implement.

**Key Findings:**
1. Claude Code hooks support 8 lifecycle events with powerful decision control
2. Skills are the new standard for custom slash commands with rich features
3. GitHub Actions integration enables CI/CD automation with `@claude` mentions
4. The project's existing hooks are well-designed but can be enhanced with additional quality gates
5. State persistence patterns enable crash recovery and workflow continuity

---

## Research Question

What hooks, skills, and automation patterns should be implemented to:
1. Enforce quality gates throughout the SDLC process?
2. Validate tool usage with PreToolUse/PostToolUse hooks?
3. Enable state persistence for crash recovery?
4. Keep documentation synchronized with code changes?
5. Streamline the SDLC process with reusable skills?

---

## Methodology

- Fetched official Claude Code documentation from code.claude.com
- Reviewed Anthropic engineering blog best practices
- Analyzed community tutorials from letanure.dev
- Examined GitHub Actions examples from anthropics/claude-code-action
- Audited the project's existing `.claude/settings.json` and hook configurations

---

## Findings

### 1. Hook Lifecycle Events (8 Total)

| Event | When It Fires | Primary Use Cases |
|-------|---------------|-------------------|
| `SessionStart` | Session begins/resumes | Display workflow reminders, load state |
| `UserPromptSubmit` | User submits prompt | Detect task types, enforce workflows |
| `PreToolUse` | Before tool execution | Block dangerous operations, validate inputs |
| `PermissionRequest` | Permission dialog appears | Custom permission handling |
| `PostToolUse` | After tool succeeds | Run linters, track changes, validate output |
| `Stop` | Claude finishes responding | Validate completion, trigger follow-up |
| `SubagentStop` | Subagent finishes | Track agent completion, aggregate results |
| `SessionEnd` | Session terminates | Cleanup, save state |

### 2. Hook Decision Control

**PreToolUse can return:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow" | "deny" | "ask",
    "permissionDecisionReason": "Explanation",
    "updatedInput": { "field": "modified_value" },
    "additionalContext": "Context for Claude"
  }
}
```

**PostToolUse can return:**
```json
{
  "decision": "block",
  "reason": "Must fix issues before proceeding",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Lint errors detected"
  }
}
```

**Stop hook can return:**
```json
{
  "decision": "block",
  "reason": "Task not complete - tests still failing"
}
```

### 3. Current Project Implementation Analysis

**Strengths:**
- Comprehensive PreToolUse guards for .env files, lock files, migrations
- PostToolUse auto-formatting with ruff/prettier
- Type checking (mypy, tsc) after edits
- Security scanning (bandit) on Python files
- SDLC workflow enforcement with research confirmation
- Documentation sync tracking

**Gaps Identified:**
- No `Stop` hook to verify task completion
- No `SubagentStop` hook to aggregate parallel agent results
- No crash recovery/session persistence beyond state files
- Limited test-related hooks (only pattern matching, not actual test runs)

### 4. Recommended Hook Configurations

#### A. Quality Gate: Stop Hook for Task Verification

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'STATE_FILE=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/sdlc-state.json\"; if [ -f \"$STATE_FILE\" ]; then PHASE=$(jq -r \".current_phase\" \"$STATE_FILE\" 2>/dev/null); if [ \"$PHASE\" = \"quality\" ]; then TESTS_PASS=$(cd \"${CLAUDE_PROJECT_ROOT:-.}/backend\" && uv run pytest -x -q 2>&1 | tail -1 | grep -c \"passed\"); if [ \"$TESTS_PASS\" = \"0\" ]; then echo \"{\\\"decision\\\": \\\"block\\\", \\\"reason\\\": \\\"[SDLC] Cannot complete quality phase - tests are failing. Fix tests before stopping.\\\"}\"; fi; fi; fi; exit 0'",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

#### B. Quality Gate: Pre-Commit Validation

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'INPUT=$(cat); CMD=$(echo \"$INPUT\" | jq -r \".tool_input.command // empty\" 2>/dev/null); if echo \"$CMD\" | grep -qE \"git commit\"; then cd \"${CLAUDE_PROJECT_ROOT:-.}/backend\" && uv run pytest -x -q --tb=no 2>&1 | tail -3; RESULT=$?; if [ $RESULT -ne 0 ]; then echo \"{\\\"decision\\\": \\\"block\\\", \\\"reason\\\": \\\"[Quality Gate] Tests must pass before commit\\\"}\"; fi; fi; exit 0'",
            "timeout": 180
          }
        ]
      }
    ]
  }
}
```

#### C. State Persistence for Crash Recovery

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'INPUT=$(cat); CHECKPOINT_DIR=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/checkpoints\"; mkdir -p \"$CHECKPOINT_DIR\"; SESSION_ID=$(echo \"$INPUT\" | jq -r \".session_id // \\\"unknown\\\"\"); TOOL=$(echo \"$INPUT\" | jq -r \".tool_name\"); CHECKPOINT_FILE=\"$CHECKPOINT_DIR/session-${SESSION_ID}.json\"; if [ ! -f \"$CHECKPOINT_FILE\" ]; then echo \"{\\\"session_id\\\":\\\"$SESSION_ID\\\",\\\"started_at\\\":\\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\",\\\"tool_calls\\\":[]}\" > \"$CHECKPOINT_FILE\"; fi; jq \".tool_calls += [{\\\"tool\\\":\\\"$TOOL\\\",\\\"at\\\":\\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\"}] | .last_activity = \\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\"\" \"$CHECKPOINT_FILE\" > \"${CHECKPOINT_FILE}.tmp\" && mv \"${CHECKPOINT_FILE}.tmp\" \"$CHECKPOINT_FILE\" 2>/dev/null; exit 0'",
            "timeout": 5
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'CHECKPOINT_DIR=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/checkpoints\"; if [ -d \"$CHECKPOINT_DIR\" ]; then LATEST=$(ls -t \"$CHECKPOINT_DIR\"/session-*.json 2>/dev/null | head -1); if [ -n \"$LATEST\" ]; then LAST_ACTIVITY=$(jq -r \".last_activity\" \"$LATEST\" 2>/dev/null); TOOL_COUNT=$(jq \".tool_calls | length\" \"$LATEST\" 2>/dev/null); echo \"{\\\"addToPrompt\\\": \\\"[Session Recovery] Previous session found with $TOOL_COUNT tool calls. Last activity: $LAST_ACTIVITY. Use --resume to continue or start fresh.\\\"}\"; fi; fi; exit 0'",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

#### D. Documentation Sync Enhancement

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'INPUT=$(cat); FILE=$(echo \"$INPUT\" | jq -r \".tool_input.file_path // empty\" 2>/dev/null); if echo \"$FILE\" | grep -qE \"(api|routes|endpoints|schema).*\\.(py|ts)$\"; then SYNC_FILE=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/api-doc-sync.json\"; mkdir -p \"$(dirname \"$SYNC_FILE\")\"; echo \"{\\\"api_changed\\\":true,\\\"file\\\":\\\"$FILE\\\",\\\"at\\\":\\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\"}\" > \"$SYNC_FILE\"; echo \"{\\\"addToPrompt\\\": \\\"[DOC-SYNC] API file modified: $FILE. Consider updating OpenAPI/Swagger docs and README API section.\\\"}\"; fi; exit 0'",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

### 5. Skill Recommendations

#### A. SDLC Phase Skills (Context: Fork for Isolation)

```markdown
---
name: sdlc-implement
description: Implement a feature following SDLC guidelines. Use when user wants to code a feature that has completed design phase.
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(uv:*), Bash(bun:*), Bash(npm:*)
disable-model-invocation: true
---

# Implementation Phase Skill

Before implementing, verify:
1. Design document exists at `docs/design/$ARGUMENTS.md`
2. Test specifications are defined

Implementation steps:
1. Create/update test files first (TDD)
2. Run tests to verify they fail
3. Implement the feature code
4. Run tests until they pass
5. Run linters and type checks
6. Update CHANGELOG.md

## Quality Checklist
- [ ] Tests written first
- [ ] All tests passing
- [ ] No lint errors
- [ ] No type errors
- [ ] CHANGELOG updated
```

#### B. Code Review Skill

```markdown
---
name: review-pr
description: Perform comprehensive code review on a pull request
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob, Bash(gh:*), Bash(git diff:*)
---

# PR Review Skill

Review the PR at $ARGUMENTS with focus on:

## Security
- Authentication/authorization issues
- Input validation
- SQL injection, XSS vulnerabilities
- Secrets in code

## Code Quality
- SOLID principles
- Error handling
- Code duplication
- Naming conventions

## Testing
- Test coverage
- Edge cases
- Integration tests

## Performance
- N+1 queries
- Memory leaks
- Unnecessary computations

Provide feedback using inline comments via `gh pr comment`.
```

#### C. Test Runner Skill (Enhanced)

```markdown
---
name: run-tests
description: Run tests with coverage and report results. Use when implementing features or fixing bugs.
allowed-tools: Bash(pytest:*), Bash(uv run pytest:*), Bash(bun test:*), Read
---

# Test Runner

Run tests for the module related to $ARGUMENTS:

## Backend (Python)
```bash
cd backend && uv run pytest -x -v --tb=short -k "$ARGUMENTS" --cov=app --cov-report=term-missing
```

## Frontend (TypeScript)
```bash
cd frontend && bun test --coverage "$ARGUMENTS"
```

Report:
1. Number of tests passed/failed
2. Coverage percentage
3. Uncovered lines (if any)
4. Recommendations for additional tests
```

### 6. GitHub Actions Integration

#### Automated PR Review Workflow

```yaml
name: Claude PR Review
on:
  pull_request:
    types: [opened, synchronize, ready_for_review]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      id-token: write
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0

      - name: Run Claude Code Review
        uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Review this PR comprehensively:
            - Check for security issues
            - Verify test coverage
            - Ensure code follows project conventions in CLAUDE.md
            - Validate documentation updates
          claude_args: |
            --max-turns 10
            --allowedTools "Read,Grep,Glob,Bash(gh pr diff:*),Bash(gh pr view:*)"
```

#### CI Failure Auto-Fix Workflow

```yaml
name: Auto Fix CI Failures
on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

permissions:
  contents: write
  pull-requests: write
  actions: read

jobs:
  auto-fix:
    if: github.event.workflow_run.conclusion == 'failure'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          ref: ${{ github.event.workflow_run.head_branch }}
          fetch-depth: 0

      - name: Fix CI Failures with Claude
        uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Analyze and fix the CI failure:
            1. Read the error logs
            2. Identify the root cause
            3. Implement the fix
            4. Run tests to verify
            5. Commit the fix
          claude_args: |
            --allowedTools "Read,Edit,Write,Bash(uv:*),Bash(bun:*),Bash(git:*)"
```

### 7. Headless Mode / SDK Usage

For CI/CD integration and scripting:

```bash
# Basic headless execution
claude -p "Review the staged changes for security issues" \
  --output-format json \
  --allowedTools "Read,Grep,Glob"

# With structured output
claude -p "Extract all API endpoints from the codebase" \
  --output-format json \
  --json-schema '{
    "type": "object",
    "properties": {
      "endpoints": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "method": {"type": "string"},
            "path": {"type": "string"},
            "handler": {"type": "string"}
          }
        }
      }
    }
  }'

# Continue conversation
session_id=$(claude -p "Start code review" --output-format json | jq -r '.session_id')
claude -p "Now check for security issues" --resume "$session_id"
```

---

## Recommendation

### Priority 1: Implement Stop Hook for Quality Gates (High Impact)

Add a Stop hook that verifies task completion criteria:
- Tests passing for quality phase
- Lint/type errors resolved
- Documentation sync completed

**Configuration:**
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Before stopping, verify: 1) All tests pass, 2) No lint errors, 3) Documentation is synced. If any fail, explain what needs to be fixed.",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

### Priority 2: Add SubagentStop Hook for Research Aggregation

Track and aggregate results from parallel research agents:

```json
{
  "hooks": {
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'INPUT=$(cat); RESULTS_FILE=\"${CLAUDE_PROJECT_ROOT:-.}/.claude/research-results.json\"; mkdir -p \"$(dirname \"$RESULTS_FILE\")\"; AGENT=$(echo \"$INPUT\" | jq -r \".subagent_type // \\\"unknown\\\"\"); jq \".agents += [{\\\"name\\\":\\\"$AGENT\\\",\\\"completed_at\\\":\\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\"}]\" \"$RESULTS_FILE\" > \"${RESULTS_FILE}.tmp\" 2>/dev/null && mv \"${RESULTS_FILE}.tmp\" \"$RESULTS_FILE\" || echo \"{\\\"agents\\\":[{\\\"name\\\":\\\"$AGENT\\\",\\\"completed_at\\\":\\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\"}]}\" > \"$RESULTS_FILE\"; exit 0'",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

### Priority 3: Create Reusable SDLC Skills

Convert the current command-based workflows to proper skills with:
- SKILL.md files with frontmatter
- `context: fork` for isolated execution
- `disable-model-invocation: true` for manual-only skills
- Supporting files for templates and examples

### Priority 4: GitHub Actions Integration

Implement the PR review and CI auto-fix workflows for automated quality assurance.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Hook timeout causing UX issues | Medium | Medium | Set appropriate timeouts (5-15s for quick checks, 120s for tests) |
| False positives blocking valid operations | Medium | High | Use specific matchers, add bypass mechanisms |
| State file corruption | Low | Medium | Use atomic writes with tmp files, add validation |
| CI costs from Claude API usage | Medium | Medium | Set `--max-turns` limits, use Sonnet for reviews |

---

## Next Steps

1. **Implement Stop hook** - Add task verification before Claude stops
2. **Add SubagentStop tracking** - Aggregate parallel agent results
3. **Create SDLC phase skills** - Convert commands to skills with proper structure
4. **Set up GitHub Actions** - PR review and CI auto-fix workflows
5. **Add session persistence** - Checkpoint system for crash recovery
6. **Test hook configurations** - Validate in safe environment before production

---

## References

- [Claude Code Hooks Documentation](https://code.claude.com/docs/en/hooks)
- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference)
- [Claude Code Headless/SDK Mode](https://code.claude.com/docs/en/headless)
- [Claude Code GitHub Actions](https://code.claude.com/docs/en/github-actions)
- [Anthropic Engineering Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [claude-code-action Repository](https://github.com/anthropics/claude-code-action)
- [Community Tutorial: Hooks for Quality Checks](https://www.letanure.dev/blog/2025-08-06--claude-code-part-8-hooks-automated-quality-checks)
- [Community Tutorial: Complete Workflows](https://www.letanure.dev/blog/2025-08-07--claude-code-part-9-complete-development-workflows)

---

## Appendix A: Complete Hook Configuration Template

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Session started. Active workflows available: /sdlc-orchestration"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "# Feature detection and SDLC enforcement",
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
            "command": "# Block .env edits, lock files, existing migrations",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "# Block dangerous commands, enforce pre-commit checks",
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
            "command": "# Auto-format, lint, type-check, track doc sync",
            "timeout": 30
          }
        ]
      },
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "# Track agent completion, update state",
            "timeout": 5
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "# Aggregate research results",
            "timeout": 5
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Verify task completion before stopping",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

## Appendix B: Skill Directory Structure

```
.claude/
├── settings.json
├── skills/
│   ├── sdlc-implement/
│   │   ├── SKILL.md
│   │   ├── templates/
│   │   │   └── implementation-checklist.md
│   │   └── examples/
│   │       └── feature-example.md
│   ├── review-pr/
│   │   ├── SKILL.md
│   │   └── checklist.md
│   ├── run-tests/
│   │   └── SKILL.md
│   └── gen-migration/
│       └── SKILL.md
├── plugins/
│   └── sdlc-orchestration/
│       ├── hooks/
│       │   └── hooks.json
│       ├── skills/
│       │   └── sdlc-orchestrator/
│       │       └── SKILL.md
│       ├── agents/
│       │   └── *.md
│       └── commands/
│           └── *.md
└── checkpoints/
    └── session-*.json
```
