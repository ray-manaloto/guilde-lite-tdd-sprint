"""Comprehensive tests for agent-browser tool wrapper.

Tests cover:
- Command validation and sanitization
- Subprocess execution and error handling
- Timeout handling
- Return value processing
- Telemetry integration
- Security considerations
"""

import subprocess
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.agents.tools.agent_browser import run_agent_browser


class TestAgentBrowserCommandValidation:
    """Tests for command input validation."""

    def test_empty_string_rejected(self):
        """Empty string command raises ValueError."""
        with pytest.raises(ValueError, match="command is required"):
            run_agent_browser("")

    def test_whitespace_only_rejected(self):
        """Whitespace-only command raises ValueError."""
        with pytest.raises(ValueError, match="command is required"):
            run_agent_browser("   ")

    def test_none_rejected(self):
        """None command raises appropriate error."""
        with pytest.raises((ValueError, TypeError)):
            run_agent_browser(None)  # type: ignore

    def test_valid_command_accepted(self, monkeypatch):
        """Valid command string is accepted."""
        fake_result = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

        result = run_agent_browser("open https://example.com")
        assert result == "ok"


class TestAgentBrowserCommandParsing:
    """Tests for command argument parsing via shlex."""

    def test_simple_command(self, monkeypatch):
        """Simple command is parsed correctly."""
        mock_run = Mock(return_value=SimpleNamespace(returncode=0, stdout="ok", stderr=""))
        monkeypatch.setattr(subprocess, "run", mock_run)

        run_agent_browser("open https://example.com")

        call_args = mock_run.call_args[0][0]
        assert call_args == ["agent-browser", "open", "https://example.com"]

    def test_command_with_quotes(self, monkeypatch):
        """Command with quoted arguments is parsed correctly."""
        mock_run = Mock(return_value=SimpleNamespace(returncode=0, stdout="ok", stderr=""))
        monkeypatch.setattr(subprocess, "run", mock_run)

        run_agent_browser('click "Submit Button"')

        call_args = mock_run.call_args[0][0]
        assert call_args == ["agent-browser", "click", "Submit Button"]

    def test_command_with_multiple_args(self, monkeypatch):
        """Command with multiple arguments is parsed correctly."""
        mock_run = Mock(return_value=SimpleNamespace(returncode=0, stdout="ok", stderr=""))
        monkeypatch.setattr(subprocess, "run", mock_run)

        run_agent_browser("type input#email test@example.com")

        call_args = mock_run.call_args[0][0]
        assert call_args == ["agent-browser", "type", "input#email", "test@example.com"]

    def test_command_with_special_chars_in_url(self, monkeypatch):
        """URL with query params is parsed correctly."""
        mock_run = Mock(return_value=SimpleNamespace(returncode=0, stdout="ok", stderr=""))
        monkeypatch.setattr(subprocess, "run", mock_run)

        run_agent_browser("open 'https://example.com/search?q=test&page=1'")

        call_args = mock_run.call_args[0][0]
        assert call_args == ["agent-browser", "open", "https://example.com/search?q=test&page=1"]


class TestAgentBrowserExecution:
    """Tests for subprocess execution."""

    def test_successful_execution_returns_stdout(self, monkeypatch):
        """Successful execution returns stdout content."""
        fake_result = SimpleNamespace(returncode=0, stdout="Page title: Example\n", stderr="")
        monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

        result = run_agent_browser("get title")
        assert result == "Page title: Example"

    def test_successful_execution_strips_whitespace(self, monkeypatch):
        """Output whitespace is stripped."""
        fake_result = SimpleNamespace(returncode=0, stdout="  result with spaces  \n\n", stderr="")
        monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

        result = run_agent_browser("get text")
        assert result == "result with spaces"

    def test_empty_stdout_returns_default_message(self, monkeypatch):
        """Empty stdout returns informative message."""
        fake_result = SimpleNamespace(returncode=0, stdout="", stderr="")
        monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

        result = run_agent_browser("click button")
        assert result == "agent-browser completed with no output"

    def test_subprocess_called_with_correct_options(self, monkeypatch):
        """Subprocess is called with capture_output, text, timeout, check=False."""
        mock_run = Mock(return_value=SimpleNamespace(returncode=0, stdout="ok", stderr=""))
        monkeypatch.setattr(subprocess, "run", mock_run)

        run_agent_browser("open https://example.com", timeout_seconds=30)

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["capture_output"] is True
        assert call_kwargs["text"] is True
        assert call_kwargs["timeout"] == 30
        assert call_kwargs["check"] is False


