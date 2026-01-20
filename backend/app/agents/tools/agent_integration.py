
import logging
import shlex
import subprocess
from typing import Optional

from pydantic_ai import RunContext

from app.agents.deps import Deps

logger = logging.getLogger(__name__)


def run_codex_agent(ctx: RunContext[Deps], prompt: str) -> str:
    """
    Run the Codex CLI agent in non-interactive mode.
    
    This tool allows the agent to delegate tasks to the Codex agent.
    The Codex agent runs in a restricted mode (-a never) and returns the output.
    
    Args:
        ctx: The run context.
        prompt: The instruction or query for Codex.
        
    Returns:
        The standard output from the Codex CLI.
    """
    # Construct the command: codex --no-alt-screen -a never exec "prompt"
    # We use shlex.quote to safely escape the prompt for the shell if needed,
    # but subprocess.run with a list is safer and preferred.
    
    cmd = ["codex", "--no-alt-screen", "-a", "never", "exec", prompt]
    
    try:
        logger.info(f"Invoking Codex Agent with prompt: {prompt[:50]}...")
        # running synchronously since these are CLI tools that might block
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            limit=20 * 1024 * 1024, # 20MB limit on output to prevent hanging
            timeout=120 # 2 minute timeout
        )
        
        if result.returncode != 0:
            error_msg = f"Codex agent failed with code {result.returncode}.\nStderr: {result.stderr}"
            logger.error(error_msg)
            return error_msg
            
        return result.stdout
        
    except subprocess.TimeoutExpired:
        logger.error("Codex agent timed out.")
        return "Error: Codex agent timed out after 120 seconds."
    except Exception as e:
        logger.exception(f"Failed to run Codex agent: {e}")
        return f"Error executing Codex agent: {str(e)}"


def run_claude_agent(ctx: RunContext[Deps], prompt: str) -> str:
    """
    Run the Claude Code CLI agent in print-only mode.
    
    This tool allows the agent to delegate tasks to the Claude Code agent.
    
    Args:
        ctx: The run context.
        prompt: The instruction or query for Claude.
        
    Returns:
        The standard output from the Claude CLI.
    """
    # Construct the command: claude -p "prompt"
    cmd = ["claude", "-p", prompt]
    
    try:
        logger.info(f"Invoking Claude Agent with prompt: {prompt[:50]}...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120 # 2 minute timeout
        )
        
        if result.returncode != 0:
            error_msg = f"Claude agent failed with code {result.returncode}.\nStderr: {result.stderr}"
            logger.error(error_msg)
            return error_msg
            
        return result.stdout

    except subprocess.TimeoutExpired:
        logger.error("Claude agent timed out.")
        return "Error: Claude agent timed out after 120 seconds."
    except Exception as e:
        logger.exception(f"Failed to run Claude agent: {e}")
        return f"Error executing Claude agent: {str(e)}"
