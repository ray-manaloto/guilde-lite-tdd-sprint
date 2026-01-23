#!/bin/bash
# Claude Code CLI Health Check Script
# Validates Claude Code setup and reports issues
# Exit 0 if healthy, exit 1 if issues found

set -eo pipefail

PROJECT_ROOT="${CLAUDE_PROJECT_ROOT:-$(pwd)}"
HEALTH_FILE="${PROJECT_ROOT}/.claude/health-status.json"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Initialize health status
ISSUES=()
WARNINGS=()

# Ensure .claude directory exists
mkdir -p "${PROJECT_ROOT}/.claude"

# Check 1: Verify .claude/settings.json exists and is valid JSON
check_settings() {
    local settings_file="${PROJECT_ROOT}/.claude/settings.json"
    if [ ! -f "$settings_file" ]; then
        ISSUES+=("settings.json not found")
        return
    fi

    if ! jq empty "$settings_file" 2>/dev/null; then
        ISSUES+=("settings.json is invalid JSON")
        return
    fi

    # Check for required sections
    if ! jq -e '.permissions' "$settings_file" >/dev/null 2>&1; then
        WARNINGS+=("settings.json missing permissions section")
    fi
}

# Check 2: Verify skill scripts have execute permissions
check_skill_permissions() {
    local skills_dir="${PROJECT_ROOT}/.claude/skills"
    if [ -d "$skills_dir" ]; then
        while IFS= read -r -d '' script; do
            if [ ! -x "$script" ]; then
                local rel_path="${script#$PROJECT_ROOT/}"
                ISSUES+=("Script not executable: $rel_path")
            fi
        done < <(find "$skills_dir" -name "*.sh" -print0 2>/dev/null)
    fi
}

# Check 3: Verify hooks files are valid JSON
check_hooks() {
    local hooks_dir="${PROJECT_ROOT}/.claude/plugins"
    if [ -d "$hooks_dir" ]; then
        while IFS= read -r -d '' hooks_file; do
            if ! jq empty "$hooks_file" 2>/dev/null; then
                local rel_path="${hooks_file#$PROJECT_ROOT/}"
                ISSUES+=("Invalid hooks JSON: $rel_path")
            fi
        done < <(find "$hooks_dir" -name "hooks*.json" -print0 2>/dev/null)
    fi
}

# Check 4: Verify required environment variables for self-healing
check_env_vars() {
    local env_file="${PROJECT_ROOT}/backend/.env"
    if [ -f "$env_file" ]; then
        if ! grep -q "^GITHUB_TOKEN=" "$env_file" || grep -q "^GITHUB_TOKEN=$" "$env_file"; then
            WARNINGS+=("GITHUB_TOKEN not set in backend/.env (self-healing disabled)")
        fi
    fi
}

# Check 5: Verify CLAUDE.md exists
check_claude_md() {
    if [ ! -f "${PROJECT_ROOT}/CLAUDE.md" ]; then
        WARNINGS+=("CLAUDE.md not found in project root")
    fi
}

# Check 6: Check for orphaned planning files without active task
check_planning_files() {
    local plan_file="${PROJECT_ROOT}/task_plan.md"
    if [ -f "$plan_file" ]; then
        # Check if any phases are in_progress
        if grep -qF "IN PROGRESS" "$plan_file" 2>/dev/null; then
            WARNINGS+=("task_plan.md has phases in progress - consider completing or cleaning up")
        fi
    fi
}

# Run all checks
check_settings
check_skill_permissions
check_hooks
check_env_vars
check_claude_md
check_planning_files

# Generate health status JSON
if [ ${#ISSUES[@]} -gt 0 ]; then
    ISSUES_JSON=$(printf '%s\n' "${ISSUES[@]}" | jq -R . | jq -s .)
else
    ISSUES_JSON="[]"
fi

if [ ${#WARNINGS[@]} -gt 0 ]; then
    WARNINGS_JSON=$(printf '%s\n' "${WARNINGS[@]}" | jq -R . | jq -s .)
else
    WARNINGS_JSON="[]"
fi

cat > "$HEALTH_FILE" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "healthy": $([ ${#ISSUES[@]} -eq 0 ] && echo "true" || echo "false"),
  "issues": $ISSUES_JSON,
  "warnings": $WARNINGS_JSON,
  "checks_run": 6
}
EOF

# Output summary
if [ ${#ISSUES[@]} -gt 0 ]; then
    echo "[CLAUDE CODE HEALTH] Issues found:"
    for issue in "${ISSUES[@]}"; do
        echo "  - $issue"
    done
    exit 1
fi

if [ ${#WARNINGS[@]} -gt 0 ]; then
    echo "[CLAUDE CODE HEALTH] Warnings:"
    for warning in "${WARNINGS[@]}"; do
        echo "  - $warning"
    done
fi

echo "[CLAUDE CODE HEALTH] All checks passed"
exit 0
