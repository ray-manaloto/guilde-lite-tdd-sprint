import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic_ai import RunContext

from app.core.config import settings

# Import Deps properly to avoid circular imports if possible, or use string forward ref if needed.
# Since Deps is defined in assistant.py, importing it here might cause circular import if assistant imports this.
# We will treat Deps as Any or define a Protocol if needed, but usually typed as 'assistant.Deps'.
# For now, we assume the caller handles imports or we use checking TYPE_CHECKING.
if TYPE_CHECKING:
    from app.agents.assistant import Deps
else:
    # Runtime mock/placeholder if needed, but usually PydanticAI handles this via generics
    pass

logger = logging.getLogger(__name__)

# Allowed characters for filenames and paths (alphanumeric, hyphen, underscore, dot, slash)
ALLOWED_FILENAME_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./")


def _audit_log(
    operation: str,
    path: str,
    user_id: str | None,
    success: bool,
    error: str | None = None,
) -> None:
    """Log filesystem operations for audit trail.

    Args:
        operation: The filesystem operation (read, write, list).
        path: The path being accessed.
        user_id: The user performing the operation (if available).
        success: Whether the operation succeeded.
        error: Error message if operation failed.
    """
    try:
        import logfire

        logfire.info(
            f"Filesystem {operation}",
            path=path,
            user_id=user_id,
            success=success,
            operation=operation,
            error=error,
        )
    except Exception:
        # Fall back to standard logging if logfire fails
        log_msg = f"Filesystem {operation}: path={path}, user_id={user_id}, success={success}"
        if error:
            log_msg += f", error={error}"
        logger.info(log_msg)


def _validate_path(session_root: Path, user_path: str) -> Path:
    """Validate and resolve path within sandbox.

    Performs comprehensive security validation:
    1. Checks for invalid/special characters
    2. Rejects absolute paths
    3. Rejects path traversal attempts (..)
    4. Ensures resolved path stays within sandbox
    5. Checks symlinks don't escape sandbox

    Args:
        session_root: The root directory of the session sandbox.
        user_path: The user-provided path to validate.

    Returns:
        The validated and resolved Path object.

    Raises:
        ValueError: If path escapes sandbox or contains invalid characters.
    """
    # 1. Check for invalid characters in path
    if not all(c in ALLOWED_FILENAME_CHARS for c in user_path):
        invalid_chars = set(user_path) - ALLOWED_FILENAME_CHARS
        raise ValueError(f"Invalid characters in path: {user_path!r} (found: {invalid_chars!r})")

    # 2. Reject absolute paths (Unix and Windows style)
    if user_path.startswith("/"):
        raise ValueError(f"Absolute paths not allowed: {user_path!r}")
    if len(user_path) > 1 and user_path[1] == ":":
        raise ValueError(f"Windows absolute paths not allowed: {user_path!r}")

    # 3. Reject path traversal attempts
    # Check each component to catch encoded/obfuscated traversal
    path_components = user_path.replace("\\", "/").split("/")
    for component in path_components:
        if component == "..":
            raise ValueError(f"Path traversal not allowed: {user_path!r}")
        # Also reject hidden files starting with .. (e.g., "..hidden")
        if component.startswith(".."):
            raise ValueError(f"Path components starting with '..' not allowed: {user_path!r}")

    # 4. Resolve the path and ensure it's within sandbox
    resolved_root = session_root.resolve()
    target = (session_root / user_path).resolve()

    if not target.is_relative_to(resolved_root):
        raise ValueError(
            f"Path escapes sandbox: {user_path!r} "
            f"(resolved to {target}, sandbox is {resolved_root})"
        )

    # 5. Check for symlink escape (if path exists and is a symlink)
    if target.exists() and target.is_symlink():
        # Get the real path following all symlinks
        real_target = target.resolve()
        if not real_target.is_relative_to(resolved_root):
            raise ValueError(
                f"Symlink escapes sandbox: {user_path!r} "
                f"(points to {real_target}, sandbox is {resolved_root})"
            )

    # 6. Also check parent directories for symlinks that might escape
    # Walk up from target to session_root checking each component
    current = target
    while current != resolved_root and current != current.parent:
        if current.exists() and current.is_symlink():
            real_current = current.resolve()
            if not real_current.is_relative_to(resolved_root):
                raise ValueError(
                    f"Parent symlink escapes sandbox: {current} (points to {real_current})"
                )
        current = current.parent

    return target


