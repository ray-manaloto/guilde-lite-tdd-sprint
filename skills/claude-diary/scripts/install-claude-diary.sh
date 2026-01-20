#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
SOURCE_DIR="${CLAUDE_DIARY_SOURCE:-$ROOT_DIR/tools/claude-diary}"
SETTINGS_FILE="${CLAUDE_SETTINGS_FILE:-$ROOT_DIR/.claude/settings.local.json}"

apply=0
write_settings=0

for arg in "$@"; do
  case "${arg}" in
    --apply)
      apply=1
      ;;
    --write-settings)
      write_settings=1
      ;;
  esac
done

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "Claude Diary source not found: ${SOURCE_DIR}" >&2
  echo "Clone it and set CLAUDE_DIARY_SOURCE, e.g.:" >&2
  echo "  git clone https://github.com/rlancemartin/claude-diary ${ROOT_DIR}/tools/claude-diary" >&2
  exit 1
fi

if [[ "${apply}" -ne 1 ]]; then
  echo "Dry run. To install commands/hooks, rerun with --apply." >&2
  echo "To also write settings, add --write-settings." >&2
  exit 0
fi

mkdir -p "${CLAUDE_HOME}/commands" "${CLAUDE_HOME}/hooks"
cp "${SOURCE_DIR}/commands/"*.md "${CLAUDE_HOME}/commands/"
cp "${SOURCE_DIR}/hooks/pre-compact.sh" "${CLAUDE_HOME}/hooks/pre-compact.sh"
chmod +x "${CLAUDE_HOME}/hooks/pre-compact.sh"

if [[ "${write_settings}" -eq 1 ]]; then
  mkdir -p "$(dirname "${SETTINGS_FILE}")"
  cat > "${SETTINGS_FILE}" <<'JSON'
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "auto",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/pre-compact.sh"
          }
        ]
      }
    ]
  }
}
JSON
fi

echo "Claude Diary commands/hooks installed."
