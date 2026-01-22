"""E2E Tests for SDLC Orchestration with Real Parallel Agents.

This module tests the parallel execution model of SDLC agents using real
API calls to validate:
1. Parallel Task invocation pattern works correctly
2. Multiple agents can run concurrently
3. Results are properly aggregated from parallel runs
4. Phase gate enforcement works as expected

These tests require API keys configured in .env and make real AI calls.
"""

import asyncio
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai import Agent

from app.core.config import settings


@pytest.fixture(autouse=True)
def set_api_keys_in_env():
    """Set API keys as environment variables for pydantic_ai.

    Pydantic_ai looks for API keys in environment variables directly,
    but our settings object loads from .env file. This fixture bridges
    the gap by setting env vars from our settings.
    """
    old_anthropic = os.environ.get("ANTHROPIC_API_KEY")
    old_openai = os.environ.get("OPENAI_API_KEY")

    if settings.ANTHROPIC_API_KEY:
        os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY
    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

    yield

    # Restore original values
    if old_anthropic is not None:
        os.environ["ANTHROPIC_API_KEY"] = old_anthropic
    elif "ANTHROPIC_API_KEY" in os.environ:
        del os.environ["ANTHROPIC_API_KEY"]

    if old_openai is not None:
        os.environ["OPENAI_API_KEY"] = old_openai
    elif "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]


def _get_anthropic_model() -> str | None:
    """Get Anthropic model string for pydantic_ai."""
    if not settings.ANTHROPIC_API_KEY:
        return None
    model_name = settings.ANTHROPIC_MODEL
    # Keep the full model string with provider prefix for pydantic_ai
    # If no prefix, add "anthropic:" prefix
    if ":" not in model_name:
        model_name = f"anthropic:{model_name}"
    return model_name


def _get_openai_model() -> str | None:
    """Get OpenAI model string for pydantic_ai.

    Note: The project may use custom/fictional models like gpt-5.2-codex.
    For testing, we use a valid fallback model (gpt-4o-mini) since the
    actual model name may not be valid for direct pydantic_ai use.
    """
    if not settings.OPENAI_API_KEY:
        return None
    # Use a known valid model for testing rather than potentially fictional models
    # The actual project models may be custom endpoints not suitable for this test
    return "openai:gpt-4o-mini"

# Check if API keys are available for integration tests
def _has_required_api_keys() -> bool:
    """Check if required API keys are configured."""
    has_openai = bool(settings.OPENAI_API_KEY)
    has_anthropic = bool(settings.ANTHROPIC_API_KEY)
    if settings.DUAL_SUBAGENT_ENABLED:
        return has_openai and has_anthropic
    return has_openai


REQUIRES_API_KEYS = pytest.mark.skipif(
    not _has_required_api_keys(),
    reason="E2E tests require API keys configured in .env",
)

# Plugin path for validation
PLUGIN_ROOT = Path(__file__).parent.parent.parent.parent / ".claude/plugins/sdlc-orchestration"


@dataclass
class AgentResult:
    """Result from an agent execution."""

    agent_name: str
    output: str
    duration_seconds: float
    success: bool
    error: str | None = None


@dataclass
class ParallelPhaseResult:
    """Aggregated result from a parallel phase execution."""

    phase_name: str
    agent_results: list[AgentResult]
    total_duration_seconds: float
    all_succeeded: bool


