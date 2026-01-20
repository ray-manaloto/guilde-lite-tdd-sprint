#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

if [[ -z "${LOGFIRE_READ_TOKEN:-}" && -f "${ENV_FILE}" ]]; then
  if command -v rg >/dev/null 2>&1; then
    token_line="$(rg -m 1 '^LOGFIRE_READ_TOKEN=' "${ENV_FILE}" || true)"
  else
    token_line="$(grep -m 1 '^LOGFIRE_READ_TOKEN=' "${ENV_FILE}" || true)"
  fi
  if [[ -n "${token_line}" ]]; then
    token_value="${token_line#LOGFIRE_READ_TOKEN=}"
    token_value="${token_value%\"}"
    token_value="${token_value#\"}"
    token_value="${token_value%\'}"
    token_value="${token_value#\'}"
    export LOGFIRE_READ_TOKEN="${token_value}"
  fi
fi

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
