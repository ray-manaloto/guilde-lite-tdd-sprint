#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing .env at ${ENV_FILE}" >&2
  exit 1
fi

if command -v rg >/dev/null 2>&1; then
  grep_cmd=(rg -q)
else
  grep_cmd=(grep -q)
fi

if "${grep_cmd[@]}" '^LOGFIRE_TOKEN=' "${ENV_FILE}"; then
  echo "LOGFIRE_TOKEN is set in .env."
else
  echo "LOGFIRE_TOKEN is missing in .env."
fi

if "${grep_cmd[@]}" '^LOGFIRE_SEND_TO_LOGFIRE=' "${ENV_FILE}"; then
  echo "LOGFIRE_SEND_TO_LOGFIRE is set in .env."
else
  echo "LOGFIRE_SEND_TO_LOGFIRE is not set; defaults apply."
fi

echo "Note: logfire-mcp uses LOGFIRE_READ_TOKEN (not LOGFIRE_TOKEN)."