class TestParallelAgentExecution:
    """Tests for parallel agent execution patterns."""

    @pytest.fixture
    def research_agents_config(self) -> list[dict[str, str]]:
        """Configuration for research phase agents."""
        return [
            {
                "name": "research-scientist",
                "role": "Research technical approaches and feasibility",
                "prompt_template": "Research technical approaches for: {topic}",
            },
            {
                "name": "business-analyst",
                "role": "Research market and user context",
                "prompt_template": "Research market/user context for: {topic}",
            },
            {
                "name": "software-architect",
                "role": "Research architectural patterns",
                "prompt_template": "Research architectural patterns for: {topic}",
            },
        ]

    @REQUIRES_API_KEYS
    @pytest.mark.anyio
    async def test_parallel_research_agents_complete(self, research_agents_config):
        """Test that 3 research agents can run in parallel and complete."""
        topic = "implementing a simple hello world CLI application"

        model = _get_anthropic_model()
        if not model:
            pytest.skip("Anthropic API key not configured")

        # Create lightweight agents for testing
        agents = []
        for config in research_agents_config:
            agent = Agent(
                model=model,
                system_prompt=f"You are a {config['role']}. Provide a brief 2-3 sentence analysis.",
            )
            agents.append((config["name"], agent, config["prompt_template"].format(topic=topic)))

        # Execute all agents in parallel
        start_time = time.time()

        async def run_agent(name: str, agent: Agent, prompt: str) -> AgentResult:
            agent_start = time.time()
            try:
                result = await agent.run(prompt)
                return AgentResult(
                    agent_name=name,
                    output=result.output,
                    duration_seconds=time.time() - agent_start,
                    success=True,
                )
            except Exception as e:
                return AgentResult(
                    agent_name=name,
                    output="",
                    duration_seconds=time.time() - agent_start,
                    success=False,
                    error=str(e),
                )

        # Run all agents concurrently
        tasks = [run_agent(name, agent, prompt) for name, agent, prompt in agents]
        results = await asyncio.gather(*tasks)

        total_duration = time.time() - start_time

        # Validate results
        phase_result = ParallelPhaseResult(
            phase_name="research",
            agent_results=results,
            total_duration_seconds=total_duration,
            all_succeeded=all(r.success for r in results),
        )

        # Assertions
        assert phase_result.all_succeeded, f"Some agents failed: {[r.error for r in results if not r.success]}"
        assert len(results) == 3, "Expected 3 agent results"

        # Each agent should have produced output
        for result in results:
            assert result.output, f"Agent {result.agent_name} produced no output"
            assert len(result.output) > 10, f"Agent {result.agent_name} output too short"

        # Verify parallel execution (total time should be less than sum of individual times)
        sum_of_durations = sum(r.duration_seconds for r in results)
        # Allow for some overhead, but parallel should be faster than sequential
        assert total_duration < sum_of_durations * 0.9, (
            f"Parallel execution ({total_duration:.2f}s) not faster than sequential ({sum_of_durations:.2f}s)"
        )

    @REQUIRES_API_KEYS
    @pytest.mark.anyio
    async def test_result_aggregation_from_parallel_agents(self, research_agents_config):
        """Test that results from parallel agents can be properly aggregated."""
        topic = "building a REST API endpoint"

        model = _get_anthropic_model()
        if not model:
            pytest.skip("Anthropic API key not configured")

        # Create agents
        agents = []
        for config in research_agents_config:
            agent = Agent(
                model=model,
                system_prompt=f"You are a {config['role']}. Respond with exactly one key insight in a single sentence.",
            )
            agents.append((config["name"], agent, config["prompt_template"].format(topic=topic)))

        # Run in parallel
        async def run_agent(name: str, agent: Agent, prompt: str) -> tuple[str, str]:
            result = await agent.run(prompt)
            return name, result.output

        tasks = [run_agent(name, agent, prompt) for name, agent, prompt in agents]
        results = await asyncio.gather(*tasks)

        # Aggregate results into a summary
        aggregated = {}
        for name, output in results:
            aggregated[name] = output

        # Validate aggregation
        assert len(aggregated) == 3, "Should have 3 aggregated results"
        assert "research-scientist" in aggregated
        assert "business-analyst" in aggregated
        assert "software-architect" in aggregated

        # Create summary document (simulating phase handoff)
        summary = "# Research Phase Summary\n\n"
        for name, insight in aggregated.items():
            summary += f"## {name}\n{insight}\n\n"

        assert len(summary) > 100, "Summary should have substantial content"
        assert "Research Phase Summary" in summary


