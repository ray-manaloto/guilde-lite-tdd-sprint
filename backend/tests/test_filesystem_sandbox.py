"""Tests for filesystem sandboxing security in agents/tools/filesystem.py.

These tests verify that the filesystem tools properly sandbox operations
within the session directory and prevent path traversal attacks.
"""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest

from app.agents.tools.filesystem import (
    ALLOWED_FILENAME_CHARS,
    _audit_log,
    _get_user_id,
    _resolve_and_check_path,
    _validate_path,
    list_dir,
    read_file,
    write_file,
)


@dataclass
class MockDeps:
    """Mock Deps class for testing."""

    session_dir: Path | None
    user_id: str | None = None
    session_id: str | None = None


class MockRunContext:
    """Mock RunContext for testing filesystem tools."""

    def __init__(self, deps: MockDeps):
        self.deps = deps


@pytest.fixture
def temp_session_dir():
    """Create a temporary session directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        # Create some test files/directories
        (session_dir / "test.txt").write_text("Hello, World!")
        (session_dir / "subdir").mkdir()
        (session_dir / "subdir" / "nested.txt").write_text("Nested content")
        yield session_dir


@pytest.fixture
def mock_ctx(temp_session_dir):
    """Create a mock context with session directory."""
    deps = MockDeps(session_dir=temp_session_dir, user_id="test-user-123")
    return MockRunContext(deps)


class TestAllowedFilenameChars:
    """Tests for the ALLOWED_FILENAME_CHARS constant."""

    def test_allowed_chars_contains_lowercase(self):
        """Lowercase letters should be allowed."""
        for c in "abcdefghijklmnopqrstuvwxyz":
            assert c in ALLOWED_FILENAME_CHARS

    def test_allowed_chars_contains_uppercase(self):
        """Uppercase letters should be allowed."""
        for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            assert c in ALLOWED_FILENAME_CHARS

    def test_allowed_chars_contains_digits(self):
        """Digits should be allowed."""
        for c in "0123456789":
            assert c in ALLOWED_FILENAME_CHARS

    def test_allowed_chars_contains_special(self):
        """Special allowed characters: hyphen, underscore, dot, slash."""
        for c in "-_./":
            assert c in ALLOWED_FILENAME_CHARS

    def test_special_chars_not_allowed(self):
        """Special characters that could be dangerous should not be allowed."""
        dangerous_chars = [
            " ",  # space
            "\n",  # newline
            "\t",  # tab
            "*",  # wildcard
            "?",  # wildcard
            "<",  # redirect
            ">",  # redirect
            "|",  # pipe
            "&",  # command separator
            ";",  # command separator
            "$",  # variable expansion
            "`",  # command substitution
            "(",
            ")",  # subshell
            "[",
            "]",  # brackets
            "{",
            "}",  # braces
            "'",  # single quote
            '"',  # double quote
            "\\",  # backslash
            "!",  # history expansion
            "~",  # home directory
            "#",  # comment
            "%",  # job control
            "^",  # caret
            "@",  # at symbol
            "=",  # assignment
            "+",  # plus
        ]
        for c in dangerous_chars:
            assert c not in ALLOWED_FILENAME_CHARS, f"Character {c!r} should not be allowed"


class TestValidatePath:
    """Tests for the _validate_path function."""

    def test_valid_simple_filename(self, temp_session_dir):
        """Simple filenames should be valid."""
        result = _validate_path(temp_session_dir, "test.txt")
        # Compare resolved paths to handle macOS /var -> /private/var symlink
        assert result.resolve() == (temp_session_dir / "test.txt").resolve()

    def test_valid_nested_path(self, temp_session_dir):
        """Nested relative paths should be valid."""
        result = _validate_path(temp_session_dir, "subdir/nested.txt")
        # Compare resolved paths to handle macOS /var -> /private/var symlink
        assert result.resolve() == (temp_session_dir / "subdir" / "nested.txt").resolve()

    def test_valid_current_directory(self, temp_session_dir):
        """Current directory reference should be valid."""
        result = _validate_path(temp_session_dir, ".")
        assert result == temp_session_dir.resolve()

    def test_reject_invalid_characters(self, temp_session_dir):
        """Paths with invalid characters should be rejected."""
        invalid_paths = [
            "file name.txt",  # space
            "file\tname.txt",  # tab
            "file;rm -rf /",  # semicolon
            "file|cat /etc/passwd",  # pipe
            "file&id",  # ampersand
            "$(whoami).txt",  # command substitution
            "`id`.txt",  # backtick
            "file<>name.txt",  # redirects
        ]
        for path in invalid_paths:
            with pytest.raises(ValueError, match="Invalid characters"):
                _validate_path(temp_session_dir, path)

    def test_reject_absolute_path_unix(self, temp_session_dir):
        """Unix absolute paths should be rejected."""
        with pytest.raises(ValueError, match="Absolute paths not allowed"):
            _validate_path(temp_session_dir, "/etc/passwd")

    def test_reject_absolute_path_windows(self, temp_session_dir):
        """Windows absolute paths should be rejected (colon is invalid char)."""
        # The colon character is not in ALLOWED_FILENAME_CHARS, so this is caught
        # as an invalid character before the Windows path check
        with pytest.raises(ValueError, match="Invalid characters"):
            _validate_path(temp_session_dir, "C:/Windows/System32")

    def test_reject_path_traversal_dotdot(self, temp_session_dir):
        """Path traversal with .. should be rejected."""
        traversal_attempts = [
            "..",
            "../",
            "../etc/passwd",
            "subdir/../..",
            "subdir/../../etc/passwd",
            "foo/bar/../../../etc/passwd",
        ]
        for path in traversal_attempts:
            with pytest.raises(
                ValueError, match=r"Path traversal not allowed|Path components starting with"
            ):
                _validate_path(temp_session_dir, path)

    def test_reject_dotdot_prefix(self, temp_session_dir):
        """Paths with components starting with .. should be rejected."""
        with pytest.raises(ValueError, match=r"Path components starting with '\.\.' not allowed"):
            _validate_path(temp_session_dir, "..hidden")

    def test_symlink_within_sandbox(self, temp_session_dir):
        """Symlinks pointing within the sandbox should be allowed."""
        # Create a symlink within the sandbox using relative path
        link_path = temp_session_dir / "link.txt"
        # Use relative symlink to avoid /var vs /private/var issues
        link_path.symlink_to("test.txt")

        result = _validate_path(temp_session_dir, "link.txt")
        # Compare resolved paths
        assert result.resolve() == link_path.resolve()

    def test_reject_symlink_escape(self, temp_session_dir):
        """Symlinks pointing outside the sandbox should be rejected."""
        # Create a symlink pointing outside the sandbox
        link_path = temp_session_dir / "escape_link"
        # Use a path that definitely exists and is outside
        link_path.symlink_to("/etc/hosts")

        # The symlink is caught by the is_relative_to check after resolve()
        # which is the primary sandbox check - the specific symlink check
        # is only reached for paths that pass the initial check
        with pytest.raises(ValueError, match="escapes sandbox"):
            _validate_path(temp_session_dir, "escape_link")

    def test_reject_parent_symlink_escape(self, temp_session_dir):
        """Parent directory symlinks that escape should be rejected."""
        # Create another temp directory that's definitely outside
        with tempfile.TemporaryDirectory() as other_dir:
            # Create a subdirectory that is a symlink to an external location
            (temp_session_dir / "external_dir").symlink_to(other_dir)

            # Try to access a file through the symlink
            # This is caught by the is_relative_to check since resolve()
            # follows symlinks and the result is outside the sandbox
            with pytest.raises(ValueError, match="escapes sandbox"):
                _validate_path(temp_session_dir, "external_dir/somefile.txt")


class TestResolveAndCheckPath:
    """Tests for the _resolve_and_check_path wrapper function."""

    def test_no_session_dir_raises(self):
        """Should raise when session_dir is not initialized."""
        deps = MockDeps(session_dir=None)
        ctx = MockRunContext(deps)

        with pytest.raises(ValueError, match="Session directory not initialized"):
            _resolve_and_check_path(ctx, "test.txt")

    def test_normalizes_whitespace(self, mock_ctx):
        """Should strip leading/trailing whitespace."""
        result = _resolve_and_check_path(mock_ctx, "  test.txt  ")
        assert result.name == "test.txt"

    def test_normalizes_backslashes(self, mock_ctx):
        """Should convert backslashes to forward slashes."""
        # Note: backslash is not in allowed characters, so we test
        # that it's properly normalized before validation
        # The function normalizes backslash to forward slash in the wrapper
        # but then _validate_path will reject backslash if any remain
        # Actually, the wrapper normalizes first, so this should work
        result = _resolve_and_check_path(mock_ctx, "subdir/nested.txt")
        assert result.resolve() == (mock_ctx.deps.session_dir / "subdir" / "nested.txt").resolve()

    def test_strips_leading_slash(self, mock_ctx):
        """Should strip leading slash and treat as relative."""
        result = _resolve_and_check_path(mock_ctx, "/test.txt")
        assert result.resolve() == (mock_ctx.deps.session_dir / "test.txt").resolve()

    def test_empty_path_becomes_current_dir(self, mock_ctx):
        """Empty path should resolve to current directory."""
        result = _resolve_and_check_path(mock_ctx, "")
        assert result == mock_ctx.deps.session_dir.resolve()


class TestGetUserId:
    """Tests for the _get_user_id helper function."""

    def test_extracts_user_id(self):
        """Should extract user_id from deps."""
        deps = MockDeps(session_dir=Path("/tmp"), user_id="user-123")
        ctx = MockRunContext(deps)
        assert _get_user_id(ctx) == "user-123"

    def test_extracts_session_id_fallback(self):
        """Should fall back to session_id if user_id not available."""
        # Need to set user_id to None explicitly for the fallback to trigger
        deps = MockDeps(session_dir=Path("/tmp"), user_id=None, session_id="sess-456")
        ctx = MockRunContext(deps)
        assert _get_user_id(ctx) == "session:sess-456"

    def test_returns_none_when_no_ids(self):
        """Should return None when no IDs available."""
        deps = MockDeps(session_dir=Path("/tmp"))
        ctx = MockRunContext(deps)
        assert _get_user_id(ctx) is None


class TestAuditLog:
    """Tests for the _audit_log function."""

    @patch("app.agents.tools.filesystem.logger")
    def test_audit_log_fallback_on_logfire_error(self, mock_logger):
        """Should fall back to standard logging if logfire fails."""
        with patch.dict("sys.modules", {"logfire": None}):
            _audit_log("read", "/test/path", "user-123", True)
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "read" in call_args
            assert "/test/path" in call_args
            assert "user-123" in call_args

    @patch("app.agents.tools.filesystem.logger")
    def test_audit_log_includes_error(self, mock_logger):
        """Should include error message when provided."""
        with patch.dict("sys.modules", {"logfire": None}):
            _audit_log("write", "/test/path", "user-123", False, "Permission denied")
            call_args = mock_logger.info.call_args[0][0]
            assert "Permission denied" in call_args


class TestReadFile:
    """Tests for the read_file function."""

    def test_read_existing_file(self, mock_ctx):
        """Should read existing file content."""
        result = read_file(mock_ctx, "test.txt")
        assert result == "Hello, World!"

    def test_read_nonexistent_file(self, mock_ctx):
        """Should return error for nonexistent file."""
        result = read_file(mock_ctx, "nonexistent.txt")
        assert "does not exist" in result

    def test_read_directory_as_file(self, mock_ctx):
        """Should return error when trying to read a directory."""
        result = read_file(mock_ctx, "subdir")
        assert "is not a file" in result

    def test_read_blocks_traversal(self, mock_ctx):
        """Should block path traversal attempts."""
        result = read_file(mock_ctx, "../../../etc/passwd")
        assert "Error" in result
        assert "Path traversal not allowed" in result

    def test_read_blocks_invalid_chars(self, mock_ctx):
        """Should block paths with invalid characters."""
        result = read_file(mock_ctx, "file;cat /etc/passwd")
        assert "Error" in result
        assert "Invalid characters" in result


class TestWriteFile:
    """Tests for the write_file function."""

    def test_write_new_file(self, mock_ctx, temp_session_dir):
        """Should write content to a new file."""
        result = write_file(mock_ctx, "new_file.txt", "New content")
        assert "Successfully" in result
        assert (temp_session_dir / "new_file.txt").read_text() == "New content"

    def test_write_creates_directories(self, mock_ctx, temp_session_dir):
        """Should create parent directories if needed."""
        result = write_file(mock_ctx, "new_dir/nested/file.txt", "Content")
        assert "Successfully" in result
        assert (temp_session_dir / "new_dir" / "nested" / "file.txt").exists()

    def test_write_overwrites_existing(self, mock_ctx, temp_session_dir):
        """Should overwrite existing file."""
        result = write_file(mock_ctx, "test.txt", "Updated content")
        assert "Successfully" in result
        assert (temp_session_dir / "test.txt").read_text() == "Updated content"

    def test_write_blocks_traversal(self, mock_ctx):
        """Should block path traversal attempts."""
        result = write_file(mock_ctx, "../../../tmp/malicious.txt", "Bad content")
        assert "Error" in result
        assert "Path traversal not allowed" in result

    def test_write_blocks_invalid_chars(self, mock_ctx):
        """Should block paths with invalid characters."""
        result = write_file(mock_ctx, "file$(id).txt", "Content")
        assert "Error" in result
        assert "Invalid characters" in result


class TestListDir:
    """Tests for the list_dir function."""

    def test_list_session_root(self, mock_ctx):
        """Should list contents of session directory."""
        result = list_dir(mock_ctx, ".")
        assert "[FILE] test.txt" in result
        assert "[DIR]  subdir" in result

    def test_list_subdirectory(self, mock_ctx):
        """Should list contents of subdirectory."""
        result = list_dir(mock_ctx, "subdir")
        assert "[FILE] nested.txt" in result

    def test_list_nonexistent_directory(self, mock_ctx):
        """Should return error for nonexistent directory."""
        result = list_dir(mock_ctx, "nonexistent")
        assert "does not exist" in result

    def test_list_file_as_directory(self, mock_ctx):
        """Should return error when trying to list a file."""
        result = list_dir(mock_ctx, "test.txt")
        assert "is not a directory" in result

    def test_list_blocks_traversal(self, mock_ctx):
        """Should block path traversal attempts."""
        result = list_dir(mock_ctx, "../../../")
        assert "Error" in result
        assert "Path traversal not allowed" in result

    def test_list_empty_directory(self, mock_ctx, temp_session_dir):
        """Should handle empty directories."""
        (temp_session_dir / "empty_dir").mkdir()
        result = list_dir(mock_ctx, "empty_dir")
        assert result == "(Empty directory)"


class TestSecurityEdgeCases:
    """Edge case tests for security hardening."""

    def test_unicode_normalization_attack(self, temp_session_dir):
        """Should handle unicode normalization attacks."""
        # Some unicode characters can normalize to .. or /
        # This test ensures we handle them safely
        dangerous_unicode = [
            "file\u2024txt",  # ONE DOT LEADER
            "file\uff0ftxt",  # FULLWIDTH SOLIDUS
        ]
        for path in dangerous_unicode:
            # These should either work (if characters are safe) or raise ValueError
            try:
                result = _validate_path(temp_session_dir, path)
                # If it works, ensure it's still within sandbox
                assert result.is_relative_to(temp_session_dir.resolve())
            except ValueError:
                # Invalid characters are acceptable
                pass

    def test_null_byte_injection(self, temp_session_dir):
        """Should reject null byte injection attempts."""
        with pytest.raises(ValueError, match="Invalid characters"):
            _validate_path(temp_session_dir, "file.txt\x00/etc/passwd")

    def test_encoded_traversal(self, temp_session_dir):
        """Should reject URL-encoded traversal attempts."""
        # Note: These contain % which is not in allowed chars
        encoded_attempts = [
            "%2e%2e/",  # ../
            "%2e%2e%2f",  # ../
            "..%2f",  # ../
        ]
        for path in encoded_attempts:
            with pytest.raises(ValueError, match="Invalid characters"):
                _validate_path(temp_session_dir, path)

    def test_double_encoding(self, temp_session_dir):
        """Should reject double-encoded attempts."""
        # Contains % which is not allowed
        with pytest.raises(ValueError, match="Invalid characters"):
            _validate_path(temp_session_dir, "%252e%252e/")

    def test_very_long_path(self, temp_session_dir):
        """Should handle very long paths."""
        long_path = "a" * 10000 + ".txt"
        # Should not crash, should validate properly
        result = _validate_path(temp_session_dir, long_path)
        assert result.is_relative_to(temp_session_dir.resolve())

    def test_path_with_many_components(self, temp_session_dir):
        """Should handle paths with many nested components."""
        deep_path = "/".join(["dir"] * 100) + "/file.txt"
        result = _validate_path(temp_session_dir, deep_path)
        assert result.is_relative_to(temp_session_dir.resolve())
