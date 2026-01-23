#!/usr/bin/env bash
#
# Self-Healing Restart Automation Script
#
# This script handles service restart logic for the self-healing infrastructure.
# It can be triggered manually or by the feedback loop after a fix is merged.
#
# Usage:
#   ./scripts/self-heal-restart.sh [options]
#
# Options:
#   --check-only     Only check if restart is needed, don't restart
#   --force          Force restart even if not needed
#   --sync           Git pull before checking
#   --service NAME   Only check/restart specific service (backend|frontend|all)
#   --verbose        Enable verbose output
#   --dry-run        Show what would be done without doing it
#
# Exit codes:
#   0 - Success (no restart needed or restart completed)
#   1 - Restart needed (when --check-only)
#   2 - Restart failed
#   3 - Configuration error
#
set -euo pipefail

# Configuration
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEVCTL="${ROOT_DIR}/scripts/devctl.sh"
BACKEND_DIR="${ROOT_DIR}/backend"
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/api/v1/health/ready}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-30}"
MAX_RESTART_ATTEMPTS="${MAX_RESTART_ATTEMPTS:-3}"

# State tracking
STATE_DIR="${ROOT_DIR}/.run/self-heal"
LAST_ENV_HASH="${STATE_DIR}/last-env-hash"
LAST_MIGRATION_HEAD="${STATE_DIR}/last-migration-head"
RESTART_LOG="${STATE_DIR}/restart.log"

# Options
CHECK_ONLY=false
FORCE_RESTART=false
SYNC_FIRST=false
TARGET_SERVICE="all"
VERBOSE=false
DRY_RUN=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    local level="$1"
    shift
    local msg="$*"
    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"

    case "$level" in
        INFO)  echo -e "${BLUE}[INFO]${NC} ${msg}" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC} ${msg}" ;;
        ERROR) echo -e "${RED}[ERROR]${NC} ${msg}" ;;
        OK)    echo -e "${GREEN}[OK]${NC} ${msg}" ;;
        DEBUG)
            if [[ "$VERBOSE" == "true" ]]; then
                echo -e "[DEBUG] ${msg}"
            fi
            ;;
    esac

    # Also log to file
    echo "[${timestamp}] [${level}] ${msg}" >> "${RESTART_LOG}" 2>/dev/null || true
}

usage() {
    head -30 "$0" | tail -25
    exit 0
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --check-only)
                CHECK_ONLY=true
                shift
                ;;
            --force)
                FORCE_RESTART=true
                shift
                ;;
            --sync)
                SYNC_FIRST=true
                shift
                ;;
            --service)
                TARGET_SERVICE="$2"
                shift 2
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                usage
                ;;
            *)
                log ERROR "Unknown option: $1"
                usage
                ;;
        esac
    done
}

init_state_dir() {
    mkdir -p "${STATE_DIR}"
}

# Check if .env file has changed since last restart
check_env_changed() {
    local current_hash

    if [[ ! -f "${ROOT_DIR}/.env" ]]; then
        log DEBUG "No .env file found"
        return 1
    fi

    current_hash="$(md5sum "${ROOT_DIR}/.env" 2>/dev/null | cut -d' ' -f1 || md5 -q "${ROOT_DIR}/.env" 2>/dev/null)"

    if [[ ! -f "${LAST_ENV_HASH}" ]]; then
        echo "${current_hash}" > "${LAST_ENV_HASH}"
        log DEBUG "First run, storing env hash"
        return 1
    fi

    local last_hash
    last_hash="$(cat "${LAST_ENV_HASH}")"

    if [[ "${current_hash}" != "${last_hash}" ]]; then
        log INFO ".env file has changed"
        return 0
    fi

    log DEBUG ".env unchanged"
    return 1
}

# Check if there are pending migrations
check_migrations_pending() {
    local current_head

    if ! command -v uv >/dev/null 2>&1; then
        log WARN "uv not found, skipping migration check"
        return 1
    fi

    current_head="$(cd "${BACKEND_DIR}" && uv run alembic heads 2>/dev/null | head -1 || echo "unknown")"

    if [[ ! -f "${LAST_MIGRATION_HEAD}" ]]; then
        echo "${current_head}" > "${LAST_MIGRATION_HEAD}"
        log DEBUG "First run, storing migration head"
        return 1
    fi

    local last_head
    last_head="$(cat "${LAST_MIGRATION_HEAD}")"

    # Check if current is at head
    local alembic_current
    alembic_current="$(cd "${BACKEND_DIR}" && uv run alembic current 2>/dev/null || echo "")"

    if [[ "${alembic_current}" != *"(head)"* ]]; then
        log INFO "Migrations pending"
        return 0
    fi

    if [[ "${current_head}" != "${last_head}" ]]; then
        log INFO "New migrations available"
        return 0
    fi

    log DEBUG "Migrations up to date"
    return 1
}

# Check if backend health endpoint is failing
check_health_failing() {
    local response
    local status_code

    log DEBUG "Checking health at ${HEALTH_URL}"

    response="$(curl -s -w "\n%{http_code}" --connect-timeout 5 "${HEALTH_URL}" 2>/dev/null || echo -e "\n000")"
    status_code="$(echo "${response}" | tail -1)"

    if [[ "${status_code}" == "200" ]]; then
        log DEBUG "Health check passed"
        return 1
    elif [[ "${status_code}" == "503" ]]; then
        log WARN "Service not ready (503)"
        return 0
    elif [[ "${status_code}" == "000" ]]; then
        log WARN "Service unreachable"
        return 0
    else
        log WARN "Health check returned ${status_code}"
        return 0
    fi
}