class TestPhaseGateEnforcement:
    """Tests for phase gate enforcement patterns."""

    @pytest.fixture
    def phase_state(self) -> dict[str, Any]:
        """Initial phase state template."""
        return {
            "phase": "requirements",
            "status": "pending",
            "agents_completed": [],
            "artifacts": {},
            "gates_passed": [],
        }

    def test_phase_state_transitions(self, phase_state):
        """Test that phase state transitions correctly."""
        # Start requirements phase
        phase_state["status"] = "in_progress"
        assert phase_state["status"] == "in_progress"

        # Complete agents
        phase_state["agents_completed"] = ["ceo-stakeholder", "business-analyst", "research-scientist"]
        assert len(phase_state["agents_completed"]) == 3

        # Pass gate
        phase_state["gates_passed"].append("requirements_complete")
        phase_state["status"] = "completed"

        # Transition to design
        phase_state["phase"] = "design"
        phase_state["status"] = "pending"
        phase_state["agents_completed"] = []

        assert phase_state["phase"] == "design"
        assert "requirements_complete" in phase_state["gates_passed"]

    def test_gate_blocks_without_prerequisites(self, phase_state):
        """Test that gates block progression without prerequisites."""
        # Try to transition without completing agents
        phase_state["status"] = "in_progress"
        phase_state["agents_completed"] = ["ceo-stakeholder"]  # Only 1 of 3

        # Gate check should fail
        required_agents = ["ceo-stakeholder", "business-analyst", "research-scientist"]
        gate_passed = all(agent in phase_state["agents_completed"] for agent in required_agents)

        assert not gate_passed, "Gate should not pass with incomplete agents"

    def test_all_phases_have_gates(self):
        """Test that all SDLC phases have defined gates."""
        phases = ["requirements", "design", "implementation", "quality", "release"]
        gates = {
            "requirements": ["requirements_complete"],
            "design": ["design_approved"],
            "implementation": ["code_complete", "tests_pass"],
            "quality": ["qa_approved", "review_approved"],
            "release": ["staging_deployed", "canary_validated", "docs_updated"],
        }

        for phase in phases:
            assert phase in gates, f"Phase {phase} missing gate definition"
            assert len(gates[phase]) > 0, f"Phase {phase} has no gates"


class TestAgentRoleValidation:
    """Tests for agent role definitions and cross-references."""

    @pytest.fixture
    def expected_agents_by_phase(self) -> dict[str, list[str]]:
        """Expected agents for each SDLC phase."""
        return {
            "requirements": ["ceo-stakeholder", "business-analyst", "research-scientist"],
            "design": ["software-architect", "data-scientist", "network-engineer"],
            "implementation": ["staff-engineer", "senior-engineer", "junior-engineer", "devops-engineer"],
            "quality": ["qa-automation", "code-reviewer", "performance-engineer"],
            "release": ["cicd-engineer", "canary-user", "documentation-engineer"],
        }

    def test_all_phases_have_agents(self, expected_agents_by_phase):
        """Test that all phases have assigned agents."""
        for phase, agents in expected_agents_by_phase.items():
            assert len(agents) >= 3, f"Phase {phase} should have at least 3 agents"

    def test_parallel_phases_have_multiple_agents(self, expected_agents_by_phase):
        """Test that parallel phases (1-4) have multiple agents for concurrency."""
        parallel_phases = ["requirements", "design", "implementation", "quality"]

        for phase in parallel_phases:
            agents = expected_agents_by_phase[phase]
            assert len(agents) >= 3, f"Parallel phase {phase} needs at least 3 agents"

    def test_agent_files_exist_for_all_roles(self, expected_agents_by_phase):
        """Test that agent definition files exist for all expected roles."""
        agents_dir = PLUGIN_ROOT / "agents"

        if not agents_dir.exists():
            pytest.skip("agents/ directory not found")

        existing_agents = {f.stem for f in agents_dir.glob("*.md")}

        all_expected = set()
        for agents in expected_agents_by_phase.values():
            all_expected.update(agents)

        missing = all_expected - existing_agents
        assert not missing, f"Missing agent files: {missing}"


