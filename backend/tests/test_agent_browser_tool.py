"""Tests for agent-browser tool wrapper."""

import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.agents.tools.agent_browser import run_agent_browser


def test_run_agent_browser_requires_command():
    """Empty commands are rejected."""
    with pytest.raises(ValueError, match="command is required"):
        run_agent_browser("")


def test_run_agent_browser_returns_stdout(monkeypatch):
    """Successful runs return stdout."""
    fake_result = SimpleNamespace(returncode=0, stdout="ok\n", stderr="")
    monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

    output = run_agent_browser("open https://example.com")
    assert output == "ok"


def test_run_agent_browser_returns_error(monkeypatch):
    """Non-zero exit returns formatted error."""
    fake_result = SimpleNamespace(returncode=1, stdout="", stderr="boom")
    monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

    output = run_agent_browser("open https://example.com")
    assert output == "agent-browser failed: boom"


def test_run_agent_browser_missing_cli(monkeypatch):
    """Missing CLI produces a runtime error."""
    def _raise(*_args, **_kwargs):
        raise FileNotFoundError("agent-browser")

    monkeypatch.setattr(subprocess, "run", _raise)

    with pytest.raises(RuntimeError, match="agent-browser CLI not found"):
        run_agent_browser("open https://example.com")
