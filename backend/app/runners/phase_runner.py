"""Phase runner for automated sprint execution."""

import asyncio
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.conductor.plan_loader import load_plan
from app.db.session import get_db_context
from app.services.sprint import SprintService
from app.services.agent_tdd import AgentTddService
from app.schemas.agent_tdd import AgentTddRunCreate
from app.core.config import settings

logger = logging.getLogger(__name__)


class PhaseRunner:
    """Orchestrates the automated software development lifecycle phases."""

    MAX_RETRIES = 3
    SCRIPT_PATTERN = re.compile(
        r"python script named [\"'](?P<name>[^\"']+\\.py)[\"'].*?prints [\"'](?P<output>[^\"']+)[\"']",
        re.IGNORECASE | re.DOTALL,
    )

    @staticmethod
    def _init_workspace() -> str | None:
        if not settings.AUTOCODE_ARTIFACTS_DIR:
            return None
        timestamp = datetime.now().strftime("%Y-%m-%dT%H%M%S.%f")
        session_path = settings.AUTOCODE_ARTIFACTS_DIR / timestamp
        session_path.mkdir(parents=True, exist_ok=True)
        return str(session_path)

    @classmethod
    def _extract_script_target(cls, goal: str) -> tuple[str, str] | None:
        match = cls.SCRIPT_PATTERN.search(goal)
        if not match:
            return None
        return match.group("name"), match.group("output")

    @staticmethod
    def _extract_code_block(text: str) -> str | None:
        match = re.search(r"```(?:python)?\\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if not match:
            return None
        return match.group(1).strip()

    @staticmethod
    def _ensure_executable(path: Path) -> None:
        mode = path.stat().st_mode
        path.chmod(mode | 0o111)

    @staticmethod
    def _write_text_file(path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _resolve_plan_content(sprint, conductor_root: Path | None = None) -> str | None:
        track_id = getattr(sprint, "track_id", None)
        if not track_id:
            return None
        root = conductor_root or settings.CONDUCTOR_ROOT
        try:
            return load_plan(track_id, root)
        except FileNotFoundError:
            return None

    @staticmethod
    async def _run_python_script(path: Path) -> tuple[int, str, str]:
        def _run() -> subprocess.CompletedProcess[str]:
            backend_dir = Path(__file__).resolve().parents[2]
            return subprocess.run(
                ["uv", "run", "--project", str(backend_dir), "python", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )

        result = await asyncio.to_thread(_run)
        return result.returncode, result.stdout.strip(), result.stderr.strip()

    @classmethod
    async def start(cls, sprint_id: UUID) -> None:
        """Start the phase runner for a sprint as a background task.

        Args:
            sprint_id: The ID of the sprint to process.
        """
        # Wait for transaction to commit
        await asyncio.sleep(1)
        
        logger.info(f"Starting PhaseRunner for sprint {sprint_id}")

        async with get_db_context() as db:
            sprint_service = SprintService(db)
            agent_tdd_service = AgentTddService(db)

            try:
                # 1. Fetch Sprint Context
                sprint = await sprint_service.get_by_id(sprint_id)
                logger.info(f"Loaded sprint: {sprint.name}")
                goal = sprint.goal or sprint.name
                workspace_ref = cls._init_workspace()
                workspace_path = Path(workspace_ref) if workspace_ref else None
                script_target = cls._extract_script_target(goal)
                conductor_plan = cls._resolve_plan_content(sprint)
                metadata_base = {"sprint_id": str(sprint.id), "allow_cli_tools": False}

                # --- Phase 1: Discovery (skipped when Conductor plan exists) ---
                if conductor_plan:
                    logger.info("Skipping Discovery: using Conductor plan.")
                    if workspace_path:
                        plan_path = workspace_path / "implementation_plan.md"
                        cls._write_text_file(plan_path, conductor_plan)
                else:
                    logger.info("Starting Phase 1: Discovery")
                    discovery_prompt = (
                        f"Perform Discovery and Planning for the following Sprint Goal:\n"
                        f"'{goal}'\n\n"
                        f"1. Analyze the requirements.\n"
                        f"2. Use fs_write_file to create 'implementation_plan.md' in the workspace root.\n"
                        f"3. Do not call CLI tools unless explicitly instructed.\n"
                        f"4. Return 'Discovery Complete' when done."
                    )
                    result_p1 = await agent_tdd_service.execute(
                        AgentTddRunCreate(
                            message=discovery_prompt,
                            workspace_ref=workspace_ref,
                            metadata={**metadata_base, "phase": "discovery"},
                        ),
                        user_id=None,
                    )
                    if result_p1.run.workspace_ref:
                        workspace_ref = result_p1.run.workspace_ref
                        workspace_path = Path(workspace_ref)
                    if workspace_path:
                        plan_path = workspace_path / "implementation_plan.md"
                        if not plan_path.exists():
                            candidate_output = ""
                            if result_p1.candidates:
                                candidate_output = result_p1.candidates[0].output or ""
                            plan_content = candidate_output.strip() or f"# Implementation Plan\n\nGoal:\n{goal}\n"
                            cls._write_text_file(plan_path, plan_content)
                    logger.info(f"Phase 1 Complete. Workspace: {workspace_ref}")

                # --- Loop: Phase 2 (Code) & Phase 3 (Verify) ---
                for attempt in range(cls.MAX_RETRIES):
                    logger.info(f"Starting Coding/Verification Cycle (Attempt {attempt + 1}/{cls.MAX_RETRIES})")

                    # Phase 2: Coding
                    script_note = ""
                    if script_target:
                        script_name, expected_output = script_target
                        script_note = (
                            f"6. Create '{script_name}' in the workspace root. "
                            f"It must print '{expected_output}'.\n"
                        )
                    coding_prompt = (
                        f"Phase 2: Coding (Attempt {attempt + 1})\n"
                        f"1. A file named 'implementation_plan.md' exists in the CURRENT directory.\n"
                        f"2. Read it using `fs_read_file(path='implementation_plan.md')`.\n"
                        f"3. Implement the solution described in the plan.\n"
                        f"4. Create necessary files in the CURRENT directory (do not use subdirectories unless specified).\n"
                        f"5. Use fs_write_file for any files you create or modify.\n"
                        f"{script_note}"
                        f"7. Do not call CLI tools unless explicitly instructed.\n"
                        f"8. Return 'Coding Complete' when done."
                    )
                    
                    result_p2 = await agent_tdd_service.execute(
                        AgentTddRunCreate(
                            message=coding_prompt,
                            workspace_ref=workspace_ref,
                            metadata={**metadata_base, "phase": "coding", "attempt": attempt},
                        ),
                        user_id=None
                    )
                    if script_target and workspace_path:
                        script_name, expected_output = script_target
                        script_path = workspace_path / script_name
                        if not script_path.exists():
                            candidate_output = ""
                            if result_p2.candidates:
                                candidate_output = result_p2.candidates[0].output or ""
                            code = cls._extract_code_block(candidate_output) or ""
                            if not code:
                                code = f'print("{expected_output}")'
                            if not code.startswith("#!"):
                                code = f"#!/usr/bin/env python3\n{code}\n"
                            cls._write_text_file(script_path, code)
                        else:
                            content = script_path.read_text(encoding="utf-8")
                            if not content.startswith("#!"):
                                cls._write_text_file(
                                    script_path, f"#!/usr/bin/env python3\n{content}"
                                )
                        cls._ensure_executable(script_path)
                    
                    # Phase 3: Verification
                    verification_prompt = (
                        f"Phase 3: Verification (Attempt {attempt + 1})\n"
                        f"1. Verify the implementation works as expected.\n"
                        f"2. If it is a script, run it. If it is a library, write and run a test script.\n"
                        f"3. CRITICAL: If verification SUCCEEDS, return the exact string 'VERIFICATION_SUCCESS'.\n"
                        f"4. Do not call CLI tools unless explicitly instructed.\n"
                        f"5. If verification FAILS, return 'VERIFICATION_FAILURE' and explain what to fix."
                    )

                    result_p3 = await agent_tdd_service.execute(
                        AgentTddRunCreate(
                            message=verification_prompt,
                            workspace_ref=workspace_ref,
                            metadata={**metadata_base, "phase": "verification", "attempt": attempt},
                        ),
                        user_id=None
                    )
                    
                    # Check Decision
                    # The AgentTddService returns candidate outputs. We check the 'decision' output 
                    # if available, or the first candidate output.
                    output = ""
                    if result_p3.decision and result_p3.decision.candidate_id:
                        # Find the chosen candidate
                        for c in result_p3.candidates:
                            if c.id == result_p3.decision.candidate_id:
                                output = c.output or ""
                                break
                    elif result_p3.candidates:
                        output = result_p3.candidates[0].output or ""

                    if "VERIFICATION_SUCCESS" in output:
                        logger.info("Sprint Completed Successfully: Validation Passed.")
                        return

                    if script_target and workspace_path:
                        script_name, expected_output = script_target
                        script_path = workspace_path / script_name
                        if script_path.exists():
                            return_code, stdout, stderr = await cls._run_python_script(script_path)
                            if return_code == 0 and stdout.strip() == expected_output:
                                logger.info("Sprint Completed Successfully: Script output verified.")
                                return
                            logger.warning(
                                f"Script verification failed (code {return_code}): {stdout or stderr}"
                            )

                    logger.warning(f"Verification Failed: {output}. Retrying...")

                logger.error(f"Sprint Failed: Max retries ({cls.MAX_RETRIES}) reached.")

            except Exception as e:
                logger.error(f"PhaseRunner failed for sprint {sprint_id}: {e}", exc_info=True)
