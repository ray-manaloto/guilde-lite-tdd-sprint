"""Spec workflow service."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError, ValidationError
from app.db.models.spec import Spec, SpecComplexity, SpecStatus
from app.agents.ralph_planner import run_planning_interview
from app.repositories import spec_repo
from app.schemas.spec import SpecCreate, SpecPlanningAnswer


@dataclass
class SpecComplexityAssessment:
    """Result of heuristic complexity assessment."""

    complexity: SpecComplexity
    confidence: float
    signals: dict
    phases: list[str]

    def to_dict(self) -> dict:
        return {
            "complexity": self.complexity.value,
            "confidence": self.confidence,
            "signals": self.signals,
            "phases": self.phases,
        }


class SpecService:
    """Service for spec workflow."""

    SIMPLE_KEYWORDS = {
        "fix",
        "typo",
        "update",
        "change",
        "rename",
        "remove",
        "delete",
        "adjust",
        "tweak",
        "copy",
        "text",
        "label",
        "button",
        "style",
        "color",
    }

    COMPLEX_KEYWORDS = {
        "integration",
        "integrate",
        "oauth",
        "auth",
        "database",
        "migration",
        "docker",
        "kubernetes",
        "queue",
        "cache",
        "redis",
        "postgres",
        "websocket",
        "pipeline",
        "workflow",
        "architecture",
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    def assess_complexity(self, task: str) -> SpecComplexityAssessment:
        """Assess complexity with a lightweight heuristic."""
        task_lower = task.lower()
        simple_matches = sum(1 for kw in self.SIMPLE_KEYWORDS if kw in task_lower)
        complex_matches = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in task_lower)

        signals = {
            "simple_keywords": simple_matches,
            "complex_keywords": complex_matches,
            "task_length": len(task.split()),
        }

        if complex_matches >= 2:
            complexity = SpecComplexity.COMPLEX
            phases = [
                "discovery",
                "requirements",
                "context",
                "spec",
                "planning",
                "validation",
            ]
            confidence = min(0.9, 0.6 + (0.1 * complex_matches))
        elif simple_matches > 0 and complex_matches == 0 and signals["task_length"] < 40:
            complexity = SpecComplexity.SIMPLE
            phases = ["discovery", "spec", "validation"]
            confidence = min(0.8, 0.5 + (0.1 * simple_matches))
        else:
            complexity = SpecComplexity.STANDARD
            phases = [
                "discovery",
                "requirements",
                "context",
                "spec",
                "planning",
                "validation",
            ]
            confidence = 0.6

        return SpecComplexityAssessment(
            complexity=complexity,
            confidence=confidence,
            signals=signals,
            phases=phases,
        )

    def _build_title(self, task: str, title: str | None = None) -> str:
        if title:
            return title.strip()
        trimmed = " ".join(task.strip().split())
        return trimmed[:80] if len(trimmed) > 80 else trimmed

    async def get_by_id(self, spec_id: UUID) -> Spec:
        """Get spec by ID."""
        spec = await spec_repo.get_by_id(self.db, spec_id)
        if not spec:
            raise NotFoundError(message="Spec not found", details={"spec_id": str(spec_id)})
        return spec

    async def get_multi(self, *, skip: int = 0, limit: int = 100, status=None) -> list[Spec]:
        """Get multiple specs."""
        return await spec_repo.get_multi(self.db, skip=skip, limit=limit, status=status)

    async def create(self, spec_in: SpecCreate, user_id: UUID | None = None) -> Spec:
        """Create a spec draft with complexity assessment."""
        assessment = self.assess_complexity(spec_in.task)
        title = self._build_title(spec_in.task, spec_in.title)
        artifacts = {"assessment": assessment.to_dict()}

        return await spec_repo.create(
            self.db,
            user_id=user_id,
            title=title,
            task=spec_in.task,
            complexity=assessment.complexity,
            status=SpecStatus.DRAFT,
            phases=assessment.phases,
            artifacts=artifacts,
        )

    async def validate(self, spec_id: UUID) -> tuple[Spec, dict]:
        """Validate spec contents and update status."""
        spec = await self.get_by_id(spec_id)
        errors: list[str] = []
        warnings: list[str] = []

        if not spec.task or not spec.task.strip():
            errors.append("Spec task is required.")
        if not spec.phases:
            errors.append("Spec phases are required.")

        valid = len(errors) == 0
        validation = {"valid": valid, "errors": errors, "warnings": warnings}

        artifacts = dict(spec.artifacts or {})
        artifacts["validation"] = validation

        status = SpecStatus.VALIDATED if valid else spec.status

        updated = await spec_repo.update(
            self.db,
            db_spec=spec,
            update_data={"artifacts": artifacts, "status": status},
        )
        return updated, validation

    async def create_with_planning(
        self,
        spec_in: SpecCreate,
        *,
        max_questions: int = 5,
    ) -> tuple[Spec, dict]:
        """Create a spec and run the planning interview."""
        spec = await self.create(spec_in)
        updated, planning = await self.start_planning(spec.id, max_questions=max_questions)
        return updated, planning

    async def start_planning(
        self,
        spec_id: UUID,
        *,
        max_questions: int = 5,
    ) -> tuple[Spec, dict]:
        """Generate planning interview questions and store them."""
        spec = await self.get_by_id(spec_id)
        if not spec.task or not spec.task.strip():
            raise ValidationError(message="Spec task is required for planning.")

        try:
            interview = await run_planning_interview(spec.task, max_questions=max_questions)
        except ValueError as exc:
            raise ValidationError(message=str(exc)) from exc
        planning = {
            "status": "needs_answers",
            "questions": interview.questions,
            "answers": [],
            "metadata": interview.metadata,
        }

        artifacts = dict(spec.artifacts or {})
        artifacts["planning"] = planning

        updated = await spec_repo.update(
            self.db,
            db_spec=spec,
            update_data={"artifacts": artifacts},
        )
        return updated, planning

    async def save_planning_answers(
        self,
        spec_id: UUID,
        answers: list[SpecPlanningAnswer],
    ) -> tuple[Spec, dict]:
        """Store planning interview answers for a spec."""
        spec = await self.get_by_id(spec_id)
        artifacts = dict(spec.artifacts or {})
        planning = dict(artifacts.get("planning") or {})
        questions = planning.get("questions") or []
        if not questions:
            raise BadRequestError(message="Planning interview has not been started.")
        if not answers:
            raise ValidationError(message="Planning answers are required.")

        normalized = []
        for answer in answers:
            question = answer.question.strip()
            response = answer.answer.strip()
            if not question or not response:
                raise ValidationError(message="Planning answers cannot be empty.")
            normalized.append({"question": question, "answer": response})

        if len(normalized) < len(questions):
            raise ValidationError(message="All planning questions must be answered.")

        planning["answers"] = normalized
        planning["status"] = "answered"
        artifacts["planning"] = planning

        updated = await spec_repo.update(
            self.db,
            db_spec=spec,
            update_data={"artifacts": artifacts},
        )
        return updated, planning
