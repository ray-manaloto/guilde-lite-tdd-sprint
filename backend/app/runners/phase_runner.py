"""Phase runner for automated sprint execution."""

import asyncio
import logging
from uuid import UUID

from app.db.session import get_db_context
from app.services.sprint import SprintService
from app.services.agent_tdd import AgentTddService
from app.schemas.agent_tdd import AgentTddRunCreate

logger = logging.getLogger(__name__)


class PhaseRunner:
    """Orchestrates the automated software development lifecycle phases."""

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

                # 2. Phase 1: Discovery / Initial Plan
                # For Phase 1 validation, we will trigger a simple Agent TDD run
                # that takes the Sprint Goal and creates an implementation plan.
                
                # If goal is missing, fallback to name
                goal = sprint.goal or sprint.name

                task_prompt = (
                    f"Perform Discovery and Planning for the following Sprint Goal:\n"
                    f"'{goal}'\n\n"
                    f"1. Analyze the requirements.\n"
                    f"2. Create a file named 'implementation_plan.md' in the workspace.\n"
                    f"3. Return 'Discovery Complete' when done."
                )

                logger.info("Triggering AgentTDDService for Discovery Phase...")
                run_create = AgentTddRunCreate(
                    message=task_prompt,
                    metadata={
                        "sprint_id": str(sprint.id),
                        "phase": "discovery"
                    }
                )

                # We pass user_id=None for system-triggered runs
                result = await agent_tdd_service.execute(run_create, user_id=None)
                
                logger.info(f"PhaseRunner completed successfully. Status: {result.run.status}")

            except Exception as e:
                logger.error(f"PhaseRunner failed for sprint {sprint_id}: {e}", exc_info=True)
