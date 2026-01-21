"""Phase runner for automated sprint execution."""

import asyncio
import logging
from uuid import UUID
import json

from app.db.session import get_db_context
from app.services.sprint import SprintService
from app.services.agent_tdd import AgentTddService
from app.schemas.agent_tdd import AgentTddRunCreate
from app.schemas.sprint import SprintUpdate
from app.db.models.sprint import SprintStatus
from app.api.routes.v1.ws import manager

logger = logging.getLogger(__name__)


class PhaseRunner:
    """Orchestrates the automated software development lifecycle phases."""

    MAX_RETRIES = 3

    @classmethod
    async def start(cls, sprint_id: UUID) -> None:
        """Start the phase runner for a sprint as a background task.

        Args:
            sprint_id: The ID of the sprint to process.
        """
        # Wait for transaction to commit
        await asyncio.sleep(1)
        
        logger.info(f"Starting PhaseRunner for sprint {sprint_id}")
        
        room = str(sprint_id)
        async def broadcast_status(status: str, phase: str | None = None, details: str | None = None):
            await manager.broadcast_to_room(room, json.dumps({
                "type": "sprint_update",
                "sprint_id": room,
                "status": status,
                "phase": phase,
                "details": details
            }))

        async with get_db_context() as db:
            sprint_service = SprintService(db)
            agent_tdd_service = AgentTddService(db)

            try:
                # 1. Fetch Sprint Context
                sprint = await sprint_service.get_by_id(sprint_id)
                logger.info(f"Loaded sprint: {sprint.name}")
                goal = sprint.goal or sprint.name
                
                # Update status to ACTIVE
                await sprint_service.update(sprint_id, SprintUpdate(status=SprintStatus.ACTIVE))
                await db.commit()
                
                await broadcast_status("active", "init", f"Starting sprint: {sprint.name}")

                # --- Phase 1: Discovery ---
                logger.info("Starting Phase 1: Discovery")
                await broadcast_status("active", "discovery", "Analyzing requirements and creating implementation plan...")
                workspace_ref = None
                
                discovery_prompt = (
                    f"Perform Discovery and Planning for the following Sprint Goal:\n"
                    f"'{goal}'\n\n"
                    f"1. Analyze the requirements.\n"
                    f"2. Create a file named 'implementation_plan.md' in the workspace.\n"
                    f"3. Return 'Discovery Complete' when done."
                )
                
                result_p1 = await agent_tdd_service.execute(
                    AgentTddRunCreate(
                        message=discovery_prompt,
                        metadata={
                            "sprint_id": str(sprint.id), 
                            "phase": "discovery",
                            "agent_type": "sprint"
                        }
                    ),
                    user_id=None
                )
                workspace_ref = result_p1.run.workspace_ref
                logger.info(f"Phase 1 Complete. Workspace: {workspace_ref}")
                await broadcast_status("active", "discovery", "Discovery complete. Implementation plan created.")

                # --- Loop: Phase 2 (Code) & Phase 3 (Verify) ---
                for attempt in range(cls.MAX_RETRIES):
                    logger.info(f"Starting Coding/Verification Cycle (Attempt {attempt + 1}/{cls.MAX_RETRIES})")
                    await broadcast_status("active", "coding", f"Starting implementation (Attempt {attempt + 1})")

                    # Phase 2: Coding
                    coding_prompt = (
                        f"Phase 2: Coding (Attempt {attempt + 1})\n"
                        f"1. A file named 'implementation_plan.md' exists in the CURRENT directory.\n"
                        f"2. Read it using `fs_read_file(path='implementation_plan.md')`.\n"
                        f"3. Implement the solution described in the plan.\n"
                        f"4. Create necessary files in the CURRENT directory (do not use subdirectories unless specified).\n"
                        f"5. Return 'Coding Complete' when done."
                    )
                    
                    result_p2 = await agent_tdd_service.execute(
                        AgentTddRunCreate(
                            message=coding_prompt,
                            workspace_ref=workspace_ref,
                            metadata={
                                "sprint_id": str(sprint.id), 
                                "phase": "coding", 
                                "attempt": attempt,
                                "agent_type": "sprint"
                            }
                        ),
                        user_id=None
                    )
                    
                    await broadcast_status("active", "verification", f"Implementation complete. Verifying... (Attempt {attempt + 1})")
                    
                    # Phase 3: Verification
                    verification_prompt = (
                        f"Phase 3: Verification (Attempt {attempt + 1})\n"
                        f"1. Verify the implementation works as expected.\n"
                        f"2. If it is a script, run it. If it is a library, write and run a test script.\n"
                        f"3. Use the 'run_tests' tool if appropriate.\n"
                        f"4. CRITICAL: If verification SUCCEEDS, return the exact string 'VERIFICATION_SUCCESS'.\n"
                        f"5. If verification FAILS, return 'VERIFICATION_FAILURE' and explain what to fix."
                    )

                    result_p3 = await agent_tdd_service.execute(
                        AgentTddRunCreate(
                            message=verification_prompt,
                            workspace_ref=workspace_ref,
                            metadata={
                                "sprint_id": str(sprint.id), 
                                "phase": "verification", 
                                "attempt": attempt,
                                "agent_type": "sprint"
                            }
                        ),
                        user_id=None
                    )
                    
                    # Check Decision
                    output = ""
                    if result_p3.decision and result_p3.decision.candidate_id:
                        for c in result_p3.candidates:
                            if c.id == result_p3.decision.candidate_id:
                                output = c.output or ""
                                break
                    elif result_p3.candidates:
                        output = result_p3.candidates[0].output or ""

                    if "VERIFICATION_SUCCESS" in output:
                        logger.info("Sprint Completed Successfully: Validation Passed.")
                        await sprint_service.update(sprint_id, SprintUpdate(status=SprintStatus.COMPLETED))
                        await db.commit()
                        await broadcast_status("completed", "verification", "Sprint successfully validated and completed!")
                        return

                    logger.warning(f"Verification Failed: {output}. Retrying...")
                    await broadcast_status("active", "verification", f"Verification failed: {output[:100]}... Retrying.")

                logger.error(f"Sprint Failed: Max retries ({cls.MAX_RETRIES}) reached.")
                await broadcast_status("failed", "error", "Sprint failed after max retries.")

            except Exception as e:
                logger.error(f"PhaseRunner failed for sprint {sprint_id}: {e}", exc_info=True)
                await broadcast_status("failed", "error", f"PhaseRunner error: {str(e)}")