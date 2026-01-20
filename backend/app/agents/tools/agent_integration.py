
import logging
import os
import shlex
import subprocess
from typing import Optional

import logfire
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
    with logfire.span("run_codex_agent", prompt=prompt) as span:
        # Check for mock mode
        if os.environ.get("MOCK_AGENT_CLI") == "true":
            logger.info(f"MOCK_AGENT_CLI is enabled. Returning mock response for Codex prompt: {prompt[:50]}...")
            span.set_attribute("mock", True)
            return f"Mock Codex Output: {prompt}"

        # Construct the command: codex --no-alt-screen -a never exec "prompt"
        # We use shlex.quote to safely escape the prompt for the shell if needed,
        # but subprocess.run with a list is safer and preferred.
        
        cmd = ["codex", "--no-alt-screen", "-a", "never", "exec", prompt]
        span.set_attribute("command", str(cmd))
        
        try:
            logger.info(f"Invoking Codex Agent with prompt: {prompt[:50]}...")
            # running synchronously since these are CLI tools that might block
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120 # 2 minute timeout
            )
            
            span.set_attribute("returncode", result.returncode)
            
            if result.returncode != 0:
                error_msg = f"Codex agent failed with code {result.returncode}.\nStderr: {result.stderr}"
                logger.error(error_msg)
                span.record_exception(Exception(error_msg))
                return error_msg
                
            return result.stdout
            
        except subprocess.TimeoutExpired:
            logger.error("Codex agent timed out.")
            span.record_exception(Exception("Timeout"))
            return "Error: Codex agent timed out after 120 seconds."
        except Exception as e:
            logger.exception(f"Failed to run Codex agent: {e}")
            span.record_exception(e)
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
    with logfire.span("run_claude_agent", prompt=prompt) as span:
        # Check for mock mode
        if os.environ.get("MOCK_AGENT_CLI") == "true":
            logger.info(f"MOCK_AGENT_CLI is enabled. Returning mock response for Claude prompt: {prompt[:50]}...")
            span.set_attribute("mock", True)
            return f"Mock Claude Output: {prompt}"

        # Construct the command: claude -p "prompt"
        cmd = ["claude", "-p", prompt]
        span.set_attribute("command", str(cmd))
        
        try:
            logger.info(f"Invoking Claude Agent with prompt: {prompt[:50]}...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120 # 2 minute timeout
            )
            
            span.set_attribute("returncode", result.returncode)
            
            if result.returncode != 0:
                error_msg = f"Claude agent failed with code {result.returncode}.\nStderr: {result.stderr}"
                logger.error(error_msg)
                span.record_exception(Exception(error_msg))
                return error_msg
                
            return result.stdout

        except subprocess.TimeoutExpired:
            logger.error("Claude agent timed out.")
            span.record_exception(Exception("Timeout"))
            return "Error: Claude agent timed out after 120 seconds."
        except Exception as e:
            logger.exception(f"Failed to run Claude agent: {e}")
            span.record_exception(e)
            return f"Error executing Claude agent: {str(e)}"
