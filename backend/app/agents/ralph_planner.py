"""Ralph playbook planning interview helper."""

from dataclasses import dataclass
from typing import Any

from pydantic_ai import RunContext

from app.agents.assistant import AssistantAgent, Deps
from app.agents.prompts import RALPH_PLANNING_SYSTEM_PROMPT
from app.core.config import settings


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
    await assistant.agent.run(interview_prompt, deps=deps)

    if not questions:
        raise ValueError("Planning interview produced no questions.")

    metadata = {
        "provider": assistant.llm_provider,
        "model_name": assistant.model_name,
        "max_questions": max_questions,
        "question_count": len(questions),
    }
    return PlanningInterviewResult(questions=questions, metadata=metadata)
