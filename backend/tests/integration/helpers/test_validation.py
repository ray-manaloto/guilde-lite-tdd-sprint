"""Unit tests for validation helper functions.

These tests verify the validation helpers work correctly with mock data
before using them in actual integration tests.
"""

import tempfile
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from tests.integration.helpers.validation import (
    ValidationResult,
    validate_artifact_execution,
    validate_artifact_exists,
    validate_checkpoint_sequence,
    validate_checkpoint_state_content,
    validate_dual_provider_execution,
    validate_dual_provider_from_metadata,
    validate_full_tdd_run,
    validate_judge_selection,
)

# =============================================================================
# Test ValidationResult
# =============================================================================


def test_validation_result_bool_success():
    """ValidationResult should be truthy when successful."""
    result = ValidationResult(success=True, message="Test passed")
    assert result
    assert bool(result) is True


def test_validation_result_bool_failure():
    """ValidationResult should be falsy when failed."""
    result = ValidationResult(success=False, message="Test failed")
    assert not result
    assert bool(result) is False


def test_validation_result_str_format():
    """ValidationResult string should include PASS/FAIL prefix."""
    pass_result = ValidationResult(success=True, message="All good")
    fail_result = ValidationResult(success=False, message="Something wrong")

    assert "[PASS]" in str(pass_result)
    assert "All good" in str(pass_result)
    assert "[FAIL]" in str(fail_result)
    assert "Something wrong" in str(fail_result)


# =============================================================================
# Test validate_dual_provider_execution
# =============================================================================


def _make_candidate(provider: str, model_name: str | None = None):
    """Create a mock candidate object."""
    return SimpleNamespace(
        id=uuid4(),
        provider=provider,
        model_name=model_name or f"{provider}-model-v1",
        output="test output",
        metrics={"duration_ms": 100},
    )


def test_dual_provider_validates_both_present():
    """Should pass when both OpenAI and Anthropic candidates exist."""
    candidates = [
        _make_candidate("openai", "gpt-4"),
        _make_candidate("anthropic", "claude-3"),
    ]
    result = validate_dual_provider_execution(candidates)
    assert result.success
    assert "openai" in result.details["found_providers"]
    assert "anthropic" in result.details["found_providers"]


def test_dual_provider_fails_missing_provider():
    """Should fail when a required provider is missing."""
    candidates = [_make_candidate("openai", "gpt-4")]
    result = validate_dual_provider_execution(candidates)
    assert not result.success
    assert "anthropic" in result.details["missing_providers"]


def test_dual_provider_fails_empty_candidates():
    """Should fail when no candidates provided."""
    result = validate_dual_provider_execution([])
    assert not result.success
    assert "No candidates" in result.message


def test_dual_provider_fails_missing_model_name():
    """Should fail when a candidate is missing model_name."""
    candidates = [
        _make_candidate("openai", "gpt-4"),
        _make_candidate("anthropic", None),  # Missing model_name
    ]
    # Manually clear model_name to simulate missing
    candidates[1].model_name = None
    result = validate_dual_provider_execution(candidates)
    assert not result.success
    assert "model_name" in result.message.lower()


def test_dual_provider_custom_providers():
    """Should validate custom provider list."""
    candidates = [
        _make_candidate("openai", "gpt-4"),
        _make_candidate("openrouter", "mixtral"),
    ]
    result = validate_dual_provider_execution(
        candidates, required_providers=["openai", "openrouter"]
    )
    assert result.success


# =============================================================================
# Test validate_dual_provider_from_metadata
# =============================================================================


def test_dual_provider_metadata_validates():
    """Should pass with valid dual_subagent metadata."""
    metadata = {
        "mode": "dual_subagent",
        "candidates": [{"provider": "openai"}, {"provider": "anthropic"}],
    }
    result = validate_dual_provider_from_metadata(metadata)
    assert result.success


def test_dual_provider_metadata_fails_wrong_mode():
    """Should fail when mode is not dual_subagent."""
    metadata = {"mode": "single", "candidates": []}
    result = validate_dual_provider_from_metadata(metadata)
    assert not result.success
    assert "mode" in result.message.lower()


# =============================================================================
# Test validate_judge_selection
# =============================================================================


def _make_decision(model_name: str | None = "judge-model", rationale: str | None = "Good choice"):
    """Create a mock decision object."""
    return SimpleNamespace(
        id=uuid4(),
        candidate_id=uuid4(),
        model_name=model_name,
        rationale=rationale,
        score=0.9,
    )


