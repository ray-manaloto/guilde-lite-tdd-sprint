#!/bin/bash
# Claude Code CLI Self-Healing Script
# Automatically fixes common issues found by health-check.sh
# Run after health-check.sh reports issues

set -euo pipefail

PROJECT_ROOT="${CLAUDE_PROJECT_ROOT:-$(pwd)}"
FIXES_APPLIED=0

echo "[SELF-HEAL] Starting Claude Code CLI self-healing..."

# Fix 1: Make all skill scripts executable
fix_script_permissions() {
    local skills_dir="${PROJECT_ROOT}/.claude/skills"
    if [ -d "$skills_dir" ]; then
        while IFS= read -r -d '' script; do
            if [ ! -x "$script" ]; then
                chmod +x "$script"
                echo "[SELF-HEAL] Fixed permissions: ${script#$PROJECT_ROOT/}"
                ((FIXES_APPLIED++))
            fi
        done < <(find "$skills_dir" -name "*.sh" -print0 2>/dev/null)
    fi

    # Also fix .claude/scripts
    local scripts_dir="${PROJECT_ROOT}/.claude/scripts"
    if [ -d "$scripts_dir" ]; then
        while IFS= read -r -d '' script; do
            if [ ! -x "$script" ]; then
                chmod +x "$script"
                echo "[SELF-HEAL] Fixed permissions: ${script#$PROJECT_ROOT/}"
                ((FIXES_APPLIED++))
            fi
        done < <(find "$scripts_dir" -name "*.sh" -print0 2>/dev/null)
    fi
}

# Fix 2: Create missing .claude directory structure
fix_directory_structure() {
    local dirs=(
        "${PROJECT_ROOT}/.claude"
        "${PROJECT_ROOT}/.claude/scripts"
        "${PROJECT_ROOT}/.claude/skills"
    )

    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            echo "[SELF-HEAL] Created directory: ${dir#$PROJECT_ROOT/}"
            ((FIXES_APPLIED++))
        fi
    done
}

# Fix 3: Create default settings.json if missing
fix_settings() {
    local settings_file="${PROJECT_ROOT}/.claude/settings.json"
    if [ ! -f "$settings_file" ]; then
        cat > "$settings_file" <<'EOF'
{
  "permissions": {
    "allow": []
  },
  "hooks": {}
}
EOF
        echo "[SELF-HEAL] Created default settings.json"
        ((FIXES_APPLIED++))
    fi
}

# Fix 4: Clean up orphaned planning files
fix_planning_cleanup() {
    local plan_file="${PROJECT_ROOT}/task_plan.md"
    local findings_file="${PROJECT_ROOT}/findings.md"
    local progress_file="${PROJECT_ROOT}/progress.md"

    # Only clean up if all planning files exist and task is complete
    if [ -f "$plan_file" ]; then
        # Check if all phases are complete
        local total_phases=$(grep -c "### Phase" "$plan_file" 2>/dev/null || echo "0")
        local complete_phases=$(grep -c "\[COMPLETE\]" "$plan_file" 2>/dev/null || echo "0")

        if [ "$total_phases" -gt 0 ] && [ "$complete_phases" -eq "$total_phases" ]; then
            # Archive to .claude/archives
            local archive_dir="${PROJECT_ROOT}/.claude/archives"
            local archive_date=$(date +%Y%m%d-%H%M%S)
            mkdir -p "$archive_dir"

            [ -f "$plan_file" ] && mv "$plan_file" "${archive_dir}/task_plan-${archive_date}.md"
            [ -f "$findings_file" ] && mv "$findings_file" "${archive_dir}/findings-${archive_date}.md"
            [ -f "$progress_file" ] && mv "$progress_file" "${archive_dir}/progress-${archive_date}.md"

            echo "[SELF-HEAL] Archived completed planning files to .claude/archives/"
            ((FIXES_APPLIED++))
        fi
    fi
}

# Fix 5: Validate and repair JSON files
fix_json_files() {
    local settings_file="${PROJECT_ROOT}/.claude/settings.json"

    if [ -f "$settings_file" ]; then
        if ! jq empty "$settings_file" 2>/dev/null; then
            # Backup corrupted file
            cp "$settings_file" "${settings_file}.corrupted.$(date +%s)"

            # Create minimal valid settings
            cat > "$settings_file" <<'EOF'
{
  "permissions": {
    "allow": []
  },
  "hooks": {}
}
EOF
            echo "[SELF-HEAL] Repaired corrupted settings.json (backup saved)"
            ((FIXES_APPLIED++))
        fi
    fi
}

# Run all fixes
fix_directory_structure
fix_settings
fix_script_permissions
fix_json_files
# fix_planning_cleanup  # Commented out - requires explicit user consent

# Summary
if [ $FIXES_APPLIED -gt 0 ]; then
    echo "[SELF-HEAL] Applied $FIXES_APPLIED fixes"
else
    echo "[SELF-HEAL] No fixes needed"
fi

# Run health check to verify
echo ""
echo "[SELF-HEAL] Running health check to verify..."
"${PROJECT_ROOT}/.claude/scripts/health-check.sh" || true
