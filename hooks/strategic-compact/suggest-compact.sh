#!/bin/bash
# Strategic compact suggestion hook
# Suggests manual compaction at logical intervals after edits

# Track edit count in temp file
COUNTER_FILE="/tmp/claude-edit-counter-$$"
EDIT_THRESHOLD=10

# Initialize or increment counter
if [ -f "$COUNTER_FILE" ]; then
  count=$(cat "$COUNTER_FILE")
  count=$((count + 1))
else
  count=1
fi

echo "$count" > "$COUNTER_FILE"

# Suggest compaction every N edits
if [ $((count % EDIT_THRESHOLD)) -eq 0 ]; then
  echo "[StrategicCompact] $count edits in session - consider /compact if context is growing" >&2
fi

# Pass through stdin
cat