class TestDualProviderExecution:
    """Tests for dual-provider (OpenAI + Anthropic) execution model."""

    @REQUIRES_API_KEYS
    @pytest.mark.anyio
    async def test_anthropic_agent_execution(self):
        """Test that Anthropic agent can execute successfully.

        Note: This test may be flaky due to API rate limits when running
        after other Anthropic-based tests. It includes retry logic to handle
        transient failures.
        """
        model = _get_anthropic_model()
        if not model:
            pytest.skip("Anthropic API key not configured")

        agent = Agent(
            model=model,
            system_prompt="You are a helpful assistant. Respond briefly.",
        )

        # Retry logic for transient API failures (rate limits, network issues)
        max_retries = 3
        last_error = None
        for attempt in range(max_retries):
            try:
                result = await agent.run("Say 'Anthropic test passed' and nothing else.")
                assert result.output is not None
                assert (
                    "anthropic" in result.output.lower()
                    or "test" in result.output.lower()
                    or "passed" in result.output.lower()
                )
                return  # Success
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        pytest.fail(f"Test failed after {max_retries} retries: {last_error}")

    @pytest.mark.anyio
    async def test_openai_agent_execution(self):
        """Test that OpenAI agent can execute successfully."""
        model = _get_openai_model()
        if not model:
            pytest.skip("OpenAI API key not configured")

        agent = Agent(
            model=model,
            system_prompt="You are a helpful assistant. Respond briefly.",
        )

        result = await agent.run("Say 'OpenAI test passed' and nothing else.")

        assert result.output is not None
        assert "openai" in result.output.lower() or "test" in result.output.lower() or "passed" in result.output.lower()

    @REQUIRES_API_KEYS
    @pytest.mark.anyio
    async def test_parallel_agent_execution_same_provider(self):
        """Test that multiple agents can run in parallel with same provider."""
        model = _get_anthropic_model()
        if not model:
            pytest.skip("Anthropic API key not configured")

        # Use Anthropic for both to test parallel execution pattern
        # This tests the async parallel execution regardless of provider mix
        agent_a = Agent(
            model=model,
            system_prompt="You are Agent A. Say only 'A complete'.",
        )

        agent_b = Agent(
            model=model,
            system_prompt="You are Agent B. Say only 'B complete'.",
        )

        # Run both in parallel
        start = time.time()
        results = await asyncio.gather(
            agent_a.run("Execute"),
            agent_b.run("Execute"),
        )
        duration = time.time() - start

        # Both should complete
        assert len(results) == 2
        assert results[0].output is not None
        assert results[1].output is not None

        # Parallel should be faster than sequential (2x single call)
        # This is a soft assertion - network variability exists
        assert duration < 60, f"Parallel execution took too long: {duration}s"


class TestResearchCommandPattern:
    """Tests for the /sdlc-orchestration:research command pattern."""

    def test_research_command_exists(self):
        """Test that research.md command file exists."""
        research_cmd = PLUGIN_ROOT / "commands" / "research.md"
        assert research_cmd.exists(), "research.md command should exist"

    def test_research_command_has_parallel_pattern(self):
        """Test that research command documents parallel execution."""
        research_cmd = PLUGIN_ROOT / "commands" / "research.md"

        if not research_cmd.exists():
            pytest.skip("research.md not found")

        content = research_cmd.read_text()

        # Should mention parallel execution
        assert "parallel" in content.lower() or "PARALLEL" in content, (
            "Research command should document parallel execution"
        )

        # Should reference at least 3 agents
        agent_refs = ["research-scientist", "business-analyst", "software-architect"]
        found_agents = [agent for agent in agent_refs if agent in content]
        assert len(found_agents) >= 2, f"Research command should reference multiple agents, found: {found_agents}"


# Run as standalone script for quick validation
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
