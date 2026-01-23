#!/bin/bash
# Session end hook - persists session state
# Runs when Claude session ends

SESSIONS_DIR="${HOME}/.claude/sessions"
TODAY=$(date '+%Y-%m-%d')
SESSION_FILE="${SESSIONS_DIR}/${TODAY}-session.tmp"

mkdir -p "$SESSIONS_DIR"

# Update or create session file
if [ -f "$SESSION_FILE" ]; then
  # Update Last Updated timestamp (macOS and Linux compatible)
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/\*\*Last Updated:\*\*.*/\*\*Last Updated:\*\* $(date '+%H:%M')/" "$SESSION_FILE" 2>/dev/null || true
  else
    sed -i "s/\*\*Last Updated:\*\*.*/\*\*Last Updated:\*\* $(date '+%H:%M')/" "$SESSION_FILE" 2>/dev/null || true
  fi
  echo "[SessionEnd] Updated session file: $SESSION_FILE" >&2
else
  # Create new session file
  cat > "$SESSION_FILE" << EOF
# Session: $(date '+%Y-%m-%d')
**Date:** $TODAY
**Started:** $(date '+%H:%M')
**Last Updated:** $(date '+%H:%M')

---

## Current State
[Session context goes here]

### Completed
- [ ]

### In Progress
- [ ]

### Notes for Next Session
-
EOF
  echo "[SessionEnd] Created session file: $SESSION_FILE" >&2
fi
