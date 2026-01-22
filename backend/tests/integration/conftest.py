"""Integration test fixtures for sprint interview to code workflow.

This module provides reusable fixtures for integration tests that exercise
the complete sprint workflow from planning interview to code generation
and validation.

Fixtures provided:
- db_session: Isolated database session with transaction rollback
- temp_workspace: Temporary directory for artifacts with cleanup
- mock_ai_config: Configuration for mock/stub AI responses
- spec_service: SpecService instance
- sprint_service: SprintService instance
- agent_tdd_service: AgentTddService instance
- planning_interview_helper: Helper for simulating planning interviews
- artifact_validator: Helper for validating generated artifacts
"""

import shutil
import subprocess
import tempfile
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.models.spec import Spec
from app.db.models.sprint import Sprint
from app.schemas.spec import SpecCreate, SpecPlanningAnswer
from app.schemas.sprint import SprintCreate
from app.services.agent_tdd import AgentTddService
from app.services.spec import SpecService
from app.services.sprint import SprintService

# =============================================================================
# Database Session Fixtures
# =============================================================================


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a real database session for integration tests.

    Creates an isolated session with NullPool to prevent connection sharing.
    All changes are rolled back after the test completes.
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=NullPool,
    )
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()
            await engine.dispose()


@pytest.fixture
async def db_session_with_commit() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session that commits changes.

    Use this for tests that need to persist data across service calls.
    WARNING: Data will persist in the database after the test.
    Consider using test-specific data with unique identifiers.
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=NullPool,
    )
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            await engine.dispose()


# =============================================================================
# Workspace and Artifact Fixtures
# =============================================================================


@pytest.fixture
def temp_workspace() -> AsyncGenerator[Path, None]:
    """Provide a temporary workspace directory for test artifacts.

    Creates a fresh temporary directory that is cleaned up after the test.
    The directory is created under the system temp directory.
    """
    workspace = Path(tempfile.mkdtemp(prefix="guilde_test_"))
    yield workspace
    # Cleanup after test
    if workspace.exists():
        shutil.rmtree(workspace)


@pytest.fixture
def clean_artifacts_dir() -> AsyncGenerator[Path | None, None]:
    """Clean up and provide the configured artifacts directory.

    Uses the settings.AUTOCODE_ARTIFACTS_DIR if configured and safe to clean.
    Falls back to a temporary directory if not configured.
    """
    artifacts_dir = settings.AUTOCODE_ARTIFACTS_DIR

    # Only clean if directory exists and is in a safe location
    if (
        artifacts_dir
        and artifacts_dir.exists()
        and (
            "tmp" in str(artifacts_dir) or "guilde-lite-tdd-sprint-filesystem" in str(artifacts_dir)
        )
    ):
        shutil.rmtree(artifacts_dir)

    if artifacts_dir:
        artifacts_dir.mkdir(parents=True, exist_ok=True)

    yield artifacts_dir

    # Optional cleanup after test (commented out to preserve artifacts for debugging)
    # if artifacts_dir and artifacts_dir.exists():
    #     shutil.rmtree(artifacts_dir)


@pytest.fixture
def isolated_artifacts_dir(temp_workspace: Path) -> AsyncGenerator[Path, None]:
    """Provide an isolated artifacts directory using the temp workspace.

    Patches settings.AUTOCODE_ARTIFACTS_DIR to use the temp workspace,
    ensuring complete isolation between tests.
    """
    artifacts_dir = temp_workspace / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with patch.object(settings, "AUTOCODE_ARTIFACTS_DIR", artifacts_dir):
        yield artifacts_dir


# =============================================================================
# AI Configuration Fixtures
# =============================================================================


@pytest.fixture
def stub_planning_mode():
    """Configure the planning interview to use stub mode.

    This avoids making real API calls during tests.
    """
    with patch.object(settings, "PLANNING_INTERVIEW_MODE", "stub"):
        yield


