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
from app.runners.evaluators import (
    EvaluationResult,
    EvaluatorRegistry,
    FeedbackMemory,
    create_default_registry,
)
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
    _evaluator_registry: EvaluatorRegistry | None = None

    @classmethod
    def get_evaluator_registry(cls) -> EvaluatorRegistry:
        """Get or create the evaluator registry."""
        if cls._evaluator_registry is None:
            cls._evaluator_registry = create_default_registry()
        return cls._evaluator_registry

    @classmethod
    async def evaluate_phase_output(
        cls,
        phase: str,
        output: str,
        context: dict,
        deterministic_only: bool = False,
    ) -> list[EvaluationResult]:
        """Evaluate phase output using registered evaluators.

        Args:
            phase: Name of the phase (e.g., "coding", "verification")
            output: The phase output to evaluate
            context: Evaluation context (workspace_ref, goal, etc.)
            deterministic_only: If True, skip LLM-based evaluators

        Returns:
            List of EvaluationResult from all applicable evaluators
        """
        registry = cls.get_evaluator_registry()

        if deterministic_only:
            evaluators = registry.get_deterministic_evaluators(phase)
        else:
            evaluators = registry.get_evaluators(phase)

        results = []
        for evaluator in evaluators:
            try:
                result = await evaluator.evaluate(phase, output, context)
                results.append(result)

                logger.info(
                    f"Evaluator {evaluator.name} for phase {phase}: "
                    f"passed={result.passed}, score={result.score:.2f}"
                )
            except Exception as e:
                logger.error(f"Evaluator {evaluator.name} failed: {e}")
                # Don't block on evaluator failures
                continue

        return results

    @classmethod
    async def run_phase_with_evaluation(
        cls,
        phase: str,
        sprint_id: UUID,
        workspace_ref: str,
        goal: str,
        prompt: str,
        agent_tdd_service: AgentTddService,
        tracker: WorkflowTracker,
        broadcast_fn,
        emit_phase_started,
        emit_phase_completed,
        emit_phase_failed,
        max_retries: int = 3,
    ) -> tuple[bool, str, list[EvaluationResult]]:
        """Run a phase with evaluation and retry logic.

        Args:
            phase: Phase name
            sprint_id: Sprint ID
            workspace_ref: Workspace reference
            goal: Sprint goal
            prompt: Base prompt for the phase
            agent_tdd_service: Service for agent execution
            tracker: Workflow tracker
            broadcast_fn: Function to broadcast status updates
            emit_phase_started: Function to emit phase started events
            emit_phase_completed: Function to emit phase completed events
            emit_phase_failed: Function to emit phase failed events
            max_retries: Maximum retry attempts

        Returns:
            Tuple of (success: bool, output: str, evaluations: list[EvaluationResult])
        """
        feedback_memory = FeedbackMemory(
            sprint_id=sprint_id,
            phase=phase,
            original_goal=goal,
            max_attempts=max_retries,
        )

        all_evaluations: list[EvaluationResult] = []

        for attempt in range(max_retries):
            logger.info(f"Phase {phase} attempt {attempt + 1}/{max_retries}")

            # Build prompt with feedback from previous attempts
            if attempt > 0:
                feedback_summary = feedback_memory.get_summary_for_prompt()
                optimized_prompt = f"{feedback_summary}\n\n{prompt}"
            else:
                optimized_prompt = prompt

            # Emit phase started
            await emit_phase_started(
                phase,
                attempt=attempt + 1,
                details=f"Starting {phase} attempt {attempt + 1}",
            )

            # Execute phase
            result = await agent_tdd_service.execute(
                AgentTddRunCreate(
                    message=optimized_prompt,
                    workspace_ref=workspace_ref,
                    metadata={
                        "sprint_id": str(sprint_id),
                        "phase": phase,
                        "attempt": attempt,
                    },
                ),
                user_id=None,
            )

            # Get output
            output = ""
            if result.decision and result.decision.candidate_id:
                for c in result.candidates:
                    if c.id == result.decision.candidate_id:
                        output = c.output or ""
                        break
            elif result.candidates:
                output = result.candidates[0].output or ""

            # Evaluate output (deterministic only for speed)
            eval_results = await cls.evaluate_phase_output(
                phase=phase,
                output=output,
                context={
                    "workspace_ref": workspace_ref,
                    "goal": goal,
                    "attempt": attempt,
                },
                deterministic_only=True,
            )
            all_evaluations.extend(eval_results)

            # Record attempt
            feedback_memory.add_attempt(
                phase_output=output,
                evaluation_results=eval_results,
                optimization_prompt=optimized_prompt if attempt > 0 else None,
            )

            # Check if all evaluations passed
            all_passed = all(e.passed for e in eval_results) if eval_results else True

            if all_passed:
                logger.info(f"Phase {phase} passed on attempt {attempt + 1}")

                # Record evaluation in tracker
                await tracker.record_event(
                    event_type="evaluation_passed",
                    phase=phase,
                    metadata={
                        "attempt": attempt + 1,
                        "evaluations": [e.model_dump() for e in eval_results],
                    },
                )

                await emit_phase_completed(
                    phase,
                    details=f"Phase {phase} completed successfully",
                )

                return True, output, all_evaluations

            # Log failed evaluations
            failed_evals = [e for e in eval_results if not e.passed]
            for eval_result in failed_evals:
                logger.warning(
                    f"Evaluation failed: {eval_result.evaluator_name} - {eval_result.feedback}"
                )

            # Record failure
            await tracker.record_event(
                event_type="evaluation_failed",
                phase=phase,
                metadata={
                    "attempt": attempt + 1,
                    "evaluations": [e.model_dump() for e in eval_results],
                    "will_retry": feedback_memory.can_retry,
                },
            )

            if not feedback_memory.can_retry:
                break

            await emit_phase_failed(
                phase,
                details=f"Evaluation failed on attempt {attempt + 1}. Retrying...",
                attempt=attempt + 1,
            )
            await broadcast_fn(
                "active",
                phase,
                f"Evaluation failed on attempt {attempt + 1}. Retrying...",
            )

        # All retries exhausted
        feedback_memory.escalate(
            f"Phase {phase} failed after {max_retries} attempts"
        )

        await tracker.record_event(
            event_type="phase_escalated",
            phase=phase,
            metadata={
                "reason": feedback_memory.escalation_reason,
                "attempts": feedback_memory.to_dict(),
            },
        )

        return False, output, all_evaluations

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
                    f"INSTRUCTIONS:\n"
                    f"1. Analyze the requirements carefully.\n"
                    f"2. Create 'implementation_plan.md' using `fs_write_file` with:\n"
                    f"   - A list of ALL files to be created (with full paths)\n"
                    f"   - Package/module structure if applicable\n"
                    f"   - Step-by-step implementation order\n"
                    f"   - Key functions/classes for each file\n"
                    f"3. Use `fs_write_file` to create the implementation_plan.md file.\n"
                    f"4. Return 'Discovery Complete' when done."
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
                            provider=candidate.provider or "unknown",
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
                        f"SPRINT GOAL: {goal[:500]}{'...' if len(goal) > 500 else ''}\n\n"
                        f"CRITICAL INSTRUCTIONS:\n"
                        f"1. Read 'implementation_plan.md' using `fs_read_file` to see the file list.\n"
                        f"2. Create ALL files listed in the plan using `fs_write_file`.\n"
                        f"3. For multi-file projects:\n"
                        f"   - Create package directories (e.g., 'todo/__init__.py')\n"
                        f"   - Create each module file with complete implementation\n"
                        f"   - Include `__main__.py` if the plan calls for it\n"
                        f"4. Use `fs_list_dir` to verify all files were created.\n"
                        f"5. Return 'Coding Complete' ONLY after ALL planned files exist."
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
                                provider=candidate.provider or "unknown",
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

                    # Phase 3: Verification with Evaluator Integration
                    verification_start_time = time.monotonic()
                    await tracker.start_phase(
                        f"verification_{attempt + 1}",
                        input_data={"attempt": attempt + 1},
                    )

                    # Initialize feedback memory for this verification cycle
                    if attempt == 0:
                        feedback_memory = FeedbackMemory(
                            sprint_id=sprint_id,
                            phase="verification",
                            original_goal=goal,
                            max_attempts=cls.MAX_RETRIES,
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

                    # Build verification prompt with feedback from previous attempts
                    base_verification_prompt = (
                        f"Phase 3: Verification (Attempt {attempt + 1})\n"
                        f"SPRINT GOAL: {goal[:300]}{'...' if len(goal) > 300 else ''}\n\n"
                        f"VERIFICATION STEPS:\n"
                        f"1. Use `fs_list_dir` to see all created files.\n"
                        f"2. Read 'implementation_plan.md' to check file list against created files.\n"
                        f"3. For CLI tools: Create a test script that exercises the main functionality.\n"
                        f"4. For packages: Verify the package can be imported and run.\n"
                        f"5. Use `run_tests()` to execute any test files in the workspace.\n"
                        f"6. CRITICAL: Return 'VERIFICATION_SUCCESS' only if the code works correctly.\n"
                        f"7. Return 'VERIFICATION_FAILURE' with details if anything fails."
                    )

                    # Add feedback from previous attempts if available
                    feedback_summary = feedback_memory.get_summary_for_prompt()
                    if feedback_summary:
                        verification_prompt = f"{feedback_summary}\n\n{base_verification_prompt}"
                    else:
                        verification_prompt = base_verification_prompt

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

                    agent_verification_success = "VERIFICATION_SUCCESS" in output

                    # Run evaluators on the workspace (deterministic only for speed)
                    eval_results = await cls.evaluate_phase_output(
                        phase="verification",
                        output=output,
                        context={
                            "workspace_ref": workspace_ref,
                            "goal": goal,
                            "attempt": attempt,
                        },
                        deterministic_only=True,
                    )

                    # Check if all evaluators passed
                    evaluators_passed = all(e.passed for e in eval_results) if eval_results else True

                    # Both agent AND evaluators must pass
                    verification_success = agent_verification_success and evaluators_passed

                    # Record attempt in feedback memory
                    feedback_memory.add_attempt(
                        phase_output=output,
                        evaluation_results=eval_results,
                    )

                    # Log evaluation results
                    for eval_result in eval_results:
                        if eval_result.passed:
                            logger.info(
                                f"Evaluator {eval_result.evaluator_name}: PASSED "
                                f"(score={eval_result.score:.2f})"
                            )
                        else:
                            logger.warning(
                                f"Evaluator {eval_result.evaluator_name}: FAILED - "
                                f"{eval_result.feedback}"
                            )

                    verification_duration_ms = int(
                        (time.monotonic() - verification_start_time) * 1000
                    )

                    # Record evaluation results in tracker
                    await tracker.record_event(
                        event_type="evaluation_completed",
                        phase=f"verification_{attempt + 1}",
                        metadata={
                            "agent_success": agent_verification_success,
                            "evaluators_passed": evaluators_passed,
                            "evaluations": [e.model_dump() for e in eval_results],
                        },
                    )

                    await tracker.end_phase(
                        f"verification_{attempt + 1}",
                        status="completed" if verification_success else "failed",
                        output_data={
                            "success": verification_success,
                            "agent_success": agent_verification_success,
                            "evaluators_passed": evaluators_passed,
                            "output": output[:500],
                        },
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
                            output={
                                "success": True,
                                "evaluations": [
                                    {"name": e.evaluator_name, "passed": e.passed, "score": e.score}
                                    for e in eval_results
                                ],
                            },
                            details="Verification and all evaluators passed",
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

                    # Build failure message
                    failure_reasons = []
                    if not agent_verification_success:
                        failure_reasons.append("Agent verification failed")
                    for eval_result in eval_results:
                        if not eval_result.passed:
                            failure_reasons.append(
                                f"{eval_result.evaluator_name}: {eval_result.feedback}"
                            )

                    failure_message = "; ".join(failure_reasons[:3])
                    logger.warning(f"Verification Failed: {failure_message}. Retrying...")

                    # Emit phase.failed event
                    await emit_phase_failed(
                        "verification",
                        details=failure_message[:200],
                        attempt=attempt + 1,
                    )
                    # Legacy event
                    await broadcast_status(
                        "active",
                        "verification",
                        f"Verification failed: {failure_message[:100]}... Retrying.",
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