def test_judge_selection_validates():
    """Should pass with valid decision."""
    decision = _make_decision()
    result = validate_judge_selection(decision)
    assert result.success
    assert "judge_info" in result.details


def test_judge_selection_fails_no_decision():
    """Should fail when no decision provided."""
    result = validate_judge_selection(None)
    assert not result.success
    assert "No judge decision" in result.message


def test_judge_selection_fails_missing_model_name():
    """Should fail when decision missing model_name."""
    decision = _make_decision(model_name=None)
    result = validate_judge_selection(decision)
    assert not result.success
    assert "model_name" in result.message.lower()


def test_judge_selection_fails_missing_rationale():
    """Should fail when decision missing rationale."""
    decision = _make_decision(rationale=None)
    result = validate_judge_selection(decision)
    assert not result.success
    assert "rationale" in result.message.lower()


def test_judge_selection_includes_selected_candidate():
    """Should include selected candidate info when candidates provided."""
    candidate_id = uuid4()
    decision = SimpleNamespace(
        id=uuid4(),
        candidate_id=candidate_id,
        model_name="judge-model",
        rationale="Best answer",
        score=0.95,
    )
    candidates = [
        SimpleNamespace(id=candidate_id, provider="openai", model_name="gpt-4", output="answer"),
    ]
    result = validate_judge_selection(decision, candidates)
    assert result.success
    judge_info = result.details["judge_info"]
    assert judge_info.selected_candidate is not None
    assert judge_info.selected_candidate.provider == "openai"


# =============================================================================
# Test validate_checkpoint_sequence
# =============================================================================


def _make_checkpoint(sequence: int, label: str, state: dict | None = None):
    """Create a mock checkpoint object."""
    return SimpleNamespace(
        id=uuid4(),
        sequence=sequence,
        label=label,
        state=state or {},
        workspace_ref=None,
    )


def test_checkpoint_sequence_validates():
    """Should pass with valid checkpoint sequence."""
    checkpoints = [
        _make_checkpoint(0, "start"),
        _make_checkpoint(1, "candidate:openai"),
        _make_checkpoint(2, "candidate:anthropic"),
        _make_checkpoint(3, "decision"),
    ]
    result = validate_checkpoint_sequence(checkpoints)
    assert result.success


def test_checkpoint_sequence_fails_missing_start():
    """Should fail when start checkpoint missing."""
    checkpoints = [
        _make_checkpoint(1, "candidate:openai"),
        _make_checkpoint(2, "decision"),
    ]
    result = validate_checkpoint_sequence(checkpoints, expected_labels=["start", "decision"])
    assert not result.success
    assert "start" in result.details["missing_labels"]


def test_checkpoint_sequence_prefix_matching():
    """Should match prefix patterns like 'candidate:'."""
    checkpoints = [
        _make_checkpoint(0, "start"),
        _make_checkpoint(1, "candidate:openai"),  # Matches "candidate:" prefix
        _make_checkpoint(2, "decision"),
    ]
    result = validate_checkpoint_sequence(
        checkpoints, expected_labels=["start", "candidate:", "decision"]
    )
    assert result.success


def test_checkpoint_sequence_strict_order():
    """Should fail when checkpoints out of order with strict_order=True."""
    checkpoints = [
        _make_checkpoint(0, "decision"),  # Out of order
        _make_checkpoint(1, "start"),
        _make_checkpoint(2, "candidate:openai"),
    ]
    result = validate_checkpoint_sequence(
        checkpoints,
        expected_labels=["start", "candidate:", "decision"],
        strict_order=True,
    )
    assert not result.success
    assert "order" in result.message.lower()


def test_checkpoint_sequence_empty():
    """Should fail with empty checkpoints."""
    result = validate_checkpoint_sequence([])
    assert not result.success
    assert "No checkpoints" in result.message


# =============================================================================
# Test validate_checkpoint_state_content
# =============================================================================


def test_checkpoint_state_validates():
    """Should pass when state contains required keys."""
    checkpoints = [
        _make_checkpoint(0, "start", {"input": "test", "timestamp": 123}),
    ]
    result = validate_checkpoint_state_content(checkpoints, "start", ["input", "timestamp"])
    assert result.success


def test_checkpoint_state_fails_missing_key():
    """Should fail when state missing required key."""
    checkpoints = [_make_checkpoint(0, "start", {"input": "test"})]
    result = validate_checkpoint_state_content(checkpoints, "start", ["input", "missing_key"])
    assert not result.success
    assert "missing_key" in result.details["missing_keys"]