@pytest.fixture
def disable_dual_subagent():
    """Disable dual-subagent mode for faster, simpler tests."""
    with patch.object(settings, "DUAL_SUBAGENT_ENABLED", False):
        yield


@pytest.fixture
def mock_ai_config(stub_planning_mode, disable_dual_subagent):
    """Combine all AI mock configurations for isolated tests.

    This fixture disables external AI calls for unit-style integration tests.
    """
    yield


# =============================================================================
# Service Instance Fixtures
# =============================================================================


@pytest.fixture
def spec_service(db_session: AsyncSession) -> SpecService:
    """Provide a SpecService instance with the test database session."""
    return SpecService(db_session)


@pytest.fixture
def sprint_service(db_session: AsyncSession) -> SprintService:
    """Provide a SprintService instance with the test database session."""
    return SprintService(db_session)


@pytest.fixture
def agent_tdd_service(db_session: AsyncSession) -> AgentTddService:
    """Provide an AgentTddService instance with the test database session."""
    return AgentTddService(db_session)


# =============================================================================
# Planning Interview Helper
# =============================================================================


@dataclass
class PlanningInterviewHelper:
    """Helper class for simulating planning interviews in tests.

    Provides methods to:
    - Create a spec with planning interview
    - Generate standard answers for common question patterns
    - Submit answers programmatically
    """

    spec_service: SpecService
    db_session: AsyncSession

    # Standard answer patterns for common question types
    ANSWER_PATTERNS: dict[str, str] = field(
        default_factory=lambda: {
            "user": "The user is a developer testing the system.",
            "audience": "The user is a developer testing the system.",
            "success": "Success when the script executes without errors and produces expected output.",
            "criteria": "Success when the script executes without errors and produces expected output.",
            "scope": "Only the specified functionality is in scope. No additional features.",
            "out of scope": "Only the specified functionality is in scope. No additional features.",
            "constraint": "No constraints. Standard Python 3 only.",
            "dependencies": "No external dependencies required.",
            "edge": "No edge cases. Just the happy path.",
            "error": "Basic error handling only.",
        }
    )

    async def create_spec_with_planning(
        self,
        task: str,
        title: str = "Test Spec",
        max_questions: int = 5,
    ) -> tuple[Spec, dict]:
        """Create a spec and run the planning interview.

        Args:
            task: The task description for the spec
            title: Optional title for the spec
            max_questions: Maximum number of planning questions

        Returns:
            Tuple of (spec, planning_dict)
        """
        spec, planning = await self.spec_service.create_with_planning(
            SpecCreate(task=task, title=title),
            max_questions=max_questions,
        )
        await self.db_session.commit()
        return spec, planning

    def generate_answers(
        self,
        questions: list[dict],
        custom_answers: dict[str, str] | None = None,
    ) -> list[SpecPlanningAnswer]:
        """Generate answers for planning questions using pattern matching.

        Args:
            questions: List of question dicts with 'question' key
            custom_answers: Optional dict mapping question substrings to answers

        Returns:
            List of SpecPlanningAnswer objects
        """
        custom = custom_answers or {}
        answers = []

        for q in questions:
            question_text = q.get("question", "")
            question_lower = question_text.lower()

            # Check custom answers first
            answer = None
            for pattern, response in custom.items():
                if pattern.lower() in question_lower:
                    answer = response
                    break

            # Fall back to standard patterns
            if answer is None:
                for pattern, response in self.ANSWER_PATTERNS.items():
                    if pattern in question_lower:
                        answer = response
                        break

            # Default answer if no pattern matches
            if answer is None:
                answer = "Keep it simple - implement only the requested functionality."

            answers.append(SpecPlanningAnswer(question=question_text, answer=answer))

        return answers

    async def submit_answers(
        self,
        spec_id: UUID,
        questions: list[dict],
        custom_answers: dict[str, str] | None = None,
    ) -> tuple[Spec, dict]:
        """Submit answers for planning questions.

        Args:
            spec_id: The spec ID
            questions: List of question dicts from planning
            custom_answers: Optional custom answer mappings

        Returns:
            Tuple of (updated_spec, planning_dict)
        """
        answers = self.generate_answers(questions, custom_answers)
        spec, planning = await self.spec_service.save_planning_answers(spec_id, answers)
        await self.db_session.commit()
        return spec, planning

    async def complete_planning(
        self,
        task: str,
        title: str = "Test Spec",
        max_questions: int = 5,
        custom_answers: dict[str, str] | None = None,
    ) -> tuple[Spec, dict]:
        """Complete the full planning workflow (create spec + answer questions).

        Args:
            task: The task description
            title: Optional spec title
            max_questions: Maximum number of planning questions
            custom_answers: Optional custom answer mappings

        Returns:
            Tuple of (spec, planning_dict) with status='answered'
        """
        spec, planning = await self.create_spec_with_planning(task, title, max_questions)
        questions = planning.get("questions", [])

        if questions:
            spec, planning = await self.submit_answers(spec.id, questions, custom_answers)

        return spec, planning


