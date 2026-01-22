# Evaluator-Optimizer Pattern

The SDLC orchestration integrates an **Evaluator-Optimizer pattern** based on Anthropic's cookbook patterns for structured evaluation with feedback-driven retry loops.

## Overview

The evaluator-optimizer pattern ensures quality gates are enforced automatically by:
1. Running multiple evaluators after each phase
2. Accumulating feedback across retry attempts
3. Escalating to human review after repeated failures

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EVALUATOR-OPTIMIZER FLOW                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐     ┌──────────────────┐                  │
│  │ Phase       │────▶│ Evaluators       │                  │
│  │ Output      │     │ (Deterministic)  │                  │
│  └─────────────┘     │ • Ruff lint      │                  │
│                      │ • Pytest         │                  │
│                      │ • Type check     │                  │
│                      └────────┬─────────┘                  │
│                               │                            │
│                      ┌────────▼─────────┐                  │
│                      │ Pass/Fail        │                  │
│                      │ Decision         │                  │
│                      └────────┬─────────┘                  │
│                               │                            │
│            ┌─────────────────┼─────────────────┐           │
│            │ PASS            │ FAIL            │           │
│            ▼                 ▼                 │           │
│  ┌─────────────────┐  ┌─────────────────┐     │           │
│  │ Proceed to      │  │ FeedbackMemory  │     │           │
│  │ Next Phase      │  │ Update          │     │           │
│  └─────────────────┘  └────────┬────────┘     │           │
│                               │               │           │
│                      ┌────────▼─────────┐     │           │
│                      │ Can Retry?       │     │           │
│                      │ (< 3 attempts)   │     │           │
│                      └────────┬─────────┘     │           │
│                               │               │           │
│            ┌─────────────────┼─────────────┐  │           │
│            │ YES             │ NO          │  │           │
│            ▼                 ▼             │  │           │
│  ┌─────────────────┐  ┌─────────────────┐  │  │           │
│  │ Retry with      │  │ Escalate to     │  │  │           │
│  │ Feedback        │  │ Human Review    │  │  │           │
│  └─────────────────┘  └─────────────────┘  │  │           │
│                                            │  │           │
└────────────────────────────────────────────┴──┴───────────┘
```

## Components

### 1. Evaluator Protocol

All evaluators implement a common interface:

```python
class Evaluator(Protocol):
    """Protocol for phase output evaluators."""

    @property
    def name(self) -> str: ...

    @property
    def category(self) -> EvaluationCategory: ...

    @property
    def is_deterministic(self) -> bool: ...

    async def evaluate(
        self,
        phase_output: str,
        context: dict[str, Any],
    ) -> EvaluationResult: ...
```

### 2. EvaluationResult

Structured result from each evaluator:

```python
class EvaluationResult(BaseModel):
    evaluator_name: str
    category: EvaluationCategory  # functionality, correctness, security, etc.
    passed: bool
    score: float  # 0.0 to 1.0
    feedback: str  # Human-readable summary
    criteria: list[CriterionResult]  # Individual checks
    suggestions: list[str]  # Improvement recommendations
```

### 3. FeedbackMemory

Tracks retry history with exponentially increasing context:

```python
@dataclass
class FeedbackMemory:
    sprint_id: UUID
    phase: str
    original_goal: str
    max_attempts: int = 3
    attempts: list[AttemptRecord] = field(default_factory=list)
    accumulated_insights: dict[str, Any] = field(default_factory=dict)
    escalated: bool = False
    escalation_reason: str | None = None
```

**Context Escalation:**
- Attempt 1: Original task only
- Attempt 2: Original task + attempt 1 feedback
- Attempt 3: Original task + all previous feedback + detailed analysis

### 4. EvaluatorRegistry

Manages evaluators by phase:

```python
registry = create_default_registry()

# Get all evaluators for a phase
evaluators = registry.get_evaluators("verification")

# Get only deterministic evaluators (fast)
deterministic = registry.get_deterministic_evaluators("verification")

