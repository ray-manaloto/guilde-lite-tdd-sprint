"""TDD-style agent runner with multi-provider subagents."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.agents.assistant import AssistantAgent
from app.agents.prompts import JUDGE_SYSTEM_PROMPT
from app.core.config import settings
from app.core.telemetry import telemetry_span
from app.schemas.agent_run import (
    AgentCandidateCreate,
    AgentCheckpointCreate,
    AgentDecisionCreate,
    AgentRunCreate,
    AgentRunUpdate,
)
from app.schemas.agent_tdd import (
    AgentTddRunCreate,
    AgentTddRunResult,
    AgentTddSubagentConfig,
    AgentTddSubagentError,
)
from app.services.agent_run import AgentRunService


@dataclass
class _SubagentResult:
    agent_name: str
    provider: str
    model_name: str
    output: str | None
    tool_calls: dict[str, Any]
    metrics: dict[str, Any]


class AgentTddService:
    """Execute multi-provider TDD runs with checkpointing and telemetry."""

    def __init__(self, db):
        self.db = db
        self.run_service = AgentRunService(db)

    async def execute(
        self,
        data: AgentTddRunCreate,
        *,
        user_id: UUID | None,
    ) -> AgentTddRunResult:
        settings.validate_dual_subagent_settings()
        run = await self._resolve_run(data, user_id=user_id)
        run = await self.run_service.update_run(run.id, AgentRunUpdate(status="running"))

        existing_checkpoints, _ = await self.run_service.list_checkpoints(run.id)
        sequence = existing_checkpoints[-1].sequence + 1 if existing_checkpoints else 0

        subagents = self._resolve_subagents(data.subagents)

        await self.run_service.add_checkpoint(
            run.id,
            AgentCheckpointCreate(
                sequence=sequence,
                label="start",
                state={
                    "input_payload": run.input_payload,
                    "model_config": run.model_config,
                    "subagents": [cfg.model_dump() for cfg in subagents],
                    "metadata": data.metadata,
                },
            ),
        )
        sequence += 1

        subagent_results, subagent_errors = await self._run_subagents(subagents, data)

        candidates = []
        for result in subagent_results:
            candidate = await self.run_service.add_candidate(
                run.id,
                AgentCandidateCreate(
                    agent_name=result.agent_name,
                    provider=result.provider,
                    model_name=result.model_name,
                    output=result.output,
                    tool_calls=result.tool_calls,
                    metrics=result.metrics,
                ),
            )
            candidates.append(candidate)

            await self.run_service.add_checkpoint(
                run.id,
                AgentCheckpointCreate(
                    sequence=sequence,
                    label=f"candidate:{result.agent_name}",
                    state={
                        "candidate_id": str(candidate.id),
                        "agent_name": result.agent_name,
                        "provider": result.provider,
                        "model_name": result.model_name,
                    },
                ),
            )
            sequence += 1

        decision = await self._run_judge(data, candidates)
        if decision is not None:
            decision_state = self._build_decision_state(decision, candidates)
            await self.run_service.add_checkpoint(
                run.id,
                AgentCheckpointCreate(
                    sequence=sequence,
                    label="decision",
                    state=decision_state,
                ),
            )
            sequence += 1

        status = "completed"
        if subagent_errors and not candidates:
            status = "failed"
        run = await self.run_service.update_run(run.id, AgentRunUpdate(status=status))

        checkpoints, _ = await self.run_service.list_checkpoints(run.id)

        return AgentTddRunResult(
            run=run,
            candidates=candidates,
            decision=decision,
            checkpoints=checkpoints,
            errors=subagent_errors,
        )

    async def _resolve_run(
        self,
        data: AgentTddRunCreate,
        *,
        user_id: UUID | None,
    ):
        if data.run_id:
            return await self.run_service.get_run(data.run_id)
        if data.checkpoint_id:
            checkpoint = await self.run_service.get_checkpoint(data.checkpoint_id)
            fork_data = data.to_fork_create()
            return await self.run_service.fork_run(checkpoint.run_id, fork_data)

        input_payload = {
            "message": data.message,
            "history": data.history,
            "metadata": data.metadata,
        }
        model_config = {
            "provider": settings.LLM_PROVIDER,
            "model": settings.LLM_MODEL,
            "temperature": settings.AI_TEMPERATURE,
        }
        return await self.run_service.create_run(
            AgentRunCreate(
                user_id=user_id,
                status="pending",
                input_payload=input_payload,
                model_config_data=model_config,
                workspace_ref=data.workspace_ref,
                fork_label=data.fork_label,
                fork_reason=data.fork_reason,
            )
        )

    def _resolve_subagents(
        self,
        subagents: list[AgentTddSubagentConfig],
    ) -> list[AgentTddSubagentConfig]:
        if subagents:
            return subagents
        if settings.DUAL_SUBAGENT_ENABLED:
            return [
                AgentTddSubagentConfig(name="openai", provider="openai"),
                AgentTddSubagentConfig(name="anthropic", provider="anthropic"),
            ]
        default_provider = settings.LLM_PROVIDER
        return [AgentTddSubagentConfig(name=default_provider, provider=default_provider)]

    async def _run_subagents(
        self,
        subagents: list[AgentTddSubagentConfig],
        data: AgentTddRunCreate,
    ) -> tuple[list[_SubagentResult], list[AgentTddSubagentError]]:
        tasks = [self._run_subagent(cfg, data) for cfg in subagents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        subagent_results: list[_SubagentResult] = []
        subagent_errors: list[AgentTddSubagentError] = []
        for cfg, result in zip(subagents, results, strict=False):
            if isinstance(result, BaseException):
                subagent_errors.append(
                    AgentTddSubagentError(
                        agent_name=cfg.name,
                        provider=cfg.provider,
                        model_name=cfg.model_name,
                        error=str(result),
                    )
                )
            else:
                if result.metrics.get("status") == "error":
                    subagent_errors.append(
                        AgentTddSubagentError(
                            agent_name=result.agent_name,
                            provider=result.provider,
                            model_name=result.model_name,
                            error=str(result.metrics.get("error", "unknown error")),
                        )
                    )
                subagent_results.append(result)
        return subagent_results, subagent_errors

    async def _run_subagent(
        self,
        cfg: AgentTddSubagentConfig,
        data: AgentTddRunCreate,
    ) -> _SubagentResult:
        model_name = cfg.model_name or settings.model_for_provider(cfg.provider)
        agent = AssistantAgent(
            model_name=model_name,
            temperature=cfg.temperature,
            system_prompt=cfg.system_prompt,
            llm_provider=cfg.provider,
        )
        tool_calls: dict[str, Any] = {}
        metrics: dict[str, Any] = {}

        started_at = time.monotonic()
        with telemetry_span(
            "agent_run.subagent",
            agent_name=cfg.name,
            provider=cfg.provider,
            model_name=model_name,
        ):
            try:
                output, tool_events, _ = await agent.run(data.message, data.history)
                tool_calls = self._serialize_tool_events(tool_events)
                metrics = {
                    "duration_ms": int((time.monotonic() - started_at) * 1000),
                    "tool_call_count": len(tool_calls.get("events", [])),
                    "status": "ok",
                    "history_length": len(data.history or []),
                    "message_length": len(data.message or ""),
                }
                return _SubagentResult(
                    agent_name=cfg.name,
                    provider=cfg.provider,
                    model_name=model_name,
                    output=output,
                    tool_calls=tool_calls,
                    metrics=metrics,
                )
            except Exception as exc:
                metrics = {
                    "duration_ms": int((time.monotonic() - started_at) * 1000),
                    "status": "error",
                    "error": str(exc),
                    "history_length": len(data.history or []),
                    "message_length": len(data.message or ""),
                }
                return _SubagentResult(
                    agent_name=cfg.name,
                    provider=cfg.provider,
                    model_name=model_name,
                    output=None,
                    tool_calls=tool_calls,
                    metrics=metrics,
                )

    async def _run_judge(
        self,
        data: AgentTddRunCreate,
        candidates,
    ):
        if not candidates:
            return None

        judge_cfg = data.judge or data.default_judge_config()
        provider = judge_cfg.provider or "openai"
        model_name = judge_cfg.model_name or settings.JUDGE_LLM_MODEL

        prompt = self._build_judge_prompt(data.message, candidates)
        agent = AssistantAgent(
            model_name=model_name,
            temperature=judge_cfg.temperature,
            system_prompt=judge_cfg.system_prompt or JUDGE_SYSTEM_PROMPT,
            llm_provider=provider,
        )

        with telemetry_span(
            "agent_run.judge",
            provider=provider,
            model_name=model_name,
            candidate_count=len(candidates),
        ):
            output, _, _ = await agent.run(prompt, history=[])

        parsed = self._parse_judge_output(output, candidates)
        if parsed is None:
            parsed = {
                "candidate_id": candidates[0].id,
                "score": None,
                "rationale": (
                    "Judge output could not be parsed; defaulted to first candidate."
                ),
            }

        return await self.run_service.set_decision(
            candidates[0].run_id,
            AgentDecisionCreate(
                candidate_id=parsed["candidate_id"],
                score=parsed.get("score"),
                rationale=parsed.get("rationale"),
                model_name=model_name,
            ),
        )

    @staticmethod
    def _serialize_tool_events(tool_events: list[Any]) -> dict[str, Any]:
        events = []
        for event in tool_events:
            event_dict = {}
            if hasattr(event, "tool_name"):
                event_dict["tool_name"] = event.tool_name
            if hasattr(event, "args"):
                event_dict["args"] = event.args
            if hasattr(event, "tool_call_id"):
                event_dict["tool_call_id"] = event.tool_call_id
            if event_dict:
                events.append(event_dict)
        return {"events": events}

    @staticmethod
    def _build_judge_prompt(user_message: str, candidates) -> str:
        items = []
        for candidate in candidates:
            items.append(
                {
                    "candidate_id": str(candidate.id),
                    "agent_name": candidate.agent_name,
                    "provider": candidate.provider,
                    "model_name": candidate.model_name,
                    "output": candidate.output or "",
                }
            )
        return (
            "Select the best candidate response based on helpfulness and correctness. "
            "Return JSON with keys: candidate_id, score (0-1), "
            "helpfulness_score (0-1), correctness_score (0-1), rationale.\n\n"
            f"User message:\n{user_message}\n\n"
            f"Candidates:\n{json.dumps(items, indent=2)}"
        )

    @staticmethod
    def _parse_judge_output(output: str, candidates) -> dict[str, Any] | None:
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return None

        candidate_id = data.get("candidate_id")
        if not candidate_id:
            return None

        candidate_ids = {str(candidate.id) for candidate in candidates}
        if candidate_id not in candidate_ids:
            return None

        helpfulness = data.get("helpfulness_score")
        correctness = data.get("correctness_score")
        rationale = data.get("rationale")
        if helpfulness is not None or correctness is not None:
            rationale_parts = []
            if helpfulness is not None:
                rationale_parts.append(f"helpfulness={helpfulness}")
            if correctness is not None:
                rationale_parts.append(f"correctness={correctness}")
            if rationale:
                rationale_parts.append(str(rationale))
            rationale = "; ".join(rationale_parts)

        return {
            "candidate_id": UUID(candidate_id),
            "score": data.get("score"),
            "rationale": rationale,
        }

    @staticmethod
    def _build_decision_state(decision, candidates) -> dict[str, Any]:
        selected = None
        if decision and decision.candidate_id:
            for candidate in candidates:
                if candidate.id == decision.candidate_id:
                    selected = candidate
                    break

        state: dict[str, Any] = {
            "decision_id": str(decision.id) if decision else None,
            "candidate_id": str(decision.candidate_id) if decision else None,
            "judge_model_name": decision.model_name if decision else None,
            "score": decision.score if decision else None,
            "rationale": decision.rationale if decision else None,
        }

        if selected:
            state["selected_candidate"] = {
                "agent_name": selected.agent_name,
                "provider": selected.provider,
                "model_name": selected.model_name,
            }

        return state