def test_checkpoint_state_fails_label_not_found():
    """Should fail when checkpoint label not found."""
    checkpoints = [_make_checkpoint(0, "start", {})]
    result = validate_checkpoint_state_content(checkpoints, "nonexistent", ["key"])
    assert not result.success
    assert "not found" in result.message.lower()


# =============================================================================
# Test validate_artifact_execution
# =============================================================================


def test_artifact_execution_validates():
    """Should pass when script executes and outputs expected text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a hello.py script
        script_path = Path(tmpdir) / "hello.py"
        script_path.write_text('print("hello world")')

        result = validate_artifact_execution(tmpdir, "hello.py")

        assert result.success
        assert result.file_path == script_path
        assert result.return_code == 0
        assert "hello world" in result.stdout.lower()


def test_artifact_execution_fails_missing_file():
    """Should fail when file not found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = validate_artifact_execution(tmpdir, "nonexistent.py")
        assert not result.success
        assert "not found" in result.message.lower()


def test_artifact_execution_fails_script_error():
    """Should fail when script returns non-zero exit code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "bad.py"
        script_path.write_text("raise Exception('error')")

        result = validate_artifact_execution(tmpdir, "bad.py")

        assert not result.success
        assert result.return_code != 0


def test_artifact_execution_fails_wrong_output():
    """Should fail when output doesn't contain expected text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "hello.py"
        script_path.write_text('print("goodbye world")')

        result = validate_artifact_execution(tmpdir, "hello.py", expected_output="hello world")

        assert not result.success
        assert "not found" in result.message.lower()


def test_artifact_execution_case_insensitive():
    """Should match case-insensitively by default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "hello.py"
        script_path.write_text('print("HELLO WORLD")')

        result = validate_artifact_execution(tmpdir, "hello.py", expected_output="hello world")

        assert result.success


def test_artifact_execution_case_sensitive():
    """Should fail case-sensitive match when case doesn't match."""
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "hello.py"
        script_path.write_text('print("HELLO WORLD")')

        result = validate_artifact_execution(
            tmpdir, "hello.py", expected_output="hello world", case_sensitive=True
        )

        assert not result.success


# =============================================================================
# Test validate_artifact_exists
# =============================================================================


def test_artifact_exists_validates():
    """Should pass when file exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.py"
        file_path.write_text("# test file")

        result = validate_artifact_exists(tmpdir, "test.py")

        assert result.success
        assert "test.py" in result.details["file_path"]


def test_artifact_exists_with_content():
    """Should validate required content is present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.py"
        file_path.write_text('print("special content")')

        result = validate_artifact_exists(tmpdir, "test.py", required_content="special content")

        assert result.success


def test_artifact_exists_fails_missing_content():
    """Should fail when required content not present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.py"
        file_path.write_text("print('other content')")

        result = validate_artifact_exists(tmpdir, "test.py", required_content="missing")

        assert not result.success
        assert "missing" in result.message.lower()


# =============================================================================
# Test validate_full_tdd_run
# =============================================================================


def test_full_tdd_run_validates():
    """Should pass when all validations succeed."""
    candidates = [
        _make_candidate("openai", "gpt-4"),
        _make_candidate("anthropic", "claude-3"),
    ]
    decision = _make_decision()
    checkpoints = [
        _make_checkpoint(0, "start"),
        _make_checkpoint(1, "candidate:openai"),
        _make_checkpoint(2, "candidate:anthropic"),
        _make_checkpoint(3, "decision"),
    ]

    result = validate_full_tdd_run(candidates, decision, checkpoints)

    assert result.success
    assert "validation_results" in result.details


def test_full_tdd_run_fails_on_dual_provider():
    """Should fail when dual-provider validation fails."""
    candidates = [_make_candidate("openai", "gpt-4")]  # Missing anthropic
    decision = _make_decision()
    checkpoints = [_make_checkpoint(0, "start")]

    result = validate_full_tdd_run(candidates, decision, checkpoints)

    assert not result.success
    assert "Dual-provider" in result.message


def test_full_tdd_run_fails_on_judge():
    """Should fail when judge validation fails."""
    candidates = [
        _make_candidate("openai", "gpt-4"),
        _make_candidate("anthropic", "claude-3"),
    ]
    decision = _make_decision(model_name=None)  # Invalid decision
    checkpoints = [_make_checkpoint(0, "start")]

    result = validate_full_tdd_run(candidates, decision, checkpoints)

    assert not result.success
    assert "Judge" in result.message
