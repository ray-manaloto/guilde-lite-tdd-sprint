#!/bin/bash
# Log hook failures to telemetry file
# Usage: log-hook-failure.sh <hook_name> <error_message>

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
LOG_DIR="${ROOT_DIR}/.run/logs"
TELEMETRY_FILE="${LOG_DIR}/telemetry.jsonl"

mkdir -p "${LOG_DIR}"

hook_name="${1:-unknown}"
error_message="${2:-unknown error}"
timestamp="$(date -Iseconds)"

# Log to telemetry file
echo "{\"timestamp\":\"${timestamp}\",\"event\":\"hook_failure\",\"hook\":\"${hook_name}\",\"error\":\"${error_message}\"}" >> "${TELEMETRY_FILE}"

# Also log to stderr for Claude Code to see
echo "[HookTelemetry] ${hook_name} failed: ${error_message}" >&2