# Check if backend process is running
check_process_running() {
    local match="uvicorn app.main:app"

    if pgrep -f "${match}" >/dev/null 2>&1; then
        log DEBUG "Backend process is running"
        return 0
    else
        log WARN "Backend process not found"
        return 1
    fi
}

# Determine if restart is needed
determine_restart_needed() {
    local needs_restart=false
    local reasons=()

    if [[ "${FORCE_RESTART}" == "true" ]]; then
        log INFO "Force restart requested"
        echo "force_requested"
        return 0
    fi

    # Check various conditions
    if check_env_changed; then
        needs_restart=true
        reasons+=("env_changed")
    fi

    if check_migrations_pending; then
        needs_restart=true
        reasons+=("migrations_pending")
    fi

    if check_health_failing; then
        needs_restart=true
        reasons+=("health_failing")
    fi

    if ! check_process_running; then
        needs_restart=true
        reasons+=("process_not_running")
    fi

    if [[ "${needs_restart}" == "true" ]]; then
        echo "${reasons[*]}"
        return 0
    fi

    return 1
}

# Run migrations
run_migrations() {
    log INFO "Running database migrations..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        log INFO "[DRY-RUN] Would run: alembic upgrade head"
        return 0
    fi

    if ! (cd "${BACKEND_DIR}" && uv run alembic upgrade head); then
        log ERROR "Migration failed"
        return 1
    fi

    # Update state
    local current_head
    current_head="$(cd "${BACKEND_DIR}" && uv run alembic heads 2>/dev/null | head -1 || echo "unknown")"
    echo "${current_head}" > "${LAST_MIGRATION_HEAD}"

    log OK "Migrations completed"
    return 0
}

# Restart backend service
restart_backend() {
    log INFO "Restarting backend service..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        log INFO "[DRY-RUN] Would run: devctl restart backend"
        return 0
    fi

    if [[ ! -x "${DEVCTL}" ]]; then
        log ERROR "devctl not found or not executable"
        return 1
    fi

    # Stop existing service
    "${DEVCTL}" stop backend 2>/dev/null || true
    sleep 2

    # Start service
    if ! "${DEVCTL}" start backend; then
        log ERROR "Failed to start backend"
        return 1
    fi

    # Wait for health
    log INFO "Waiting for backend to become healthy..."
    local attempts=0
    while [[ $attempts -lt $HEALTH_TIMEOUT ]]; do
        if ! check_health_failing; then
            log OK "Backend is healthy"

            # Update env hash
            if [[ -f "${ROOT_DIR}/.env" ]]; then
                md5sum "${ROOT_DIR}/.env" 2>/dev/null | cut -d' ' -f1 > "${LAST_ENV_HASH}" || \
                md5 -q "${ROOT_DIR}/.env" > "${LAST_ENV_HASH}" 2>/dev/null || true
            fi

            return 0
        fi
        sleep 1
        ((attempts++))
    done

    log ERROR "Backend failed to become healthy within ${HEALTH_TIMEOUT}s"
    return 1
}

# Restart frontend service
restart_frontend() {
    log INFO "Restarting frontend service..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        log INFO "[DRY-RUN] Would run: devctl restart frontend"
        return 0
    fi

    if ! "${DEVCTL}" restart frontend; then
        log ERROR "Failed to restart frontend"
        return 1
    fi

    log OK "Frontend restarted"
    return 0
}

# Git sync
git_sync() {
    log INFO "Syncing from remote..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        log INFO "[DRY-RUN] Would run: git pull --rebase"
        return 0
    fi

    cd "${ROOT_DIR}"

    # Check for uncommitted changes
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        log WARN "Uncommitted changes detected, stashing..."
        git stash push -m "self-heal-restart auto-stash $(date +%Y%m%d%H%M%S)"
    fi

    if ! git pull --rebase; then
        log ERROR "Git pull failed"
        return 1
    fi

    log OK "Git sync completed"
    return 0
}

# Main execution
main() {
    parse_args "$@"
    init_state_dir

    log INFO "Self-Healing Restart Check"
    log INFO "=========================="
    log DEBUG "ROOT_DIR: ${ROOT_DIR}"
    log DEBUG "TARGET_SERVICE: ${TARGET_SERVICE}"
    log DEBUG "CHECK_ONLY: ${CHECK_ONLY}"
    log DEBUG "FORCE_RESTART: ${FORCE_RESTART}"

    # Git sync if requested
    if [[ "${SYNC_FIRST}" == "true" ]]; then
        if ! git_sync; then
            exit 3
        fi
    fi

    # Determine if restart is needed
    local restart_reasons
    if restart_reasons="$(determine_restart_needed)"; then
        log INFO "Restart needed: ${restart_reasons}"

        if [[ "${CHECK_ONLY}" == "true" ]]; then
            log INFO "Check-only mode, exiting with code 1"
            exit 1
        fi

        # Handle migrations if pending
        if [[ "${restart_reasons}" == *"migrations_pending"* ]]; then
            if ! run_migrations; then
                exit 2
            fi
        fi

        # Restart services
        local exit_code=0

        if [[ "${TARGET_SERVICE}" == "all" || "${TARGET_SERVICE}" == "backend" ]]; then
            if ! restart_backend; then
                exit_code=2
            fi
        fi

        if [[ "${TARGET_SERVICE}" == "all" || "${TARGET_SERVICE}" == "frontend" ]]; then
            if ! restart_frontend; then
                exit_code=2
            fi
        fi

        if [[ $exit_code -eq 0 ]]; then
            log OK "Restart completed successfully"
        fi

        exit $exit_code
    else
        log OK "No restart needed"
        exit 0
    fi
}

main "$@"