# Get only LLM-based evaluators (deeper analysis)
llm_based = registry.get_llm_evaluators("verification")
```

## Available Evaluators

### Deterministic Evaluators

| Evaluator | Category | Phases | What It Checks |
|-----------|----------|--------|----------------|
| `RuffLintEvaluator` | Correctness | All | Python linting (ruff check) |
| `PytestEvaluator` | Functionality | Verification, Coding | Test execution, pass/fail |
| `TypeCheckEvaluator` | Correctness | Coding | Type validation (pyright/mypy) |

### LLM-Based Evaluators (Planned)

| Evaluator | Category | What It Checks |
|-----------|----------|----------------|
| `CompletenessEvaluator` | Completeness | All requirements addressed |
| `SecurityEvaluator` | Security | OWASP vulnerabilities |
| `PerformanceEvaluator` | Performance | Efficiency patterns |

## Integration with PhaseRunner

The evaluator system is integrated into the PhaseRunner's verification phase:

```python
# In PhaseRunner.start()
eval_results = await cls.evaluate_phase_output(
    phase="verification",
    output=output,
    context={"workspace_ref": workspace_ref, "goal": goal},
    deterministic_only=True,  # Fast checks only
)

# Check if all evaluators passed
evaluators_passed = all(r.passed for r in eval_results)

# Both agent AND evaluators must pass
verification_success = agent_verification_success and evaluators_passed
```

## FeedbackMemory Usage

### Creating Memory

```python
feedback_memory = FeedbackMemory(
    sprint_id=sprint_id,
    phase="verification",
    original_goal=goal,
    max_attempts=3,
)
```

### Recording Attempts

```python
attempt = feedback_memory.add_attempt(
    phase_output=output,
    evaluation_results=eval_results,
    trace_id="trace_123",
)
```

### Getting Optimization Context

```python
# For retry prompts
context = feedback_memory.get_optimization_context()
# Returns: {
#     "sprint_id": "...",
#     "phase": "verification",
#     "attempt_number": 2,
#     "previous_feedback": ["Fix linting errors", "Add missing tests"],
#     "previous_score": 0.6,
# }
```

### Generating Prompt Summary

```python
# For inclusion in agent prompts
summary = feedback_memory.get_summary_for_prompt()
# Returns markdown with attempt history and issues to fix
```

### Escalation

```python
if not feedback_memory.can_retry:
    feedback_memory.escalate("Maximum retries exceeded")
    # Human review required
```

## Evaluation Categories

```python
class EvaluationCategory(StrEnum):
    FUNCTIONALITY = "functionality"
    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
```

## Configuration

### Default Registry Setup

```python
def create_default_registry() -> EvaluatorRegistry:
    registry = EvaluatorRegistry()

    # Global evaluators (all phases)
    registry.register(RuffLintEvaluator())

    # Phase-specific evaluators
    registry.register(PytestEvaluator(), phases=["verification", "coding"])
    registry.register(TypeCheckEvaluator(), phases=["coding"])

    return registry
```

### Custom Evaluators

Implement the `Evaluator` protocol:

```python
class CustomEvaluator:
    @property
    def name(self) -> str:
        return "custom-evaluator"

    @property
    def category(self) -> EvaluationCategory:
        return EvaluationCategory.FUNCTIONALITY

    @property
    def is_deterministic(self) -> bool:
        return True  # or False for LLM-based

    async def evaluate(
        self,
        phase_output: str,
        context: dict[str, Any],
    ) -> EvaluationResult:
        # Your evaluation logic
        return EvaluationResult(...)
```

## File Locations

| Component | Path |
|-----------|------|
| Protocol | `backend/app/runners/evaluators/protocol.py` |
| FeedbackMemory | `backend/app/runners/evaluators/feedback_memory.py` |
| Deterministic | `backend/app/runners/evaluators/deterministic.py` |
| Registry | `backend/app/runners/evaluators/registry.py` |
| Tests | `backend/tests/unit/test_evaluators.py` |

## Best Practices

1. **Run deterministic evaluators first** - They're fast and catch obvious issues
2. **Use LLM evaluators sparingly** - They're slower and more expensive
3. **Accumulate feedback** - Don't retry with the same prompt
4. **Escalate early** - 3 retries is often enough; humans are better at ambiguous issues
5. **Log trace IDs** - Every evaluation should be traceable

## References

- [Anthropic Evaluator-Optimizer Cookbook](https://github.com/anthropics/anthropic-cookbook/tree/main/patterns/evaluator_optimizer)
- [FeedbackMemory Design](docs/design/evaluator-optimizer-architecture.md)
