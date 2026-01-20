#!/usr/bin/env bash
set -euo pipefail

if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm is required to install dev3000. Install pnpm first." >&2
  exit 1
fi

mode="${DEV3000_INSTALL_MODE:-global}"

case "${mode}" in
  global)
    pnpm install -g dev3000
    ;;
  local|dev)
    pnpm add -D dev3000
    ;;
  *)
    echo "Unknown DEV3000_INSTALL_MODE: ${mode} (use global|local|dev)" >&2
    exit 1
    ;;
esac
