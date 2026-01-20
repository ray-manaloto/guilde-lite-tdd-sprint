"""Ralph playbook planning interview helper."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic_ai import RunContext

from app.agents.assistant import AssistantAgent, Deps
from app.agents.prompts import PLANNING_JUDGE_SYSTEM_PROMPT, RALPH_PLANNING_SYSTEM_PROMPT
from app.core.config import settings
from app.core.logfire_links import build_logfire_payload
from app.core.telemetry import telemetry_span


@dataclass(frozen=True)
class PlanningInterviewResult:
    """Result of a planning interview run."""

    questions: list[dict[str, str]]
    metadata: dict[str, Any]


async def run_planning_interview(
    prompt: str,
    *,
    max_questions: int = 5,
    provider: str | None = None,
    model_name: str | None = None,
) -> PlanningInterviewResult:
    """Run the Ralph planning interview and return captured questions."""
    if settings.PLANNING_INTERVIEW_MODE == "stub":
        stub_questions = [
            {
                "question": "Who is the primary user for this sprint?",
                "rationale": "Clarify the target audience and JTBD.",
            },
            {
                "question": "What does success look like at the end of this sprint?",
                "rationale": "Define acceptance criteria.",
            },
            {
                "question": "Are there constraints or dependencies we must respect?",
                "rationale": "Surface blockers, integrations, or deadlines.",
            },
            {
                "question": "What should be explicitly out of scope?",
                "rationale": "Set boundaries to keep the sprint focused.",
            },
            {
                "question": "Are there edge cases we must cover?",
                "rationale": "Identify critical scenarios early.",
            },
        ]
        questions = stub_questions[:max_questions]
        metadata = {
            "mode": "stub",
            "max_questions": max_questions,
            "question_count": len(questions),
        }
        return PlanningInterviewResult(questions=questions, metadata=metadata)

    if settings.DUAL_SUBAGENT_ENABLED:
        return await _run_dual_subagent_planning(prompt, max_questions=max_questions)

    provider_name = provider or settings.LLM_PROVIDER
    model = model_name or settings.model_for_provider(provider_name)
    questions, telemetry = await _run_planning_agent(
        prompt,
        max_questions=max_questions,
        provider=provider_name,
        model_name=model,
    )
    metadata = {
        "mode": "single",
        "provider": telemetry.get("provider"),
        "model_name": telemetry.get("model_name"),
        "max_questions": max_questions,
        "question_count": len(questions),
    }
    metadata.update(_trace_metadata(telemetry))
    return PlanningInterviewResult(questions=questions, metadata=metadata)


def _trace_metadata(telemetry: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if telemetry.get("trace_id"):
        data["trace_id"] = telemetry["trace_id"]
    if telemetry.get("trace_url"):
        data["trace_url"] = telemetry["trace_url"]
    return data


async def _run_planning_agent(
    prompt: str,
    *,
    max_questions: int,
    provider: str,
    model_name: str,
    allow_errors: bool = False,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    assistant = AssistantAgent(
        model_name=model_name,
        system_prompt=RALPH_PLANNING_SYSTEM_PROMPT,
        llm_provider=provider,
        temperature=0.2,
    )

    questions: list[dict[str, str]] = []

    @assistant.agent.tool
    async def ask_user_question(
        ctx: RunContext[Deps],
        question: str,
        rationale: str | None = None,
    ) -> str:
        """Capture a planning interview question."""
        if len(questions) >= max_questions:
            return "Question limit reached. Stop the interview."
        question_text = question.strip()
        if not question_text:
            return "Question was empty; ask a different question."
        payload: dict[str, str] = {"question": question_text}
        if rationale:
            payload["rationale"] = rationale.strip()
        questions.append(payload)
        return "Question recorded. Ask the next question or finish."

    interview_prompt = (
        "Interview the user using the ask_user_question tool. "
        f"Ask up to {max_questions} questions about the sprint prompt below. "
        "Do not answer the questions. Do not propose solutions or plans.\n\n"
        f"Sprint prompt:\n{prompt}"
    )

    deps = Deps(metadata={"max_questions": max_questions, "planning_prompt": prompt})
    trace_id = None
    span_id = None
    error: str | None = None
    try:
        with telemetry_span(
            "sprint_planning.subagent",
            provider=provider,
            model_name=assistant.model_name,
            max_questions=max_questions,
        ) as (span_trace_id, span_span_id):
            trace_id = span_trace_id
            span_id = span_span_id
            await assistant.agent.run(interview_prompt, deps=deps)

        if not questions:
            raise ValueError("Planning interview produced no questions.")
    except Exception as exc:
        error = str(exc)
        if not allow_errors:
            raise

    telemetry = {
        "provider": assistant.llm_provider,
        "model_name": assistant.model_name,
        "trace_id": trace_id,
        "span_id": span_id,
    }
    if error:
        telemetry["error"] = error
    trace_payload = build_logfire_payload(trace_id)
    if trace_payload:
        telemetry.update(trace_payload)
    return questions, telemetry


async def _run_dual_subagent_planning(
    prompt: str,
    *,
    max_questions: int,
) -> PlanningInterviewResult:
    settings.validate_dual_subagent_settings()
    candidate_specs = [
        ("openai", settings.model_for_provider("openai")),
        ("anthropic", settings.model_for_provider("anthropic")),
    ]

    candidates: list[dict[str, Any]] = []
    for provider, model_name in candidate_specs:
        questions, telemetry = await _run_planning_agent(
            prompt,
            max_questions=max_questions,
            provider=provider,
            model_name=model_name,
            allow_errors=True,
        )
        candidates.append(
            {
                "provider": telemetry.get("provider"),
                "model_name": telemetry.get("model_name"),
                "questions": questions,
                "trace_id": telemetry.get("trace_id"),
                "trace_url": telemetry.get("trace_url"),
                "error": telemetry.get("error"),
            }
        )

    successful_candidates = [c for c in candidates if c.get("questions")]
    if not successful_candidates:
        raise ValueError("Planning interview produced no questions.")

    judge_prompt = _build_planning_judge_prompt(prompt, successful_candidates)
    judge_meta, selected_key = await _run_planning_judge(
        judge_prompt,
        successful_candidates,
    )

    selected = next(
        (
            candidate
            for candidate in successful_candidates
            if candidate["provider"] == selected_key
        ),
        successful_candidates[0],
    )

    metadata = {
        "mode": "dual_subagent",
        "max_questions": max_questions,
        "question_count": len(selected["questions"]),
        "candidates": [
            {
                "provider": candidate.get("provider"),
                "model_name": candidate.get("model_name"),
                "trace_id": candidate.get("trace_id"),
                "trace_url": candidate.get("trace_url"),
                "error": candidate.get("error"),
            }
            for candidate in candidates
        ],
        "judge": {
            "provider": judge_meta.get("provider"),
            "model_name": judge_meta.get("model_name"),
            "trace_id": judge_meta.get("trace_id"),
            "trace_url": judge_meta.get("trace_url"),
            "score": judge_meta.get("score"),
            "rationale": judge_meta.get("rationale"),
        },
        "selected_candidate": {
            "provider": selected.get("provider"),
            "model_name": selected.get("model_name"),
        },
    }

    return PlanningInterviewResult(questions=selected["questions"], metadata=metadata)


def _build_planning_judge_prompt(
    user_message: str,
    candidates: list[dict[str, Any]],
) -> str:
    items = []
    for candidate in candidates:
        items.append(
            {
                "candidate_key": candidate.get("provider"),
                "provider": candidate.get("provider"),
                "model_name": candidate.get("model_name"),
                "questions": candidate.get("questions") or [],
            }
        )
    return (
        "Select the best question set based on helpfulness and correctness. "
        "Return JSON with keys: candidate_key, score (0-1), "
        "helpfulness_score (0-1), correctness_score (0-1), rationale.\n\n"
        f"Sprint prompt:\n{user_message}\n\n"
        f"Candidates:\n{json.dumps(items, indent=2)}"
    )


async def _run_planning_judge(
    prompt: str,
    candidates: list[dict[str, Any]],
) -> tuple[dict[str, Any], str]:
    provider = "openai"
    model_name = settings.JUDGE_LLM_MODEL
    agent = AssistantAgent(
        model_name=model_name,
        temperature=0.0,
        system_prompt=PLANNING_JUDGE_SYSTEM_PROMPT,
        llm_provider=provider,
    )

    candidate_keys = {candidate.get("provider") for candidate in candidates}
    with telemetry_span(
        "sprint_planning.judge",
        provider=provider,
        model_name=model_name,
        candidate_count=len(candidates),
    ) as (trace_id, span_id):
        output, _, _ = await agent.run(prompt, history=[])

    parsed = _parse_planning_judge_output(output, candidate_keys)
    if parsed is None:
        parsed = {
            "candidate_key": candidates[0].get("provider"),
            "score": None,
            "rationale": "Judge output could not be parsed; defaulted to first candidate.",
        }

    telemetry = {
        "provider": provider,
        "model_name": model_name,
        "trace_id": trace_id,
        "span_id": span_id,
        "score": parsed.get("score"),
        "rationale": parsed.get("rationale"),
    }
    trace_payload = build_logfire_payload(trace_id)
    if trace_payload:
        telemetry.update(trace_payload)
    return telemetry, parsed["candidate_key"]


def _parse_planning_judge_output(
    output: str,
    candidate_keys: set[str | None],
) -> dict[str, Any] | None:
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return None

    candidate_key = data.get("candidate_key")
    if not candidate_key or candidate_key not in candidate_keys:
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
        "candidate_key": candidate_key,
        "score": data.get("score"),
        "rationale": rationale,
    }
