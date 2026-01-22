"""Phase runner for automated sprint execution."""

import asyncio
import json
import logging
from uuid import UUID

from app.api.routes.v1.ws import manager
from app.core.config import settings
from app.db.models.sprint import SprintStatus
from app.db.session import get_db_context
from app.schemas.agent_tdd import AgentTddRunCreate
from app.schemas.sprint import SprintUpdate
from app.services.agent_tdd import AgentTddService
from app.services.spec import SpecService
from app.services.sprint import SprintService
from app.services.workflow_tracker import WorkflowTracker

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

        async def broadcast_status(
            status: str, phase: str | None = None, details: str | None = None
        ):
            await manager.broadcast_to_room(
                room,
                json.dumps(
                    {
                        "type": "sprint_update",
                        "sprint_id": room,
                        "status": status,
                        "phase": phase,
                        "details": details,
                    }
                ),
            )

        async with get_db_context() as db:
            sprint_service = SprintService(db)
            agent_tdd_service = AgentTddService(db)
            spec_service = SpecService(db)

            try:
                # 1. Fetch Sprint Context
                sprint = await sprint_service.get_by_id(sprint_id)
                logger.info(f"Loaded sprint: {sprint.name}")
                goal = sprint.goal or sprint.name

                # Initialize workflow tracker
                tracker = WorkflowTracker(
                    sprint_id=sprint_id,
                    spec_id=sprint.spec_id,
                    artifacts_dir=settings.AUTOCODE_ARTIFACTS_DIR,
                )
                await tracker.start_sprint()

                # Export spec to disk if linked
                if sprint.spec_id:
                    try:
                        await spec_service.export_to_disk(
                            sprint.spec_id,
                            sprint_dir=tracker.base_dir,
                        )
                        await tracker.record_event(
                            event_type="spec_exported",
                            metadata={"spec_id": str(sprint.spec_id)},
                        )
                    except Exception as e:
                        logger.warning(f"Failed to export spec: {e}")

                # Update status to ACTIVE
                await sprint_service.update(sprint_id, SprintUpdate(status=SprintStatus.ACTIVE))

                await broadcast_status("active", "init", f"Starting sprint: {sprint.name}")
                await tracker.record_event(
                    event_type="sprint_activated",
                    state="active",
                )

                # --- Phase 1: Discovery ---
                logger.info("Starting Phase 1: Discovery")
                await tracker.start_phase(
                    "discovery",
                    model_config={
                        "openai_model": settings.model_for_provider("openai"),
                        "anthropic_model": settings.model_for_provider("anthropic"),
                    },
                    input_data={"goal": goal},
                )
                await broadcast_status(
                    "active",
                    "discovery",
                    "Analyzing requirements and creating implementation plan...",
                )
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
                            "agent_type": "sprint",
                        },
                    ),
                    user_id=None,
                )
                workspace_ref = result_p1.run.workspace_ref

                # Record candidates from discovery phase
                discovery_candidates = []
                for candidate in result_p1.candidates:
                    discovery_candidates.append({
                        "provider": candidate.provider,
                        "model": candidate.model_name,
                        "trace_id": candidate.metrics.get("trace_id") if candidate.metrics else None,
                        "duration_ms": candidate.metrics.get("duration_ms") if candidate.metrics else None,
                        "success": candidate.metrics.get("status") == "ok" if candidate.metrics else False,
                    })
                await tracker.record_candidates("discovery", discovery_candidates)

                # Record judge decision if available
                if result_p1.decision:
                    await tracker.record_judge_decision(
                        "discovery",
                        {
                            "winner": result_p1.decision.model_name,
                            "score": result_p1.decision.score,
                            "rationale": result_p1.decision.rationale,
                            "model": result_p1.decision.model_name,
                        },
                    )

                await tracker.end_phase(
                    "discovery",
                    output_data={"workspace_ref": workspace_ref},
                )
                logger.info(f"Phase 1 Complete. Workspace: {workspace_ref}")
                await broadcast_status(
                    "active", "discovery", "Discovery complete. Implementation plan created."
                )

                # --- Loop: Phase 2 (Code) & Phase 3 (Verify) ---
                for attempt in range(cls.MAX_RETRIES):
                    logger.info(
                        f"Starting Coding/Verification Cycle (Attempt {attempt + 1}/{cls.MAX_RETRIES})"
                    )

                    # Phase 2: Coding
                    await tracker.start_phase(
                        f"coding_{attempt + 1}",
                        input_data={"attempt": attempt + 1, "workspace_ref": workspace_ref},
                    )
                    await broadcast_status(
                        "active", "coding", f"Starting implementation (Attempt {attempt + 1})"
                    )

                    coding_prompt = (
                        f"Phase 2: Coding (Attempt {attempt + 1})\n"
                        f"CRITICAL: YOU MUST NOW IMPLEMENT THE CODE.\n"
                        f"1. Read 'implementation_plan.md' using `fs_read_file`.\n"
                        f"2. IMMEDIATELY USE `fs_write_file` to create the python script (e.g., 'hello.py').\n"
                        f"3. You are prohibited from finishing this turn without calling `fs_write_file`.\n"
                        f"4. If you have already created the files, verify them with `fs_list_dir`.\n"
                        f"5. Return 'Coding Complete' ONLY after the files are written to the filesystem."
                    )

                    result_p2 = await agent_tdd_service.execute(
                        AgentTddRunCreate(
                            message=coding_prompt,
                            workspace_ref=workspace_ref,
                            metadata={
                                "sprint_id": str(sprint.id),
                                "phase": "coding",
                                "attempt": attempt,
                                "agent_type": "sprint",
                            },
                        ),
                        user_id=None,
                    )

                    # Record coding candidates
                    coding_candidates = []
                    for candidate in result_p2.candidates:
                        coding_candidates.append({
                            "provider": candidate.provider,
                            "model": candidate.model_name,
                            "trace_id": candidate.metrics.get("trace_id") if candidate.metrics else None,
                            "duration_ms": candidate.metrics.get("duration_ms") if candidate.metrics else None,
                            "success": candidate.metrics.get("status") == "ok" if candidate.metrics else False,
                        })
                    await tracker.record_candidates(f"coding_{attempt + 1}", coding_candidates)

                    await tracker.end_phase(f"coding_{attempt + 1}")

                    # Phase 3: Verification
                    await tracker.start_phase(
                        f"verification_{attempt + 1}",
                        input_data={"attempt": attempt + 1},
                    )
                    await broadcast_status(
                        "active",
                        "verification",
                        f"Implementation complete. Verifying... (Attempt {attempt + 1})",
                    )

                    verification_prompt = (
                        f"Phase 3: Verification (Attempt {attempt + 1})\n"
                        f"1. Verify the implementation works as expected.\n"
                        f"2. If it is a script, run it. If it is a library, write and run a test script.\n"
                        f"3. Use the `run_tests()` tool without arguments to run tests in your CURRENT workspace.\n"
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
                                "agent_type": "sprint",
                            },
                        ),
                        user_id=None,
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

                    verification_success = "VERIFICATION_SUCCESS" in output

                    await tracker.end_phase(
                        f"verification_{attempt + 1}",
                        status="completed" if verification_success else "failed",
                        output_data={"success": verification_success, "output": output[:500]},
                    )

                    if verification_success:
                        logger.info("Sprint Completed Successfully: Validation Passed.")
                        await sprint_service.update(
                            sprint_id, SprintUpdate(status=SprintStatus.COMPLETED)
                        )

                        # Complete workflow tracking
                        await tracker.complete_sprint(status="completed")

                        await broadcast_status(
                            "completed",
                            "verification",
                            "Sprint successfully validated and completed!",
                        )
                        return

                    logger.warning(f"Verification Failed: {output}. Retrying...")
                    await broadcast_status(
                        "active",
                        "verification",
                        f"Verification failed: {output[:100]}... Retrying.",
                    )

                logger.error(f"Sprint Failed: Max retries ({cls.MAX_RETRIES}) reached.")
                await tracker.complete_sprint(status="failed")
                await broadcast_status("failed", "error", "Sprint failed after max retries.")

            except Exception as e:
                logger.error(f"PhaseRunner failed for sprint {sprint_id}: {e}", exc_info=True)
                # Try to save timeline on failure
                try:
                    if "tracker" in locals():
                        await tracker.complete_sprint(status="failed")
                except Exception as save_error:
                    logger.warning(f"Failed to save timeline on error: {save_error}")
                await broadcast_status("failed", "error", f"PhaseRunner error: {e!s}")
