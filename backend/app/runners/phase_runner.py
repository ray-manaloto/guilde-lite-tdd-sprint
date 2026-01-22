"""Phase runner for automated sprint execution."""

import asyncio
import logging
import time
from uuid import UUID

from app.api.routes.v1.ws import manager
from app.core.config import settings
from app.core.websocket_events import (
    CandidateData,
    CandidateGeneratedEvent,
    CandidateStartedEvent,
    JudgeDecidedEvent,
    JudgeDecisionData,
    JudgeStartedEvent,
    PhaseCompletedEvent,
    PhaseFailedEvent,
    PhaseStartedEvent,
    WorkflowStatusEvent,
)
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
            """Broadcast legacy sprint_update event for backwards compatibility."""
            await manager.broadcast_legacy_status(room, status, phase, details)

        async def emit_workflow_status(
            status: str, phase: str | None = None, details: str | None = None
        ):
            """Emit new workflow.status event."""
            event = WorkflowStatusEvent.create(
                sprint_id=sprint_id,
                status=status,
                phase=phase,
                details=details,
            )
            await manager.broadcast_event(room, event)

        async def emit_phase_started(
            phase: str, attempt: int | None = None, details: str | None = None
        ):
            """Emit phase.started event."""
            event = PhaseStartedEvent.create(
                sprint_id=sprint_id,
                phase=phase,
                attempt=attempt,
                details=details,
            )
            await manager.broadcast_event(room, event)

        async def emit_phase_completed(
            phase: str,
            duration_ms: int | None = None,
            output: dict | None = None,
            details: str | None = None,
        ):
            """Emit phase.completed event."""
            event = PhaseCompletedEvent.create(
                sprint_id=sprint_id,
                phase=phase,
                duration_ms=duration_ms,
                output=output,
                details=details,
            )
            await manager.broadcast_event(room, event)

        async def emit_phase_failed(
            phase: str, details: str | None = None, attempt: int | None = None
        ):
            """Emit phase.failed event."""
            event = PhaseFailedEvent.create(
                sprint_id=sprint_id,
                phase=phase,
                details=details,
                attempt=attempt,
            )
            await manager.broadcast_event(room, event)

        async def emit_candidate_started(provider: str, model_name: str | None, phase: str):
            """Emit candidate.started event."""
            event = CandidateStartedEvent.create(
                sprint_id=sprint_id,
                provider=provider,
                model_name=model_name,
                phase=phase,
            )
            await manager.broadcast_event(room, event)

        async def emit_candidate_generated(candidate_data: CandidateData):
            """Emit candidate.generated event."""
            event = CandidateGeneratedEvent.create(
                sprint_id=sprint_id,
                candidate=candidate_data,
            )
            await manager.broadcast_event(room, event)

        async def emit_judge_started(candidate_count: int, phase: str):
            """Emit judge.started event."""
            event = JudgeStartedEvent.create(
                sprint_id=sprint_id,
                candidate_count=candidate_count,
                phase=phase,
            )
            await manager.broadcast_event(room, event)

        async def emit_judge_decided(decision_data: JudgeDecisionData):
            """Emit judge.decided event."""
            event = JudgeDecidedEvent.create(
                sprint_id=sprint_id,
                decision=decision_data,
            )
            await manager.broadcast_event(room, event)

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
                discovery_start_time = time.monotonic()
                await tracker.start_phase(
                    "discovery",
                    model_config={
                        "openai_model": settings.model_for_provider("openai"),
                        "anthropic_model": settings.model_for_provider("anthropic"),
                    },
                    input_data={"goal": goal},
                )
                # Emit new granular events
                await emit_phase_started(
                    "discovery", details="Analyzing requirements and creating implementation plan"
                )
                await emit_workflow_status("active", "discovery", "Starting discovery phase")
                # Emit legacy event for backwards compatibility
                await broadcast_status(
                    "active",
                    "discovery",
                    "Analyzing requirements and creating implementation plan...",
                )

                # Emit candidate started events for expected providers
                await emit_candidate_started(
                    "openai", settings.model_for_provider("openai"), "discovery"
                )
                await emit_candidate_started(
                    "anthropic", settings.model_for_provider("anthropic"), "discovery"
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

                # Record candidates from discovery phase and emit events
                discovery_candidates = []
                for candidate in result_p1.candidates:
                    metrics = candidate.metrics or {}
                    trace_id = metrics.get("trace_id") if isinstance(metrics, dict) else None
                    duration_ms = metrics.get("duration_ms") if isinstance(metrics, dict) else None
                    success = metrics.get("status") == "ok" if isinstance(metrics, dict) else False

                    discovery_candidates.append(
                        {
                            "provider": candidate.provider,
                            "model": candidate.model_name,
                            "trace_id": trace_id,
                            "duration_ms": duration_ms,
                            "success": success,
                        }
                    )

                    # Emit candidate.generated event
                    await emit_candidate_generated(
                        CandidateData(
                            candidate_id=str(candidate.id) if candidate.id else None,
                            provider=candidate.provider,
                            model_name=candidate.model_name,
                            agent_name=candidate.agent_name,
                            output=candidate.output[:500] if candidate.output else None,
                            duration_ms=duration_ms,
                            trace_id=trace_id,
                            success=success,
                        )
                    )

                await tracker.record_candidates("discovery", discovery_candidates)

                # Record judge decision if available and emit event
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
                    # Emit judge.started before decision (candidates were already evaluated)
                    await emit_judge_started(len(result_p1.candidates), "discovery")
                    # Emit judge.decided event
                    await emit_judge_decided(
                        JudgeDecisionData(
                            winner_candidate_id=str(result_p1.decision.candidate_id)
                            if result_p1.decision.candidate_id
                            else None,
                            winner_model=result_p1.decision.model_name,
                            score=result_p1.decision.score,
                            rationale=result_p1.decision.rationale,
                            model_name=result_p1.decision.model_name,
                            trace_id=result_p1.decision.trace_id,
                        )
                    )

                discovery_duration_ms = int((time.monotonic() - discovery_start_time) * 1000)
                await tracker.end_phase(
                    "discovery",
                    output_data={"workspace_ref": workspace_ref},
                )
                logger.info(f"Phase 1 Complete. Workspace: {workspace_ref}")
                # Emit new phase.completed event
                await emit_phase_completed(
                    "discovery",
                    duration_ms=discovery_duration_ms,
                    output={"workspace_ref": workspace_ref},
                    details="Implementation plan created",
                )
                # Legacy event
                await broadcast_status(
                    "active", "discovery", "Discovery complete. Implementation plan created."
                )

                # --- Loop: Phase 2 (Code) & Phase 3 (Verify) ---
                for attempt in range(cls.MAX_RETRIES):
                    logger.info(
                        f"Starting Coding/Verification Cycle (Attempt {attempt + 1}/{cls.MAX_RETRIES})"
                    )

                    # Phase 2: Coding
                    coding_start_time = time.monotonic()
                    await tracker.start_phase(
                        f"coding_{attempt + 1}",
                        input_data={"attempt": attempt + 1, "workspace_ref": workspace_ref},
                    )
                    # Emit new granular events
                    await emit_phase_started(
                        "coding",
                        attempt=attempt + 1,
                        details=f"Starting implementation attempt {attempt + 1}",
                    )
                    await emit_workflow_status(
                        "active", "coding", f"Implementation attempt {attempt + 1}"
                    )
                    # Legacy event
                    await broadcast_status(
                        "active", "coding", f"Starting implementation (Attempt {attempt + 1})"
                    )
                    # Emit candidate started events
                    await emit_candidate_started(
                        "openai", settings.model_for_provider("openai"), "coding"
                    )
                    await emit_candidate_started(
                        "anthropic", settings.model_for_provider("anthropic"), "coding"
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

                    # Record coding candidates and emit events
                    coding_candidates = []
                    for candidate in result_p2.candidates:
                        metrics = candidate.metrics or {}
                        trace_id = metrics.get("trace_id") if isinstance(metrics, dict) else None
                        duration_ms = (
                            metrics.get("duration_ms") if isinstance(metrics, dict) else None
                        )
                        success = (
                            metrics.get("status") == "ok" if isinstance(metrics, dict) else False
                        )

                        coding_candidates.append(
                            {
                                "provider": candidate.provider,
                                "model": candidate.model_name,
                                "trace_id": trace_id,
                                "duration_ms": duration_ms,
                                "success": success,
                            }
                        )

                        # Emit candidate.generated event
                        await emit_candidate_generated(
                            CandidateData(
                                candidate_id=str(candidate.id) if candidate.id else None,
                                provider=candidate.provider,
                                model_name=candidate.model_name,
                                agent_name=candidate.agent_name,
                                output=candidate.output[:500] if candidate.output else None,
                                duration_ms=duration_ms,
                                trace_id=trace_id,
                                success=success,
                            )
                        )

                    await tracker.record_candidates(f"coding_{attempt + 1}", coding_candidates)

                    coding_duration_ms = int((time.monotonic() - coding_start_time) * 1000)
                    await tracker.end_phase(f"coding_{attempt + 1}")
                    # Emit phase.completed for coding
                    await emit_phase_completed(
                        "coding",
                        duration_ms=coding_duration_ms,
                        details=f"Coding attempt {attempt + 1} complete",
                    )

                    # Phase 3: Verification
                    verification_start_time = time.monotonic()
                    await tracker.start_phase(
                        f"verification_{attempt + 1}",
                        input_data={"attempt": attempt + 1},
                    )
                    # Emit new granular events
                    await emit_phase_started(
                        "verification",
                        attempt=attempt + 1,
                        details=f"Verifying implementation attempt {attempt + 1}",
                    )
                    await emit_workflow_status(
                        "active", "verification", f"Verification attempt {attempt + 1}"
                    )
                    # Legacy event
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

                    verification_duration_ms = int(
                        (time.monotonic() - verification_start_time) * 1000
                    )
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

                        # Emit new granular events
                        await emit_phase_completed(
                            "verification",
                            duration_ms=verification_duration_ms,
                            output={"success": True},
                            details="Verification passed",
                        )
                        await emit_workflow_status(
                            "completed", "verification", "Sprint successfully completed"
                        )
                        # Legacy event
                        await broadcast_status(
                            "completed",
                            "verification",
                            "Sprint successfully validated and completed!",
                        )
                        return

                    logger.warning(f"Verification Failed: {output}. Retrying...")
                    # Emit phase.failed event
                    await emit_phase_failed(
                        "verification",
                        details=output[:200] if output else "Verification failed",
                        attempt=attempt + 1,
                    )
                    # Legacy event
                    await broadcast_status(
                        "active",
                        "verification",
                        f"Verification failed: {output[:100]}... Retrying.",
                    )

                logger.error(f"Sprint Failed: Max retries ({cls.MAX_RETRIES}) reached.")
                await tracker.complete_sprint(status="failed")
                # Emit workflow failed event
                await emit_workflow_status(
                    "failed", "error", f"Sprint failed after {cls.MAX_RETRIES} retries"
                )
                # Legacy event
                await broadcast_status("failed", "error", "Sprint failed after max retries.")

            except Exception as e:
                logger.error(f"PhaseRunner failed for sprint {sprint_id}: {e}", exc_info=True)
                # Update sprint status to failed in database
                try:
                    await sprint_service.update(
                        sprint_id, SprintUpdate(status=SprintStatus.FAILED)
                    )
                    await db.commit()
                except Exception as db_error:
                    logger.warning(f"Failed to update sprint status to failed: {db_error}")
                # Try to save timeline on failure
                try:
                    if "tracker" in locals():
                        await tracker.complete_sprint(status="failed")
                except Exception as save_error:
                    logger.warning(f"Failed to save timeline on error: {save_error}")
                # Emit workflow failed event
                await emit_workflow_status("failed", "error", f"PhaseRunner error: {e!s}")
                # Legacy event
                await broadcast_status("failed", "error", f"PhaseRunner error: {e!s}")
