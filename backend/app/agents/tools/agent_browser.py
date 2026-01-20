"""Agent-browser tool wrapper."""

from __future__ import annotations

import shlex
import subprocess


def run_agent_browser(command: str, timeout_seconds: int | None = 60) -> str:
    """Run an agent-browser CLI command and return its output."""
    if not command or not command.strip():
        raise ValueError("agent-browser command is required")

    args = ["agent-browser", *shlex.split(command)]

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("agent-browser CLI not found in PATH") from exc
    except subprocess.TimeoutExpired:
        return f"agent-browser timed out after {timeout_seconds} seconds"

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0:
        if stderr:
            return f"agent-browser failed: {stderr}"
        if stdout:
            return f"agent-browser failed: {stdout}"
        return "agent-browser failed with no output"

    return stdout or "agent-browser completed with no output"
