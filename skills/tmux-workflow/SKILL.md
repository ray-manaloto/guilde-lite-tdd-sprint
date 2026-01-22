---
name: tmux-workflow
description: Use tmux as a programmable terminal multiplexer for persistent sessions, parallel Claude Code instances, and background task management. Essential for long-running operations and multi-agent workflows.
---

# tmux Workflow for Claude Code

tmux enables persistent terminal sessions, parallel Claude Code instances, and background task management.

## Quick Reference

### Session Management

```bash
# Create new session
tmux new-session -s dev

# Detach from session
Ctrl+b d

# List sessions
tmux list-sessions

# Attach to session
tmux attach -t dev

# Kill session
tmux kill-session -t dev
```

### Window Management

```bash
# Create new window
Ctrl+b c

# Switch windows
Ctrl+b 0-9  # By number
Ctrl+b n    # Next
Ctrl+b p    # Previous

# Rename window
Ctrl+b ,

# Close window
Ctrl+b &
```

### Pane Management

```bash
# Split horizontally
Ctrl+b "

# Split vertically
Ctrl+b %

# Navigate panes
Ctrl+b arrow-keys

# Resize panes
Ctrl+b Ctrl+arrow-keys

# Close pane
Ctrl+b x
```

## Recommended Setup for This Project

### Development Session Layout

```bash
#!/bin/bash
# scripts/tmux-dev.sh

SESSION="guilde-dev"

tmux new-session -d -s $SESSION -n 'backend'
tmux send-keys -t $SESSION:backend 'cd backend && uv run uvicorn app.main:app --reload' Enter

tmux new-window -t $SESSION -n 'frontend'
tmux send-keys -t $SESSION:frontend 'cd frontend && bun dev' Enter

tmux new-window -t $SESSION -n 'claude'
tmux send-keys -t $SESSION:claude 'claude' Enter

tmux new-window -t $SESSION -n 'tests'
# Keep empty for running tests

tmux select-window -t $SESSION:claude
tmux attach -t $SESSION
```

### Multi-Claude Setup

```bash
# Window 1: Main Claude Code session
# Window 2: Claude for backend work
# Window 3: Claude for frontend work
# Window 4: Claude for tests/QA

# Navigate between with Ctrl+b 1, Ctrl+b 2, etc.
```

## Background Tasks with Claude Code

### Long-Running Operations

```bash
# Start Claude in tmux, run long task, detach
tmux new-session -d -s claude-task
tmux send-keys -t claude-task 'claude "Run full test suite and fix failures"' Enter

# Detach and do other work
# Later, check progress:
tmux attach -t claude-task
```

### Parallel Agent Execution

```bash
# Create session with multiple panes for parallel agents
tmux new-session -s agents -n 'parallel'
tmux split-window -h
tmux split-window -v
tmux select-pane -t 0
tmux split-window -v

# Send commands to each pane
tmux send-keys -t agents:parallel.0 'claude "Research technical feasibility"' Enter
tmux send-keys -t agents:parallel.1 'claude "Analyze business requirements"' Enter
tmux send-keys -t agents:parallel.2 'claude "Design architecture"' Enter
tmux send-keys -t agents:parallel.3 'claude "Review security implications"' Enter
```

## Integration with This Project

### Recommended Workflow

1. **Start dev session**: `./scripts/tmux-dev.sh`
2. **Run SDLC workflow**: `/sdlc-orchestration:full-feature "feature"`
3. **Monitor in parallel windows**: Tests, logs, frontend
4. **Detach when needed**: `Ctrl+b d`
5. **Resume later**: `tmux attach -t guilde-dev`

### Session Persistence

- Sessions survive SSH disconnects
- Long Claude operations continue in background
- Can check on agents from mobile via SSH

## Troubleshooting

### Common Issues

```bash
# Session already exists
tmux kill-session -t old-session

# No sessions running
tmux new-session -s dev

# Can't scroll in pane
Ctrl+b [  # Enter copy mode
q         # Exit copy mode

# Frozen pane
Ctrl+c    # Cancel current command
```

### Check Running Sessions

```bash
tmux list-sessions
tmux list-windows -t session-name
tmux list-panes -t session-name:window-index
```

## References

- [tmux Cheat Sheet](https://tmuxcheatsheet.com/)
- [Claude Code + tmux Guide](https://www.blle.co/blog/claude-code-tmux-beautiful-terminal)
- [tmux MCP Server](https://github.com/nickgnd/tmux-mcp)
