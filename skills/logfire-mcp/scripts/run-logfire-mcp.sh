#!/usr/bin/env bash
set -euo pipefail

if ! command -v uvx >/dev/null 2>&1; then
  echo "uvx is required. Install uv first: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

if [[ -z "${LOGFIRE_READ_TOKEN:-}" ]]; then
  echo "LOGFIRE_READ_TOKEN is not set." >&2
  echo "Export LOGFIRE_READ_TOKEN or set it in a .env file for the working directory." >&2
  exit 1
fi

args=()
if [[ -n "${LOGFIRE_BASE_URL:-}" ]]; then
  args+=(--base-url="${LOGFIRE_BASE_URL}")
fi

exec uvx logfire-mcp@latest --read-token="${LOGFIRE_READ_TOKEN}" "${args[@]}" "$@"
