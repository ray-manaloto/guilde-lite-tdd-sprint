"""Validation helper functions for integration tests.

These helpers provide reusable validation logic for testing the sprint
interview-to-code workflow, including dual-provider execution, judge
selection, checkpoint sequences, and artifact execution validation.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.schemas.agent_run import AgentCandidateRead, AgentCheckpointRead, AgentDecisionRead

# =============================================================================
# Result Types
# =============================================================================


@dataclass
class ValidationResult:
    """Result of a validation check."""

    success: bool
    message: str
    details: dict[str, Any] | None = None

    def __bool__(self) -> bool:
        """Allow using result in boolean context."""
        return self.success

    def __str__(self) -> str:
        """String representation for debugging."""
        status = "PASS" if self.success else "FAIL"
        return f"[{status}] {self.message}"


@dataclass
class CandidateInfo:
    """Information about a candidate from validation."""

    provider: str
    model_name: str | None
    candidate_id: str | None
    output: str | None = None
    metrics: dict[str, Any] | None = None


@dataclass
class JudgeSelectionInfo:
    """Information about judge selection."""

    judge_model_name: str | None
    rationale: str | None
    selected_candidate: CandidateInfo | None
    score: float | None = None


@dataclass
class ArtifactExecutionResult:
    """Result of artifact execution validation."""

    success: bool
    message: str
    file_path: Path | None = None
    file_content: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    return_code: int | None = None


# =============================================================================
# Dual-Provider Execution Validation
# =============================================================================


def validate_dual_provider_execution(
    candidates: list[AgentCandidateRead],
    required_providers: list[str] | None = None,
) -> ValidationResult:
    """Verify both OpenAI and Anthropic candidates exist.

    Args:
        candidates: List of candidate objects from the TDD run result.
        required_providers: List of provider names to check for.
            Defaults to ["openai", "anthropic"].

    Returns:
        ValidationResult with success status and details about found candidates.

    Example:
        >>> result = validate_dual_provider_execution(tdd_result.candidates)
        >>> assert result.success, result.message
    """
    if required_providers is None:
        required_providers = ["openai", "anthropic"]

    if not candidates:
        return ValidationResult(
            success=False,
            message="No candidates found in result",
            details={"candidates_count": 0, "required_providers": required_providers},
        )

    # Extract provider information from candidates
    found_providers: dict[str, CandidateInfo] = {}
    for candidate in candidates:
        provider = candidate.provider
        if provider:
            found_providers[provider] = CandidateInfo(
                provider=provider,
                model_name=candidate.model_name,
                candidate_id=str(candidate.id) if candidate.id else None,
                output=candidate.output[:200] if candidate.output else None,
                metrics=candidate.metrics,
            )

    # Check for missing providers
    missing_providers = [p for p in required_providers if p not in found_providers]

    if missing_providers:
        return ValidationResult(
            success=False,
            message=f"Missing required providers: {missing_providers}",
            details={
                "found_providers": list(found_providers.keys()),
                "missing_providers": missing_providers,
                "required_providers": required_providers,
                "candidates_count": len(candidates),
            },
        )

    # Verify each found provider has model_name stored
    providers_without_model = []
    for provider, info in found_providers.items():
        if not info.model_name:
            providers_without_model.append(provider)

    if providers_without_model:
        return ValidationResult(
            success=False,
            message=f"Providers missing model_name: {providers_without_model}",
            details={
                "providers_without_model": providers_without_model,
                "found_providers": {
                    p: {"model_name": info.model_name, "has_output": bool(info.output)}
                    for p, info in found_providers.items()
                },
            },
        )

    return ValidationResult(
        success=True,
        message=f"Dual-provider execution validated: {list(found_providers.keys())}",
        details={
            "found_providers": {
                p: {
                    "model_name": info.model_name,
                    "candidate_id": info.candidate_id,
                    "has_output": bool(info.output),
                    "metrics": info.metrics,
                }
                for p, info in found_providers.items()
            },
            "candidates_count": len(candidates),
        },
    )


def validate_dual_provider_from_metadata(
    metadata: dict[str, Any],
    required_providers: list[str] | None = None,
) -> ValidationResult:
    """Validate dual-provider execution from planning interview metadata.

    Args:
        metadata: Metadata dict from planning interview result.
        required_providers: List of provider names to check for.

    Returns:
        ValidationResult with success status and found providers.
    """
    if required_providers is None:
        required_providers = ["openai", "anthropic"]

    mode = metadata.get("mode")
    if mode != "dual_subagent":
        return ValidationResult(
            success=False,
            message=f"Expected mode 'dual_subagent', got '{mode}'",
            details={"mode": mode, "metadata_keys": list(metadata.keys())},
        )

    candidates = metadata.get("candidates", [])
    if not candidates:
        return ValidationResult(
            success=False,
            message="No candidates found in metadata",
            details={"metadata_keys": list(metadata.keys())},
        )

    found_providers = [c.get("provider") for c in candidates]
    missing = [p for p in required_providers if p not in found_providers]

    if missing:
        return ValidationResult(
            success=False,
            message=f"Missing providers in metadata: {missing}",
            details={"found_providers": found_providers, "missing": missing},
        )

    return ValidationResult(
        success=True,
        message=f"Dual-provider metadata validated: {found_providers}",
        details={"found_providers": found_providers, "candidates_count": len(candidates)},
    )


# =============================================================================
# Judge Selection Validation
# =============================================================================


def validate_judge_selection(
    decision: AgentDecisionRead | None,
    candidates: list[AgentCandidateRead] | None = None,
) -> ValidationResult:
    """Verify judge model name recorded and rationale exists.

    Args:
        decision: The AgentDecisionRead from the TDD run result.
        candidates: Optional list of candidates to validate selected candidate.

    Returns:
        ValidationResult with JudgeSelectionInfo in details.

    Example:
        >>> result = validate_judge_selection(tdd_result.decision, tdd_result.candidates)
        >>> if result.success:
        >>>     info = result.details["judge_info"]
        >>>     print(f"Judge selected: {info.selected_candidate.provider}")
    """
    if decision is None:
        return ValidationResult(
            success=False,
            message="No judge decision found in result",
            details={"decision": None},
        )

    # Check for model name
    if not decision.model_name:
        return ValidationResult(
            success=False,
            message="Judge decision missing model_name",
            details={
                "decision_id": str(decision.id) if decision.id else None,
                "has_rationale": bool(decision.rationale),
                "has_candidate_id": bool(decision.candidate_id),
            },
        )

    # Check for rationale
    if not decision.rationale:
        return ValidationResult(
            success=False,
            message="Judge decision missing rationale",
            details={
                "decision_id": str(decision.id) if decision.id else None,
                "model_name": decision.model_name,
                "has_candidate_id": bool(decision.candidate_id),
            },
        )

    # Find selected candidate if candidates provided
    selected_candidate_info: CandidateInfo | None = None
    if candidates and decision.candidate_id:
        for candidate in candidates:
            if candidate.id == decision.candidate_id:
                selected_candidate_info = CandidateInfo(
                    provider=candidate.provider or "unknown",
                    model_name=candidate.model_name,
                    candidate_id=str(candidate.id),
                    output=candidate.output[:200] if candidate.output else None,
                )
                break

    judge_info = JudgeSelectionInfo(
        judge_model_name=decision.model_name,
        rationale=decision.rationale,
        selected_candidate=selected_candidate_info,
        score=decision.score,
    )

    return ValidationResult(
        success=True,
        message=f"Judge selection validated: model={decision.model_name}",
        details={
            "judge_info": judge_info,
            "decision_id": str(decision.id) if decision.id else None,
            "selected_candidate_id": str(decision.candidate_id) if decision.candidate_id else None,
        },
    )


def validate_judge_from_metadata(metadata: dict[str, Any]) -> ValidationResult:
    """Validate judge selection from planning interview metadata.

    Args:
        metadata: Metadata dict from planning interview result.

    Returns:
        ValidationResult with judge info in details.
    """
    judge = metadata.get("judge")
    if not judge:
        return ValidationResult(
            success=False,
            message="No judge metadata found",
            details={"metadata_keys": list(metadata.keys())},
        )

    judge_model = judge.get("model_name")
    if not judge_model:
        return ValidationResult(
            success=False,
            message="Judge metadata missing model_name",
            details={"judge_keys": list(judge.keys())},
        )

    selected = metadata.get("selected_candidate", {})
    selected_provider = selected.get("provider")

    return ValidationResult(
        success=True,
        message=f"Judge metadata validated: model={judge_model}",
        details={
            "judge_model_name": judge_model,
            "selected_provider": selected_provider,
            "selected_candidate": selected,
        },
    )


# =============================================================================
# Checkpoint Sequence Validation
# =============================================================================


def validate_checkpoint_sequence(
    checkpoints: list[AgentCheckpointRead],
    expected_labels: list[str] | None = None,
    strict_order: bool = False,
) -> ValidationResult:
    """Verify checkpoint labels include expected sequence.

    Args:
        checkpoints: List of checkpoint objects from the TDD run result.
        expected_labels: List of labels that must be present.
            Defaults to ["start", "candidate:", "decision"].
        strict_order: If True, labels must appear in the specified order.

    Returns:
        ValidationResult with checkpoint sequence details.

    Example:
        >>> result = validate_checkpoint_sequence(
        >>>     tdd_result.checkpoints,
        >>>     expected_labels=["start", "candidate:openai", "candidate:anthropic", "decision"]
        >>> )
        >>> assert result.success, result.message
    """
    if expected_labels is None:
        expected_labels = ["start", "candidate:", "decision"]

    if not checkpoints:
        return ValidationResult(
            success=False,
            message="No checkpoints found in result",
            details={"checkpoints_count": 0, "expected_labels": expected_labels},
        )

    # Extract labels and sort by sequence
    sorted_checkpoints = sorted(checkpoints, key=lambda cp: cp.sequence)
    actual_labels = [cp.label for cp in sorted_checkpoints if cp.label]

    # Check for expected labels (prefix matching for patterns like "candidate:")
    missing_labels = []
    for expected in expected_labels:
        if expected.endswith(":"):
            # Prefix match - check if any label starts with this prefix
            if not any(label.startswith(expected) for label in actual_labels):
                missing_labels.append(expected)
        else:
            # Exact match
            if expected not in actual_labels:
                missing_labels.append(expected)

    if missing_labels:
        return ValidationResult(
            success=False,
            message=f"Missing expected checkpoint labels: {missing_labels}",
            details={
                "actual_labels": actual_labels,
                "expected_labels": expected_labels,
                "missing_labels": missing_labels,
                "checkpoints_count": len(checkpoints),
            },
        )

    # Validate ordering if strict_order is True
    if strict_order:
        # Build position map for expected labels
        label_positions = {}
        for i, label in enumerate(actual_labels):
            for expected in expected_labels:
                if expected.endswith(":"):
                    if label.startswith(expected) and expected not in label_positions:
                        label_positions[expected] = i
                else:
                    if label == expected:
                        label_positions[expected] = i

        # Check ordering
        prev_pos = -1
        out_of_order = []
        for expected in expected_labels:
            pos = label_positions.get(expected, -1)
            if pos != -1 and pos < prev_pos:
                out_of_order.append(expected)
            prev_pos = max(prev_pos, pos)

        if out_of_order:
            return ValidationResult(
                success=False,
                message=f"Checkpoints out of expected order: {out_of_order}",
                details={
                    "actual_labels": actual_labels,
                    "expected_order": expected_labels,
                    "label_positions": label_positions,
                },
            )

    # Build checkpoint details
    checkpoint_details = []
    for cp in sorted_checkpoints:
        checkpoint_details.append(
            {
                "sequence": cp.sequence,
                "label": cp.label,
                "has_state": bool(cp.state),
                "workspace_ref": cp.workspace_ref,
            }
        )

    return ValidationResult(
        success=True,
        message=f"Checkpoint sequence validated: {len(checkpoints)} checkpoints",
        details={
            "actual_labels": actual_labels,
            "expected_labels": expected_labels,
            "checkpoints_count": len(checkpoints),
            "checkpoint_details": checkpoint_details,
        },
    )


def validate_checkpoint_state_content(
    checkpoints: list[AgentCheckpointRead],
    label: str,
    required_keys: list[str],
) -> ValidationResult:
    """Validate that a specific checkpoint's state contains required keys.

    Args:
        checkpoints: List of checkpoints to search.
        label: The label of the checkpoint to validate.
        required_keys: Keys that must be present in the checkpoint's state.

    Returns:
        ValidationResult with state content details.
    """
    target_checkpoint = None
    for cp in checkpoints:
        if cp.label == label:
            target_checkpoint = cp
            break

    if not target_checkpoint:
        return ValidationResult(
            success=False,
            message=f"Checkpoint with label '{label}' not found",
            details={"available_labels": [cp.label for cp in checkpoints]},
        )

    state = target_checkpoint.state or {}
    missing_keys = [k for k in required_keys if k not in state]

    if missing_keys:
        return ValidationResult(
            success=False,
            message=f"Checkpoint '{label}' missing state keys: {missing_keys}",
            details={
                "label": label,
                "state_keys": list(state.keys()),
                "required_keys": required_keys,
                "missing_keys": missing_keys,
            },
        )

    return ValidationResult(
        success=True,
        message=f"Checkpoint '{label}' state validated",
        details={
            "label": label,
            "state_keys": list(state.keys()),
            "required_keys": required_keys,
        },
    )


# =============================================================================
# Artifact Execution Validation
# =============================================================================


def validate_artifact_execution(
    workspace_path: Path | str,
    filename: str,
    expected_output: str = "hello world",
    case_sensitive: bool = False,
    timeout_seconds: int = 10,
) -> ArtifactExecutionResult:
    """Check file exists, execute Python file, verify output contains expected text.

    Args:
        workspace_path: Path to the workspace directory to search.
        filename: Name of the file to find and execute (e.g., "hello.py").
        expected_output: Text expected in stdout (default: "hello world").
        case_sensitive: Whether output comparison is case-sensitive.
        timeout_seconds: Timeout for script execution.

    Returns:
        ArtifactExecutionResult with execution details.

    Example:
        >>> result = validate_artifact_execution(
        >>>     workspace_path="/tmp/artifacts",
        >>>     filename="hello.py",
        >>>     expected_output="hello world"
        >>> )
        >>> assert result.success, result.message
    """
    workspace = Path(workspace_path) if isinstance(workspace_path, str) else workspace_path

    # Validate workspace exists
    if not workspace.exists():
        return ArtifactExecutionResult(
            success=False,
            message=f"Workspace path does not exist: {workspace}",
        )

    # Search for the file recursively
    found_files = list(workspace.rglob(filename))

    if not found_files:
        # List what files do exist for debugging
        all_files = list(workspace.rglob("*"))
        file_list = [str(f.relative_to(workspace)) for f in all_files[:20]]
        return ArtifactExecutionResult(
            success=False,
            message=f"File '{filename}' not found in {workspace}",
            file_path=None,
            stdout=f"Available files: {file_list}",
        )

    target_file = found_files[0]

    # Read file content
    try:
        file_content = target_file.read_text()
    except Exception as e:
        return ArtifactExecutionResult(
            success=False,
            message=f"Failed to read file: {e}",
            file_path=target_file,
        )

    # Execute the Python file
    try:
        result = subprocess.run(
            ["python3", str(target_file)],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return ArtifactExecutionResult(
            success=False,
            message=f"Script execution timed out after {timeout_seconds} seconds",
            file_path=target_file,
            file_content=file_content,
        )
    except Exception as e:
        return ArtifactExecutionResult(
            success=False,
            message=f"Failed to execute script: {e}",
            file_path=target_file,
            file_content=file_content,
        )

    # Check return code
    if result.returncode != 0:
        return ArtifactExecutionResult(
            success=False,
            message=f"Script exited with non-zero code: {result.returncode}",
            file_path=target_file,
            file_content=file_content,
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
        )

    # Check output contains expected text
    stdout = result.stdout
    expected = expected_output
    if not case_sensitive:
        stdout_check = stdout.lower()
        expected = expected_output.lower()
    else:
        stdout_check = stdout

    if expected not in stdout_check:
        return ArtifactExecutionResult(
            success=False,
            message=f"Expected '{expected_output}' not found in output",
            file_path=target_file,
            file_content=file_content,
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
        )

    return ArtifactExecutionResult(
        success=True,
        message=f"Artifact execution validated: {target_file.name}",
        file_path=target_file,
        file_content=file_content,
        stdout=result.stdout,
        stderr=result.stderr,
        return_code=result.returncode,
    )


def validate_artifact_exists(
    workspace_path: Path | str,
    filename: str,
    required_content: str | None = None,
) -> ValidationResult:
    """Validate that an artifact file exists and optionally contains expected content.

    Args:
        workspace_path: Path to the workspace directory.
        filename: Name of the file to find.
        required_content: Optional string that must be present in file content.

    Returns:
        ValidationResult with file details.
    """
    workspace = Path(workspace_path) if isinstance(workspace_path, str) else workspace_path

    if not workspace.exists():
        return ValidationResult(
            success=False,
            message=f"Workspace does not exist: {workspace}",
        )

    found_files = list(workspace.rglob(filename))

    if not found_files:
        all_files = [str(f.name) for f in workspace.rglob("*.py")][:10]
        return ValidationResult(
            success=False,
            message=f"File '{filename}' not found",
            details={"workspace": str(workspace), "python_files_found": all_files},
        )

    target_file = found_files[0]
    content = target_file.read_text()

    if required_content and required_content not in content:
        return ValidationResult(
            success=False,
            message=f"Required content '{required_content}' not found in {filename}",
            details={
                "file_path": str(target_file),
                "content_preview": content[:500],
            },
        )

    return ValidationResult(
        success=True,
        message=f"Artifact validated: {target_file.name}",
        details={
            "file_path": str(target_file),
            "file_size": len(content),
            "content_preview": content[:200],
        },
    )


# =============================================================================
# Composite Validation Helpers
# =============================================================================


def validate_full_tdd_run(
    candidates: list[AgentCandidateRead],
    decision: AgentDecisionRead | None,
    checkpoints: list[AgentCheckpointRead],
    required_providers: list[str] | None = None,
    expected_checkpoint_labels: list[str] | None = None,
) -> ValidationResult:
    """Perform comprehensive validation of a TDD run result.

    This combines dual-provider, judge selection, and checkpoint validations.

    Args:
        candidates: List of candidates from TDD run.
        decision: Judge decision from TDD run.
        checkpoints: List of checkpoints from TDD run.
        required_providers: Providers that must be present.
        expected_checkpoint_labels: Labels that must be in checkpoints.

    Returns:
        ValidationResult with combined validation details.
    """
    results: dict[str, ValidationResult] = {}

    # Validate dual-provider execution
    dual_result = validate_dual_provider_execution(candidates, required_providers)
    results["dual_provider"] = dual_result
    if not dual_result.success:
        return ValidationResult(
            success=False,
            message=f"Dual-provider validation failed: {dual_result.message}",
            details={"validation_results": results},
        )

    # Validate judge selection
    judge_result = validate_judge_selection(decision, candidates)
    results["judge_selection"] = judge_result
    if not judge_result.success:
        return ValidationResult(
            success=False,
            message=f"Judge selection validation failed: {judge_result.message}",
            details={"validation_results": results},
        )

    # Validate checkpoint sequence
    checkpoint_result = validate_checkpoint_sequence(checkpoints, expected_checkpoint_labels)
    results["checkpoints"] = checkpoint_result
    if not checkpoint_result.success:
        return ValidationResult(
            success=False,
            message=f"Checkpoint validation failed: {checkpoint_result.message}",
            details={"validation_results": results},
        )

    return ValidationResult(
        success=True,
        message="Full TDD run validation passed",
        details={
            "validation_results": {
                name: {"success": r.success, "message": r.message} for name, r in results.items()
            },
            "providers": list((dual_result.details or {}).get("found_providers", {}).keys()),
            "judge_model": (
                (judge_result.details or {})
                .get("judge_info", JudgeSelectionInfo(None, None, None))
                .judge_model_name
            ),
            "checkpoint_count": len(checkpoints),
        },
    )
