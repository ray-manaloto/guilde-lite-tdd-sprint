"""Spec exporter service for disk persistence."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class SpecExporter:
    """Exports specs and related artifacts to disk in multiple formats."""

    def __init__(self, base_dir: Path):
        """Initialize the spec exporter.

        Args:
            base_dir: Base directory for the sprint artifacts
        """
        self.base_dir = base_dir
        self.spec_dir = base_dir / "spec"

    def _ensure_dirs(self) -> None:
        """Ensure required directories exist."""
        dirs = [
            self.spec_dir,
            self.spec_dir / "questionnaire",
            self.spec_dir / "questionnaire" / "candidates",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    async def export_spec(
        self,
        spec_id: UUID,
        title: str,
        task: str,
        complexity: str,
        status: str,
        phases: list[str],
        artifacts: dict[str, Any],
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> tuple[Path, Path]:
        """Export spec to JSON and Markdown formats.

        Args:
            spec_id: Spec UUID
            title: Spec title
            task: The task description
            complexity: Complexity tier (simple/standard/complex)
            status: Spec status (draft/validated/approved/rejected)
            phases: List of phase names
            artifacts: Full artifacts dictionary
            created_at: Creation timestamp
            updated_at: Last update timestamp

        Returns:
            Tuple of (json_path, markdown_path)
        """
        self._ensure_dirs()

        # Build spec data
        spec_data = {
            "id": str(spec_id),
            "title": title,
            "task": task,
            "complexity": complexity,
            "status": status,
            "phases": phases,
            "artifacts": artifacts,
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

        # Save JSON
        json_path = self.spec_dir / "spec.json"
        json_path.write_text(json.dumps(spec_data, indent=2))

        # Save Markdown
        md_path = self.spec_dir / "spec.md"
        md_content = self._generate_spec_markdown(spec_data)
        md_path.write_text(md_content)

        logger.info(f"Exported spec to {json_path} and {md_path}")
        return json_path, md_path

    def _generate_spec_markdown(self, spec_data: dict[str, Any]) -> str:
        """Generate human-readable Markdown from spec data.

        Args:
            spec_data: Spec data dictionary

        Returns:
            Markdown string
        """
        lines = [
            f"# {spec_data['title']}",
            "",
            f"**Status:** {spec_data['status']}",
            f"**Complexity:** {spec_data['complexity']}",
            f"**Spec ID:** `{spec_data['id']}`",
            "",
            "---",
            "",
            "## Task",
            "",
            spec_data["task"],
            "",
        ]

        # Add phases
        if spec_data.get("phases"):
            lines.extend(
                [
                    "## Phases",
                    "",
                ]
            )
            for i, phase in enumerate(spec_data["phases"], 1):
                lines.append(f"{i}. {phase}")
            lines.append("")

        # Add artifacts summary
        artifacts = spec_data.get("artifacts", {})

        # Planning section
        if "planning" in artifacts:
            planning = artifacts["planning"]
            lines.extend(
                [
                    "## Planning",
                    "",
                ]
            )
            if planning.get("assessment"):
                assessment = planning["assessment"]
                lines.extend(
                    [
                        "### Assessment",
                        "",
                        f"- **Complexity:** {assessment.get('complexity', 'N/A')}",
                        f"- **Rationale:** {assessment.get('rationale', 'N/A')}",
                        "",
                    ]
                )

            if planning.get("questions"):
                lines.extend(
                    [
                        "### Interview Questions",
                        "",
                    ]
                )
                for q in planning["questions"]:
                    lines.append(f"- {q.get('text', q)}")
                lines.append("")

            if planning.get("answers"):
                lines.extend(
                    [
                        "### Answers",
                        "",
                    ]
                )
                for a in planning["answers"]:
                    if isinstance(a, dict):
                        lines.append(f"**Q:** {a.get('question', 'N/A')}")
                        lines.append(f"**A:** {a.get('answer', 'N/A')}")
                        lines.append("")
                    else:
                        lines.append(f"- {a}")
                lines.append("")

        # Judge section
        if "judge" in artifacts:
            judge = artifacts["judge"]
            lines.extend(
                [
                    "## Judge Decision",
                    "",
                    f"- **Winner:** {judge.get('winner', 'N/A')}",
                    f"- **Score:** {judge.get('score', 'N/A')}",
                    f"- **Model:** {judge.get('model', 'N/A')}",
                    "",
                ]
            )
            if judge.get("rationale"):
                lines.extend(
                    [
                        "### Rationale",
                        "",
                        judge["rationale"],
                        "",
                    ]
                )

        # Candidates section
        if "candidates" in artifacts:
            lines.extend(
                [
                    "## Candidates",
                    "",
                ]
            )
            for provider, candidate in artifacts["candidates"].items():
                lines.append(f"### {provider.title()}")
                lines.append("")
                if isinstance(candidate, dict):
                    if candidate.get("questions"):
                        lines.append(f"Questions generated: {len(candidate['questions'])}")
                    if candidate.get("error"):
                        lines.append(f"Error: {candidate['error']}")
                lines.append("")

        # Metadata
        lines.extend(
            [
                "---",
                "",
                "## Metadata",
                "",
                f"- **Created:** {spec_data.get('created_at', 'N/A')}",
                f"- **Updated:** {spec_data.get('updated_at', 'N/A')}",
                f"- **Exported:** {spec_data.get('exported_at', 'N/A')}",
            ]
        )

        return "\n".join(lines)

    async def export_questionnaire(
        self,
        questions: list[dict[str, Any]],
        candidates: dict[str, Any],
        judge_result: dict[str, Any],
        answers: list[dict[str, Any]],
    ) -> Path:
        """Export full questionnaire with all artifacts.

        Args:
            questions: Final selected questions
            candidates: Candidate questions from each provider
            judge_result: Judge decision on questions
            answers: User-provided answers

        Returns:
            Path to the questionnaire directory
        """
        self._ensure_dirs()
        questionnaire_dir = self.spec_dir / "questionnaire"

        # Save final questions
        questions_path = questionnaire_dir / "questions.json"
        questions_path.write_text(json.dumps(questions, indent=2))

        # Save candidate questions
        candidates_dir = questionnaire_dir / "candidates"
        for provider, candidate_data in candidates.items():
            candidate_path = candidates_dir / f"{provider}.json"
            candidate_path.write_text(json.dumps(candidate_data, indent=2))

        # Save judge result
        judge_path = questionnaire_dir / "judge_result.json"
        judge_path.write_text(json.dumps(judge_result, indent=2))

        # Save answers
        answers_path = questionnaire_dir / "answers.json"
        answers_path.write_text(json.dumps(answers, indent=2))

        # Save final questions (after judging)
        final_path = questionnaire_dir / "final_questions.json"
        final_path.write_text(json.dumps(questions, indent=2))

        logger.info(f"Exported questionnaire to {questionnaire_dir}")
        return questionnaire_dir

    async def export_assessment(self, assessment: dict[str, Any]) -> Path:
        """Export complexity assessment.

        Args:
            assessment: Assessment data with complexity and rationale

        Returns:
            Path to the assessment file
        """
        self._ensure_dirs()

        assessment_path = self.spec_dir / "assessment.json"
        assessment_path.write_text(json.dumps(assessment, indent=2))

        logger.info(f"Exported assessment to {assessment_path}")
        return assessment_path

    async def export_code_files(
        self,
        files: dict[str, str],
        execution_log: dict[str, Any] | None = None,
    ) -> Path:
        """Export generated code files.

        Args:
            files: Dictionary of filename -> content
            execution_log: Optional execution/test results

        Returns:
            Path to the code directory
        """
        code_dir = self.base_dir / "code"
        code_dir.mkdir(parents=True, exist_ok=True)

        # Save each code file
        for filename, content in files.items():
            file_path = code_dir / filename
            file_path.write_text(content)
            logger.debug(f"Exported code file: {file_path}")

        # Save execution log if provided
        if execution_log:
            log_path = code_dir / "execution_log.json"
            log_path.write_text(json.dumps(execution_log, indent=2))

        logger.info(f"Exported {len(files)} code files to {code_dir}")
        return code_dir

    async def export_from_spec_model(self, spec: Any) -> tuple[Path, Path]:
        """Export from a Spec database model.

        Args:
            spec: Spec model instance with all fields

        Returns:
            Tuple of (json_path, markdown_path)
        """
        return await self.export_spec(
            spec_id=spec.id,
            title=spec.title,
            task=spec.task,
            complexity=spec.complexity.value if hasattr(spec.complexity, "value") else spec.complexity,
            status=spec.status.value if hasattr(spec.status, "value") else spec.status,
            phases=spec.phases or [],
            artifacts=spec.artifacts or {},
            created_at=spec.created_at,
            updated_at=spec.updated_at,
        )
