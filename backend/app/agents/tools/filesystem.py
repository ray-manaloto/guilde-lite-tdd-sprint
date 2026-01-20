import logging
import os
from pathlib import Path
from typing import List

from pydantic_ai import RunContext

# Import Deps properly to avoid circular imports if possible, or use string forward ref if needed.
# Since Deps is defined in assistant.py, importing it here might cause circular import if assistant imports this.
# We will treat Deps as Any or define a Protocol if needed, but usually typed as 'assistant.Deps'.
# For now, we assume the caller handles imports or we use checking TYPE_CHECKING.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.assistant import Deps
else:
    # Runtime mock/placeholder if needed, but usually PydanticAI handles this via generics
    pass

logger = logging.getLogger(__name__)

from app.core.config import settings

def _resolve_and_check_path(ctx: RunContext["Deps"], path: str) -> Path:
    """Resolve path and ensure it is within the session directory."""
    if not ctx.deps.session_dir:
        debug_info = f"Settings: {settings.AUTOCODE_ARTIFACTS_DIR}"
        raise ValueError(f"Session directory not initialized. {debug_info}")
    
    # Allow simple filenames or relative paths
    target_path = (ctx.deps.session_dir / path).resolve()
    session_root = ctx.deps.session_dir.resolve()
    
    if not target_path.is_relative_to(session_root):
        raise ValueError(f"Access denied: Path '{path}' resolves outside the session directory.")
    
    return target_path

def read_file(ctx: RunContext["Deps"], path: str) -> str:
    """Read the content of a file from the session directory.
    
    Args:
        ctx: Context with dependencies.
        path: Relative path to the file (e.g., "logs/error.txt").
        
    Returns:
        Content of the file.
    """
    try:
        target_path = _resolve_and_check_path(ctx, path)
        if not target_path.exists():
            return f"Error: File '{path}' does not exist."
        if not target_path.is_file():
            return f"Error: '{path}' is not a file."
            
        return target_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"read_file error: {e}")
        return f"Error reading file: {str(e)}"

def write_file(ctx: RunContext["Deps"], path: str, content: str) -> str:
    """Write content to a file in the session directory.
    
    Args:
        ctx: Context with dependencies.
        path: Relative path to the file.
        content: Text content to write.
        
    Returns:
        Success message.
    """
    try:
        target_path = _resolve_and_check_path(ctx, path)
        
        # Ensure parent directories exist
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        target_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote to '{path}'."
    except Exception as e:
        logger.error(f"write_file error: {e}")
        return f"Error writing file: {str(e)}"

def list_dir(ctx: RunContext["Deps"], path: str = ".") -> str:
    """List contents of a directory within the session directory.
    
    Args:
        ctx: Context with dependencies.
        path: Relative path to the directory (default is root).
        
    Returns:
        List of files and directories.
    """
    try:
        target_path = _resolve_and_check_path(ctx, path)
        if not target_path.exists():
            return f"Error: Directory '{path}' does not exist."
        if not target_path.is_dir():
            return f"Error: '{path}' is not a directory."
            
        items = []
        for item in target_path.iterdir():
            prefix = "[DIR] " if item.is_dir() else "[FILE]"
            items.append(f"{prefix} {item.name}")
            
        return "\n".join(sorted(items)) if items else "(Empty directory)"
    except Exception as e:
        logger.error(f"list_dir error: {e}")
        return f"Error listing directory: {str(e)}"