@pytest.fixture
def planning_interview_helper(
    spec_service: SpecService,
    db_session: AsyncSession,
) -> PlanningInterviewHelper:
    """Provide a PlanningInterviewHelper instance."""
    return PlanningInterviewHelper(
        spec_service=spec_service,
        db_session=db_session,
    )


# =============================================================================
# Artifact Validation Helper
# =============================================================================


@dataclass
class ArtifactValidationResult:
    """Result of artifact validation."""

    found: bool
    path: Path | None = None
    content: str | None = None
    execution_result: subprocess.CompletedProcess | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if artifact is valid (found, content exists, execution succeeded)."""
        return (
            self.found
            and self.content is not None
            and (self.execution_result is None or self.execution_result.returncode == 0)
        )


@dataclass
class ArtifactValidator:
    """Helper class for validating generated artifacts.

    Provides methods to:
    - Find artifacts by name pattern
    - Validate file content
    - Execute scripts and validate output
    """

    artifacts_dir: Path

    def find_file(self, filename: str) -> Path | None:
        """Find a file by name in the artifacts directory.

        Args:
            filename: The file name to search for

        Returns:
            Path to the file or None if not found
        """
        matches = list(self.artifacts_dir.rglob(filename))
        return matches[0] if matches else None

    def find_files(self, pattern: str) -> list[Path]:
        """Find all files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g., "*.py", "**/*.md")

        Returns:
            List of matching file paths
        """
        return list(self.artifacts_dir.rglob(pattern))

    def read_file(self, filepath: Path) -> str | None:
        """Read content from a file.

        Args:
            filepath: Path to the file

        Returns:
            File content or None if file doesn't exist
        """
        if filepath and filepath.exists():
            return filepath.read_text()
        return None

    def validate_file_exists(
        self,
        filename: str,
        required_content: str | None = None,
    ) -> ArtifactValidationResult:
        """Validate that a file exists and optionally contains expected content.

        Args:
            filename: The file name to find
            required_content: Optional content that must be present (case-insensitive)

        Returns:
            ArtifactValidationResult with validation details
        """
        result = ArtifactValidationResult(found=False)

        path = self.find_file(filename)
        if not path:
            result.errors.append(f"File '{filename}' not found in {self.artifacts_dir}")
            return result

        result.found = True
        result.path = path
        result.content = self.read_file(path)

        if (
            required_content
            and result.content
            and required_content.lower() not in result.content.lower()
        ):
            result.errors.append(f"Required content '{required_content}' not found in {filename}")

        return result

    def execute_python_script(
        self,
        filepath: Path,
        timeout: int = 30,
        expected_output: str | None = None,
    ) -> ArtifactValidationResult:
        """Execute a Python script and validate the output.

        Args:
            filepath: Path to the Python script
            timeout: Execution timeout in seconds
            expected_output: Optional expected output (case-insensitive)

        Returns:
            ArtifactValidationResult with execution details
        """
        result = ArtifactValidationResult(found=filepath.exists())

        if not result.found:
            result.errors.append(f"Script not found: {filepath}")
            return result

        result.path = filepath
        result.content = self.read_file(filepath)

        try:
            execution = subprocess.run(
                ["python3", str(filepath)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=filepath.parent,
            )
            result.execution_result = execution

            if execution.returncode != 0:
                result.errors.append(
                    f"Script execution failed with code {execution.returncode}: {execution.stderr}"
                )

            if expected_output and expected_output.lower() not in execution.stdout.lower():
                result.errors.append(
                    f"Expected output '{expected_output}' not found. Got: {execution.stdout}"
                )

        except subprocess.TimeoutExpired:
            result.errors.append(f"Script execution timed out after {timeout}s")
        except Exception as e:
            result.errors.append(f"Script execution error: {e}")

        return result

    def validate_hello_world(self) -> ArtifactValidationResult:
        """Convenience method to validate a hello world script.

        Looks for hello.py and validates it prints 'hello world'.
        """
        path = self.find_file("hello.py")
        if not path:
            return ArtifactValidationResult(
                found=False, errors=["hello.py not found in artifacts directory"]
            )

        return self.execute_python_script(path, expected_output="hello world")

    def list_all_artifacts(self) -> list[Path]:
        """List all files in the artifacts directory.

        Returns:
            List of all file paths
        """
        return list(self.artifacts_dir.rglob("*"))

    def get_artifact_summary(self) -> dict[str, Any]:
        """Get a summary of all artifacts for debugging.

        Returns:
            Dict with file counts and paths
        """
        all_files = self.list_all_artifacts()
        return {
            "total_files": len([f for f in all_files if f.is_file()]),
            "total_dirs": len([f for f in all_files if f.is_dir()]),
            "python_files": [str(f) for f in all_files if f.suffix == ".py"],
            "markdown_files": [str(f) for f in all_files if f.suffix == ".md"],
            "all_files": [str(f) for f in all_files if f.is_file()][:20],  # Limit output
        }


@pytest.fixture
def artifact_validator(clean_artifacts_dir: Path) -> ArtifactValidator | None:
    """Provide an ArtifactValidator instance for the artifacts directory."""
    if clean_artifacts_dir:
        return ArtifactValidator(artifacts_dir=clean_artifacts_dir)
    return None


@pytest.fixture
def isolated_artifact_validator(isolated_artifacts_dir: Path) -> ArtifactValidator:
    """Provide an ArtifactValidator for the isolated temp artifacts directory."""
    return ArtifactValidator(artifacts_dir=isolated_artifacts_dir)


# =============================================================================
# Checkpoint Validation Helper
# =============================================================================


@dataclass
class CheckpointValidator:
    """Helper class for validating execution checkpoints.

    Provides methods to verify checkpoint creation at each execution stage.
    """

    def validate_checkpoints(
        self,
        checkpoints: list,
        required_labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Validate checkpoints contain required labels.

        Args:
            checkpoints: List of checkpoint objects
            required_labels: List of required checkpoint labels

        Returns:
            Dict with validation results
        """
        labels = [cp.label for cp in checkpoints]

        result = {
            "total_checkpoints": len(checkpoints),
            "labels": labels,
            "missing_labels": [],
            "is_valid": True,
        }

        if required_labels:
            for label in required_labels:
                # Handle prefix matching for dynamic labels like "candidate:*"
                if label.endswith(":*"):
                    prefix = label[:-1]  # Remove the "*"
                    if not any(lbl.startswith(prefix) for lbl in labels if lbl):
                        result["missing_labels"].append(label)
                elif label not in labels:
                    result["missing_labels"].append(label)

            result["is_valid"] = len(result["missing_labels"]) == 0

        return result

    def get_checkpoint_state(
        self,
        checkpoints: list,
        label: str,
    ) -> dict[str, Any] | None:
        """Get the state data from a specific checkpoint.

        Args:
            checkpoints: List of checkpoint objects
            label: The checkpoint label to find

        Returns:
            The checkpoint state dict or None if not found
        """
        for cp in checkpoints:
            if cp.label == label:
                return cp.state
        return None

    def validate_start_checkpoint(self, checkpoints: list) -> bool:
        """Validate the 'start' checkpoint exists with required fields."""
        state = self.get_checkpoint_state(checkpoints, "start")
        if not state:
            return False

        return all(key in state for key in ["input_payload", "model_config", "subagents"])

    def validate_decision_checkpoint(self, checkpoints: list) -> bool:
        """Validate the 'decision' checkpoint exists with required fields."""
        state = self.get_checkpoint_state(checkpoints, "decision")
        if not state:
            return False

        return all(key in state for key in ["decision_id", "candidate_id", "judge_model_name"])


