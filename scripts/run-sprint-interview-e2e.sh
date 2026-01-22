#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v bun >/dev/null 2>&1; then
  echo "bun is required to run Playwright E2E tests." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to wait for service readiness." >&2
  exit 1
fi

BACKEND_PORT="${BACKEND_PORT:-8000}"
AGENT_WEB_PORT="${AGENT_WEB_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
: "${AGENT_FS_ENABLED:=true}"
: "${AUTOCODE_ARTIFACTS_DIR:=/Users/rmanaloto/dev/tmp/guilde-lite-tdd-sprint-filesystem}"
: "${PHASE_RUNNER_MODE:=sync}"

export AGENT_FS_ENABLED
export AUTOCODE_ARTIFACTS_DIR
export PHASE_RUNNER_MODE

wait_for_url() {
  local url="$1"
  local timeout="${2:-120}"
  local start
  start="$(date +%s)"
  while true; do
    if curl --fail --silent --output /dev/null "$url"; then
      return 0
    fi
    if (( $(date +%s) - start >= timeout )); then
      echo "Timed out waiting for ${url}" >&2
      return 1
    fi
    sleep 1
  done
}

DEVCTL_MODE=background "${ROOT_DIR}/scripts/devctl.sh" stop frontend
DEVCTL_MODE=background "${ROOT_DIR}/scripts/devctl.sh" restart backend
DEVCTL_MODE=background "${ROOT_DIR}/scripts/devctl.sh" restart agent-web

wait_for_url "http://localhost:${BACKEND_PORT}/api/v1/health"
wait_for_url "http://localhost:${AGENT_WEB_PORT}/"

cd "${ROOT_DIR}/frontend"
bun run test:e2e -- sprint-interview-hello-world.spec.ts --project=chromium