def _resolve_and_check_path(ctx: RunContext["Deps"], path: str) -> Path:
    """Resolve path and ensure it is within the session directory.

    This is a wrapper around _validate_path that extracts the session
    directory from the context.

    Args:
        ctx: Context with dependencies including session_dir.
        path: The user-provided relative path.

    Returns:
        The validated and resolved Path object.

    Raises:
        ValueError: If session directory not initialized or path is invalid.
    """
    if not ctx.deps.session_dir:
        debug_info = f"Settings: {settings.AUTOCODE_ARTIFACTS_DIR}"
        raise ValueError(f"Session directory not initialized. {debug_info}")

    session_root = ctx.deps.session_dir

    # Normalize the path - strip leading/trailing whitespace and normalize separators
    normalized_path = path.strip().replace("\\", "/")

    # Strip leading slash to treat as relative path
    # (already validated as not absolute in _validate_path, but normalize here)
    if normalized_path.startswith("/"):
        normalized_path = normalized_path.lstrip("/")

    # Handle empty path as current directory
    if not normalized_path:
        normalized_path = "."

    return _validate_path(session_root, normalized_path)


def _get_user_id(ctx: RunContext["Deps"]) -> str | None:
    """Extract user ID from context for audit logging.

    Args:
        ctx: Context with dependencies.

    Returns:
        User ID string if available, None otherwise.
    """
    try:
        # Try to get user_id from deps if available
        if hasattr(ctx.deps, "user_id") and ctx.deps.user_id:
            return str(ctx.deps.user_id)
        # Fall back to session_id if user_id not available or is None
        if hasattr(ctx.deps, "session_id") and ctx.deps.session_id:
            return f"session:{ctx.deps.session_id}"
    except Exception:
        pass
    return None


def read_file(ctx: RunContext["Deps"], path: str) -> str:
    """Read the content of a file from the session directory.

    Args:
        ctx: Context with dependencies.
        path: Relative path to the file (e.g., "logs/error.txt").

    Returns:
        Content of the file.
    """
    user_id = _get_user_id(ctx)
    try:
        target_path = _resolve_and_check_path(ctx, path)
        if not target_path.exists():
            error_msg = f"File '{path}' does not exist."
            _audit_log("read", path, user_id, success=False, error=error_msg)
            return f"Error: {error_msg}"
        if not target_path.is_file():
            error_msg = f"'{path}' is not a file."
            _audit_log("read", path, user_id, success=False, error=error_msg)
            return f"Error: {error_msg}"

        content = target_path.read_text(encoding="utf-8")
        _audit_log("read", path, user_id, success=True)
        return content
    except ValueError as e:
        # Security validation errors
        error_msg = str(e)
        logger.warning(f"read_file security violation: {e}")
        _audit_log("read", path, user_id, success=False, error=error_msg)
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = str(e)
        logger.error(f"read_file error: {e}")
        _audit_log("read", path, user_id, success=False, error=error_msg)
        return f"Error reading file: {error_msg}"


def write_file(ctx: RunContext["Deps"], path: str, content: str) -> str:
    """Write content to a file in the session directory.

    Args:
        ctx: Context with dependencies.
        path: Relative path to the file.
        content: Text content to write.

    Returns:
        Success message.
    """
    user_id = _get_user_id(ctx)
    try:
        target_path = _resolve_and_check_path(ctx, path)

        # Ensure parent directories exist
        target_path.parent.mkdir(parents=True, exist_ok=True)

        target_path.write_text(content, encoding="utf-8")
        _audit_log("write", path, user_id, success=True)
        return f"Successfully wrote to '{path}'."
    except ValueError as e:
        # Security validation errors
        error_msg = str(e)
        logger.warning(f"write_file security violation: {e}")
        _audit_log("write", path, user_id, success=False, error=error_msg)
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = str(e)
        logger.error(f"write_file error: {e}")
        _audit_log("write", path, user_id, success=False, error=error_msg)
        return f"Error writing file: {error_msg}"


def list_dir(ctx: RunContext["Deps"], path: str = ".") -> str:
    """List contents of a directory within the session directory.

    Args:
        ctx: Context with dependencies.
        path: Relative path to the directory (default is root).

    Returns:
        List of files and directories.
    """
    user_id = _get_user_id(ctx)
    try:
        target_path = _resolve_and_check_path(ctx, path)
        if not target_path.exists():
            error_msg = f"Directory '{path}' does not exist."
            _audit_log("list", path, user_id, success=False, error=error_msg)
            return f"Error: {error_msg}"
        if not target_path.is_dir():
            error_msg = f"'{path}' is not a directory."
            _audit_log("list", path, user_id, success=False, error=error_msg)
            return f"Error: {error_msg}"

        items = []
        for item in target_path.iterdir():
            prefix = "[DIR] " if item.is_dir() else "[FILE]"
            items.append(f"{prefix} {item.name}")

        _audit_log("list", path, user_id, success=True)
        return "\n".join(sorted(items)) if items else "(Empty directory)"
    except ValueError as e:
        # Security validation errors
        error_msg = str(e)
        logger.warning(f"list_dir security violation: {e}")
        _audit_log("list", path, user_id, success=False, error=error_msg)
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = str(e)
        logger.error(f"list_dir error: {e}")
        _audit_log("list", path, user_id, success=False, error=error_msg)
        return f"Error listing directory: {error_msg}"
