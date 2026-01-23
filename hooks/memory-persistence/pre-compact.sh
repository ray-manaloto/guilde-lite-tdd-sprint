#!/bin/bash
# Pre-compact hook - saves state before context compaction

SESSIONS_DIR="${HOME}/.claude/sessions"
TODAY=$(date '+%Y-%m-%d')
SESSION_FILE="${SESSIONS_DIR}/${TODAY}-session.tmp"

mkdir -p "$SESSIONS_DIR"

# Update session file with compaction notice
if [ -f "$SESSION_FILE" ]; then
  echo "" >> "$SESSION_FILE"
  echo "### Compaction at $(date '+%H:%M')" >> "$SESSION_FILE"
  echo "[PreCompact] Saved state before compaction" >&2
fi