class TestAgentBrowserErrorHandling:
    """Tests for error handling scenarios."""

    def test_nonzero_exit_with_stderr(self, monkeypatch):
        """Non-zero exit with stderr returns error message."""
        fake_result = SimpleNamespace(returncode=1, stdout="", stderr="Element not found")
        monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

        result = run_agent_browser("click #nonexistent")
        assert result == "agent-browser failed: Element not found"

    def test_nonzero_exit_with_stdout_only(self, monkeypatch):
        """Non-zero exit with only stdout returns that as error."""
        fake_result = SimpleNamespace(returncode=1, stdout="Error: timeout", stderr="")
        monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

        result = run_agent_browser("wait #slow-element")
        assert result == "agent-browser failed: Error: timeout"

    def test_nonzero_exit_no_output(self, monkeypatch):
        """Non-zero exit with no output returns generic message."""
        fake_result = SimpleNamespace(returncode=1, stdout="", stderr="")
        monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

        result = run_agent_browser("unknown command")
        assert result == "agent-browser failed with no output"

    def test_cli_not_found_raises_runtime_error(self, monkeypatch):
        """Missing CLI raises RuntimeError."""
        def raise_not_found(*args, **kwargs):
            raise FileNotFoundError("agent-browser")

        monkeypatch.setattr(subprocess, "run", raise_not_found)

        with pytest.raises(RuntimeError, match="agent-browser CLI not found"):
            run_agent_browser("open https://example.com")

    def test_various_exit_codes(self, monkeypatch):
        """Various non-zero exit codes are handled."""
        for exit_code in [1, 2, 127, 255]:
            fake_result = SimpleNamespace(returncode=exit_code, stdout="", stderr=f"Exit {exit_code}")
            monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

            result = run_agent_browser("test")
            assert f"Exit {exit_code}" in result


class TestAgentBrowserTimeout:
    """Tests for timeout handling."""

    def test_default_timeout_is_60_seconds(self, monkeypatch):
        """Default timeout is 60 seconds."""
        mock_run = Mock(return_value=SimpleNamespace(returncode=0, stdout="ok", stderr=""))
        monkeypatch.setattr(subprocess, "run", mock_run)

        run_agent_browser("open https://example.com")

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 60

    def test_custom_timeout(self, monkeypatch):
        """Custom timeout is passed to subprocess."""
        mock_run = Mock(return_value=SimpleNamespace(returncode=0, stdout="ok", stderr=""))
        monkeypatch.setattr(subprocess, "run", mock_run)

        run_agent_browser("open https://example.com", timeout_seconds=120)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 120

    def test_none_timeout_disables_timeout(self, monkeypatch):
        """None timeout disables subprocess timeout."""
        mock_run = Mock(return_value=SimpleNamespace(returncode=0, stdout="ok", stderr=""))
        monkeypatch.setattr(subprocess, "run", mock_run)

        run_agent_browser("open https://example.com", timeout_seconds=None)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] is None

    def test_timeout_expired_returns_message(self, monkeypatch):
        """TimeoutExpired returns informative message."""
        def raise_timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="agent-browser", timeout=30)

        monkeypatch.setattr(subprocess, "run", raise_timeout)

        result = run_agent_browser("slow-operation", timeout_seconds=30)
        assert result == "agent-browser timed out after 30 seconds"


class TestAgentBrowserTelemetry:
    """Tests for telemetry integration."""

    def test_telemetry_span_created(self, monkeypatch):
        """Telemetry span is created with command."""
        fake_result = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

        # Mock telemetry_span
        span_calls = []

        class MockContextManager:
            def __enter__(self):
                return ("trace-id", "span-id")
            def __exit__(self, *args):
                pass

        def mock_telemetry_span(name, **kwargs):
            span_calls.append((name, kwargs))
            return MockContextManager()

        with patch("app.agents.tools.agent_browser.telemetry_span", mock_telemetry_span):
            run_agent_browser("open https://example.com")

        assert len(span_calls) == 1
        assert span_calls[0][0] == "agent_browser.cli"
        assert span_calls[0][1]["command"] == "open https://example.com"


