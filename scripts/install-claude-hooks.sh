#!/usr/bin/env bash
set -euo pipefail

SOURCE_FILE="$(cd "$(dirname "$0")" && pwd)/claude-hooks-global.json"
TARGET_FILE="$HOME/.claude/settings.json"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required to install global hooks." >&2
  exit 1
fi

mkdir -p "$(dirname "$TARGET_FILE")"

if [[ ! -f "$TARGET_FILE" ]]; then
  jq -s '.[0] * .[1]' /dev/null "$SOURCE_FILE" > "$TARGET_FILE"
  echo "Created $TARGET_FILE"
  exit 0
fi

jq -s '.[0] * .[1]' "$TARGET_FILE" "$SOURCE_FILE" > "$TARGET_FILE.tmp"
mv "$TARGET_FILE.tmp" "$TARGET_FILE"

echo "Updated $TARGET_FILE with global hooks."
