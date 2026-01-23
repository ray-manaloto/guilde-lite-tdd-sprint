#!/bin/bash
# Session start hook - loads previous context on new session

SESSIONS_DIR="${HOME}/.claude/sessions"
TODAY=$(date '+%Y-%m-%d')
SESSION_FILE="${SESSIONS_DIR}/${TODAY}-session.tmp"

mkdir -p "$SESSIONS_DIR"

# If today's session file exists, show summary
if [ -f "$SESSION_FILE" ]; then
  echo "[SessionStart] Found existing session: $SESSION_FILE" >&2
  echo "[SessionStart] Review with: cat $SESSION_FILE" >&2
fi

# Create/update session start time
if [ ! -f "$SESSION_FILE" ]; then
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
  echo "[SessionStart] Created session file: $SESSION_FILE" >&2
fi
