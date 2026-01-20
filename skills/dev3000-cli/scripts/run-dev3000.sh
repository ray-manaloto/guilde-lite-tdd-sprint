#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
WORKDIR="${DEV3000_WORKDIR:-$ROOT_DIR}"

args=()

if [[ -n "${DEV3000_PORT:-}" ]]; then
  args+=(--port "${DEV3000_PORT}")
fi

if [[ -n "${DEV3000_MCP_PORT:-}" ]]; then
  args+=(--mcp-port "${DEV3000_MCP_PORT}")
fi

if [[ -n "${DEV3000_DISABLE_MCP_CONFIGS:-}" ]]; then
  args+=(--disable-mcp-configs "${DEV3000_DISABLE_MCP_CONFIGS}")
fi

if [[ -n "${DEV3000_BROWSER:-}" ]]; then
  args+=(--browser "${DEV3000_BROWSER}")
fi

if [[ "${DEV3000_SERVERS_ONLY:-}" == "1" || "${DEV3000_SERVERS_ONLY:-}" == "true" ]]; then
  args+=(--servers-only)
fi

if [[ "${DEV3000_HEADLESS:-}" == "1" || "${DEV3000_HEADLESS:-}" == "true" ]]; then
  args+=(--headless)
fi

cd "${WORKDIR}"

if command -v dev3000 >/dev/null 2>&1; then
  exec dev3000 "${args[@]}" "$@"
fi

if command -v pnpm >/dev/null 2>&1 && [[ -f package.json ]]; then
  exec pnpm dev3000 "${args[@]}" "$@"
fi

echo "dev3000 is not available. Install it with:" >&2
echo "  pnpm install -g dev3000" >&2
echo "or:" >&2
echo "  pnpm add -D dev3000" >&2
exit 1