@pytest.fixture
def checkpoint_validator() -> CheckpointValidator:
    """Provide a CheckpointValidator instance."""
    return CheckpointValidator()


# =============================================================================
# Sprint Workflow Helper
# =============================================================================


@dataclass
class SprintWorkflowHelper:
    """Helper class for testing complete sprint workflows.

    Combines planning interview, sprint creation, and execution.
    """

    spec_service: SpecService
    sprint_service: SprintService
    db_session: AsyncSession
    planning_helper: PlanningInterviewHelper

    async def create_sprint_from_spec(
        self,
        spec: Spec,
        name: str | None = None,
    ) -> Sprint:
        """Create a sprint linked to a spec.

        Args:
            spec: The spec to link
            name: Optional sprint name (defaults to spec title)

        Returns:
            The created sprint
        """
        sprint = await self.sprint_service.create(
            SprintCreate(
                name=name or f"Sprint: {spec.title}",
                goal=spec.task,
                spec_id=spec.id,
            )
        )
        await self.db_session.commit()
        return sprint

    async def setup_hello_world_sprint(
        self,
        task: str = "Create a Python script that prints 'hello world' to the console.",
        title: str = "Hello World Integration Test",
        max_questions: int = 3,
    ) -> tuple[Spec, Sprint, dict]:
        """Set up a complete hello world sprint with planning.

        Args:
            task: The task description
            title: The spec/sprint title
            max_questions: Max planning questions

        Returns:
            Tuple of (spec, sprint, planning_dict)
        """
        # Complete planning
        spec, planning = await self.planning_helper.complete_planning(
            task=task,
            title=title,
            max_questions=max_questions,
            custom_answers={
                "hello": "The script should print exactly 'hello world' on a single line.",
            },
        )

        # Create sprint
        sprint = await self.create_sprint_from_spec(spec, f"{title} Sprint")

        return spec, sprint, planning


@pytest.fixture
def sprint_workflow_helper(
    spec_service: SpecService,
    sprint_service: SprintService,
    db_session: AsyncSession,
    planning_interview_helper: PlanningInterviewHelper,
) -> SprintWorkflowHelper:
    """Provide a SprintWorkflowHelper instance."""
    return SprintWorkflowHelper(
        spec_service=spec_service,
        sprint_service=sprint_service,
        db_session=db_session,
        planning_helper=planning_interview_helper,
    )


# =============================================================================
# Test Data Cleanup Fixture
# =============================================================================


@pytest.fixture
async def cleanup_test_data(db_session: AsyncSession):
    """Fixture that tracks and cleans up test data.

    Usage:
        def test_something(cleanup_test_data):
            spec_id = ...  # create spec
            cleanup_test_data['specs'].append(spec_id)
    """
    data = {
        "specs": [],
        "sprints": [],
        "runs": [],
    }
    yield data

    # Cleanup is handled by transaction rollback in db_session fixture
    # This is mainly for tests that need to track created IDs