class TestAgentBrowserSecurityConsiderations:
    """Tests for security-related behavior."""

    def test_command_injection_via_shell_not_possible(self, monkeypatch):
        """Shell injection is prevented by using list args (not shell=True)."""
        mock_run = Mock(return_value=SimpleNamespace(returncode=0, stdout="ok", stderr=""))
        monkeypatch.setattr(subprocess, "run", mock_run)

        # Attempt shell injection
        run_agent_browser("open https://example.com; rm -rf /")

        # Verify shell=True is NOT used (it's not in kwargs)
        call_kwargs = mock_run.call_args[1]
        assert "shell" not in call_kwargs or call_kwargs.get("shell") is False

    def test_backtick_command_substitution_not_executed(self, monkeypatch):
        """Backtick command substitution is not executed."""
        mock_run = Mock(return_value=SimpleNamespace(returncode=0, stdout="ok", stderr=""))
        monkeypatch.setattr(subprocess, "run", mock_run)

        run_agent_browser("open `whoami`.example.com")

        # The backticks should be passed as literal characters
        call_args = mock_run.call_args[0][0]
        # shlex will parse this as a single argument
        assert "`whoami`.example.com" in call_args

    def test_env_variable_not_expanded(self, monkeypatch):
        """Environment variables are not expanded."""
        mock_run = Mock(return_value=SimpleNamespace(returncode=0, stdout="ok", stderr=""))
        monkeypatch.setattr(subprocess, "run", mock_run)

        run_agent_browser("open https://$HOME.example.com")

        call_args = mock_run.call_args[0][0]
        # $HOME should not be expanded
        assert "$HOME.example.com" in " ".join(call_args)


class TestAgentBrowserIntegrationScenarios:
    """Tests for realistic usage scenarios."""

    def test_navigate_and_get_title_flow(self, monkeypatch):
        """Simulate navigate then get title flow."""
        call_count = [0]

        def mock_run(args, **kwargs):
            call_count[0] += 1
            if "open" in args:
                return SimpleNamespace(returncode=0, stdout="Navigated to https://example.com", stderr="")
            elif "title" in args:
                return SimpleNamespace(returncode=0, stdout="Example Domain", stderr="")
            return SimpleNamespace(returncode=0, stdout="ok", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)

        result1 = run_agent_browser("open https://example.com")
        result2 = run_agent_browser("get title")

        assert "Navigated" in result1
        assert "Example Domain" in result2
        assert call_count[0] == 2

    def test_form_fill_flow(self, monkeypatch):
        """Simulate form fill flow."""
        operations = []

        def mock_run(args, **kwargs):
            operations.append(args[1] if len(args) > 1 else "unknown")
            return SimpleNamespace(returncode=0, stdout="ok", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)

        run_agent_browser("type #email test@example.com")
        run_agent_browser("type #password secret123")
        run_agent_browser("click #submit")

        assert operations == ["type", "type", "click"]

    def test_wait_for_element_timeout(self, monkeypatch):
        """Simulate waiting for element that times out."""
        fake_result = SimpleNamespace(returncode=1, stdout="", stderr="Timeout waiting for #loading")
        monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

        result = run_agent_browser("wait #loading", timeout_seconds=10)
        assert "Timeout waiting" in result


class TestAgentBrowserEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_long_output(self, monkeypatch):
        """Very long output is handled."""
        long_output = "x" * 100000
        fake_result = SimpleNamespace(returncode=0, stdout=long_output, stderr="")
        monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

        result = run_agent_browser("get html")
        assert len(result) == 100000

    def test_unicode_in_output(self, monkeypatch):
        """Unicode in output is preserved."""
        fake_result = SimpleNamespace(returncode=0, stdout="Title: 日本語テスト 🎉", stderr="")
        monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

        result = run_agent_browser("get title")
        assert "日本語テスト" in result
        assert "🎉" in result

    def test_newlines_in_output(self, monkeypatch):
        """Newlines in output are preserved (except trailing)."""
        fake_result = SimpleNamespace(returncode=0, stdout="Line 1\nLine 2\nLine 3\n", stderr="")
        monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

        result = run_agent_browser("get text")
        assert "Line 1\nLine 2\nLine 3" == result

    def test_stderr_and_stdout_both_present_on_error(self, monkeypatch):
        """When both stdout and stderr present on error, stderr takes precedence."""
        fake_result = SimpleNamespace(
            returncode=1,
            stdout="Some output before error",
            stderr="The actual error message"
        )
        monkeypatch.setattr(subprocess, "run", Mock(return_value=fake_result))

        result = run_agent_browser("failing command")
        assert "The actual error message" in result
        assert "Some output before error" not in result
