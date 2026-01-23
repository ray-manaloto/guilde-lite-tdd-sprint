#!/usr/bin/env bash
#
# Trigger Self-Heal Workflow via repository_dispatch
#
# This script sends a repository_dispatch event to GitHub to trigger
# the ai-self-heal.yml workflow. Use this for testing or manual triggering.
#
# Usage:
#   ./scripts/trigger-self-heal.sh --error "Error message" [options]
#
# Options:
#   --error MESSAGE    Error message to diagnose (required)
#   --file PATH        File where error occurred
#   --line NUMBER      Line number of error
#   --trace-id ID      Trace ID from observability system
#   --type TYPE        Event type: error-detected (default) or anomaly-detected
#   --dry-run          Show the request without sending
#
# Environment:
#   GITHUB_TOKEN       Required: Personal access token with repo scope
#   GITHUB_REPO        Required: Repository in format owner/repo
#
# Examples:
#   ./scripts/trigger-self-heal.sh --error "NullPointerException in UserService"
#   ./scripts/trigger-self-heal.sh --error "Import error" --file "app/main.py" --line 42
#
set -euo pipefail

# Configuration
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
GITHUB_REPO="${GITHUB_REPO:-}"
API_URL="https://api.github.com"

# Options
ERROR_MESSAGE=""
ERROR_FILE=""
ERROR_LINE=""
TRACE_ID=""
EVENT_TYPE="error-detected"
DRY_RUN=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    head -28 "$0" | tail -25
    exit 0
}

error() {
    echo -e "${RED}Error:${NC} $1" >&2
    exit 1
}

info() {
    echo -e "${GREEN}Info:${NC} $1"
}

warn() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --error)
                ERROR_MESSAGE="$2"
                shift 2
                ;;
            --file)
                ERROR_FILE="$2"
                shift 2
                ;;
            --line)
                ERROR_LINE="$2"
                shift 2
                ;;
            --trace-id)
                TRACE_ID="$2"
                shift 2
                ;;
            --type)
                EVENT_TYPE="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                usage
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done
}

validate_config() {
    # Try to load from .env if not set
    if [[ -z "${GITHUB_TOKEN}" ]] && [[ -f ".env" ]]; then
        GITHUB_TOKEN="$(grep '^GITHUB_TOKEN=' .env 2>/dev/null | cut -d'=' -f2- | tr -d '"' || true)"
    fi

    if [[ -z "${GITHUB_REPO}" ]] && [[ -f ".env" ]]; then
        GITHUB_REPO="$(grep '^GITHUB_REPO=' .env 2>/dev/null | cut -d'=' -f2- | tr -d '"' || true)"
    fi

    # Also try git remote
    if [[ -z "${GITHUB_REPO}" ]]; then
        local remote_url
        remote_url="$(git remote get-url origin 2>/dev/null || true)"
        if [[ -n "${remote_url}" ]]; then
            # Extract owner/repo from git URL
            GITHUB_REPO="$(echo "${remote_url}" | sed -E 's#.*[:/]([^/]+/[^/]+)(\.git)?$#\1#')"
        fi
    fi

    if [[ -z "${GITHUB_TOKEN}" ]]; then
        error "GITHUB_TOKEN not set. Set it in environment or .env file."
    fi

    if [[ -z "${GITHUB_REPO}" ]]; then
        error "GITHUB_REPO not set. Set it in environment, .env file, or ensure git remote is configured."
    fi

    if [[ -z "${ERROR_MESSAGE}" ]]; then
        error "--error MESSAGE is required"
    fi
}

build_payload() {
    local payload

    payload=$(cat <<EOF
{
  "event_type": "${EVENT_TYPE}",
  "client_payload": {
    "error_message": "${ERROR_MESSAGE}"
EOF
)

    if [[ -n "${ERROR_FILE}" ]]; then
        payload+=",
    \"file\": \"${ERROR_FILE}\""
    fi

    if [[ -n "${ERROR_LINE}" ]]; then
        payload+=",
    \"line\": \"${ERROR_LINE}\""
    fi

    if [[ -n "${TRACE_ID}" ]]; then
        payload+=",
    \"trace_id\": \"${TRACE_ID}\""
    fi

    payload+="
  }
}"

    echo "${payload}"
}

send_dispatch() {
    local payload="$1"
    local url="${API_URL}/repos/${GITHUB_REPO}/dispatches"

    info "Sending repository_dispatch to ${GITHUB_REPO}"
    info "Event type: ${EVENT_TYPE}"

    if [[ "${DRY_RUN}" == "true" ]]; then
        echo ""
        echo "=== DRY RUN - Request Details ==="
        echo "URL: ${url}"
        echo "Method: POST"
        echo "Headers:"
        echo "  Authorization: Bearer <GITHUB_TOKEN>"
        echo "  Accept: application/vnd.github+json"
        echo "  X-GitHub-Api-Version: 2022-11-28"
        echo ""
        echo "Payload:"
        echo "${payload}" | jq . 2>/dev/null || echo "${payload}"
        echo ""
        echo "=== END DRY RUN ==="
        return 0
    fi

    local response
    local http_code

    response=$(curl -s -w "\n%{http_code}" -X POST "${url}" \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        -H "Accept: application/vnd.github+json" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        -d "${payload}")

    http_code=$(echo "${response}" | tail -1)
    body=$(echo "${response}" | head -n -1)

    case "${http_code}" in
        204)
            info "Successfully triggered workflow!"
            info "Check status at: https://github.com/${GITHUB_REPO}/actions"
            ;;
        401)
            error "Authentication failed. Check your GITHUB_TOKEN."
            ;;
        403)
            error "Forbidden. Token may lack 'repo' scope or workflow is disabled."
            ;;
        404)
            error "Repository not found or you don't have access: ${GITHUB_REPO}"
            ;;
        422)
            error "Validation failed. Check event_type matches workflow trigger."
            ;;
        *)
            error "Unexpected response (HTTP ${http_code}): ${body}"
            ;;
    esac
}

main() {
    parse_args "$@"
    validate_config

    info "Triggering self-heal workflow"
    info "Repository: ${GITHUB_REPO}"
    info "Error: ${ERROR_MESSAGE}"
    [[ -n "${ERROR_FILE}" ]] && info "File: ${ERROR_FILE}"
    [[ -n "${ERROR_LINE}" ]] && info "Line: ${ERROR_LINE}"
    [[ -n "${TRACE_ID}" ]] && info "Trace ID: ${TRACE_ID}"
    echo ""

    local payload
    payload="$(build_payload)"

    send_dispatch "${payload}"
}

main "$@"
