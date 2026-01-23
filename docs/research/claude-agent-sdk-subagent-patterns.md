# Research Report: Claude Agent SDK Patterns and Subagent Best Practices

## Executive Summary

This report analyzes Anthropic's Claude Agent SDK cookbooks for best practices on subagent usage, context engineering, and observability. The key findings reveal three distinct patterns for agent construction (stateless, stateful, hierarchical), proven context isolation strategies for subagents, and comprehensive observability approaches using MCP servers and activity tracking. We recommend adopting the hierarchical orchestrator pattern with Opus for coordination and faster models (Haiku/Sonnet) for extraction tasks, implementing cost-efficient tool restriction via `disallowed_tools`, and enhancing our existing Logfire integration with agent-specific metrics.

## Research Question

How can we improve our SDLC workflow's context engineering and ensure subagents work efficiently, while tracking agent costs and performance?

## Methodology

1. Fetched and analyzed three Anthropic cookbook resources:
   - One-liner Research Agent cookbook
   - Observability Agent cookbook
   - Using Sub-Agents Jupyter notebook
2. Reviewed current codebase implementation (`ralph_planner.py`, `sprint_agent.py`, `telemetry.py`)
3. Cross-referenced with installed AI research skills for relevant patterns

---

## Findings

### 1. Agent Construction Patterns (Claude Agent SDK)

The Claude Agent SDK provides three distinct patterns for building agents:

#### Option A: Stateless Query (One-Liner Pattern)
```python
from claude_agent_sdk import ClaudeAgentOptions, query

async for msg in query(
    prompt="Research the latest trends in AI agents",
    options=ClaudeAgentOptions(
        model="claude-opus-4-5",
        allowed_tools=["WebSearch", "Read"]
    ),
):
    print_activity(msg)
```

- **Pros:** Simple, fresh context per query, easy parallelization
- **Cons:** No conversation memory, limited for iterative tasks
- **Feasibility:** High - drop-in replacement for simple research tasks
- **Effort Estimate:** S (2-4 hours)

#### Option B: Stateful Agent (Session Pattern)
```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async with ClaudeSDKClient(
    options=ClaudeAgentOptions(
        model="claude-opus-4-5",
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=["WebSearch", "Read"],
        max_buffer_size=10 * 1024 * 1024,  # 10MB for images
    )
) as agent:
    await agent.query("First query...")
    async for msg in agent.receive_response():
        messages.append(msg)

    # Context preserved for follow-up
    await agent.query("Follow-up query...")
```

- **Pros:** Multi-turn memory, iterative refinement, full context access
- **Cons:** Higher token costs as context accumulates
- **Feasibility:** High - aligns with current `AssistantAgent` pattern
- **Effort Estimate:** M (1-2 days)

#### Option C: Hierarchical Subagent Pattern
```python
# Orchestrator (Opus) generates task-specific prompts
def generate_extraction_prompt(question):
    response = client.messages.create(
        model="claude-opus-4-1",  # Orchestrator
        messages=[{"role": "user", "content": question}]
    )
    return response.content[0].text

# Sub-agents (Haiku) execute focused tasks on isolated context
def extract_info(document, haiku_prompt):
    response = client.messages.create(
        model="claude-haiku-4-5",  # Sub-agent (cheaper, faster)
        messages=[{"role": "user", "content": [
            {"type": "image", "source": document},
            {"type": "text", "text": haiku_prompt}
        ]}]
    )
    return response.content[0].text
```

- **Pros:** Cost-efficient (5x cheaper), parallel processing, context isolation prevents overflow
- **Cons:** More complex orchestration, requires careful prompt engineering
- **Feasibility:** Medium - needs architectural changes to current dual-subagent pattern
- **Effort Estimate:** L (1 week)

### 2. Context Engineering Best Practices

#### Tool Permission Model (Critical Finding)
```python
# IMPORTANT: allowed_tools only controls permission prompting
# To truly restrict, use disallowed_tools
async with ClaudeSDKClient(
    options=ClaudeAgentOptions(
        allowed_tools=["mcp__github"],  # Auto-approved
        disallowed_tools=["Bash", "Task", "WebSearch", "WebFetch"],  # BLOCKED
    )
) as agent:
    ...
```

**Key insight:** `allowed_tools` alone does NOT restrict tool availability. You MUST use `disallowed_tools` to enforce single integration paths.

#### Context Isolation for Subagents
```python
from concurrent.futures import ThreadPoolExecutor

# Each sub-agent operates on isolated context
with ThreadPoolExecutor() as executor:
    extracted_info_list = list(executor.map(process_document, documents))

# Structured aggregation for orchestrator
extracted_info = ""
for quarter, info in zip(quarters, extracted_info_list):
    extracted_info += f'<info quarter="{quarter}">{info}</info>\n'
```

**Pattern:** Use XML tags to organize subagent results for orchestrator parsing.

#### System Prompt Engineering
```python
RESEARCH_SYSTEM_PROMPT = """You are a research agent specialized in AI.

When providing research findings:
- Always include source URLs as citations
- Format citations as markdown links: [Source Title](URL)
- Group sources in a "Sources:" section at the end

CRITICAL: Do not create issues or PRs - this is a read-only analysis."""
```

**Best Practice:** Encode domain-specific standards, output structure, and operational constraints in system prompts.

### 3. Observability Patterns

#### Current Project State
The project already has solid observability foundation:
- Logfire integration (`backend/app/core/logfire_setup.py`)
- Telemetry spans with trace context (`backend/app/core/telemetry.py`)
- PydanticAI instrumentation

#### Enhanced Activity Tracking Pattern
```python
from utils.agent_visualizer import print_activity, visualize_conversation

# Real-time activity monitoring
async for msg in query(...):
    print_activity(msg)  # Shows: "Using: WebSearch()", "Tool completed"

# Post-execution analysis
visualize_conversation(messages)  # Timeline view
```

**Implementation suggestion for our project:**
```python
# backend/app/agents/activity.py
import logfire
from dataclasses import dataclass
from typing import Any

@dataclass
class AgentActivity:
    action: str
    tool_name: str | None = None
    duration_ms: int | None = None
    metadata: dict[str, Any] | None = None

def log_agent_activity(activity: AgentActivity) -> None:
    """Log agent activity with structured data."""
    logfire.info(
        "agent_activity",
        action=activity.action,
        tool_name=activity.tool_name,
        duration_ms=activity.duration_ms,
        **activity.metadata or {}
    )
```

#### MCP Server Integration for External Observability
```python
# For GitHub CI monitoring
github_mcp: dict[str, Any] = {
    "github": {
        "command": "docker",
        "args": [
            "run", "-i", "--rm",
            "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
            "ghcr.io/github/github-mcp-server",
        ],
        "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ.get("GITHUB_TOKEN")},
    }
}
```

### 4. Cost and Performance Tracking

#### Token Usage Monitoring
```python
# From CrewAI pattern - applicable to our agents
result = crew.kickoff(inputs={"topic": "AI trends"})
print(result.token_usage)  # Token consumption per agent
```

**Implementation for PydanticAI:**
```python
# backend/app/services/cost_tracker.py
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class AgentCost:
    provider: str
    model: str
    input_tokens: int
    output_tokens: int

    @property
    def estimated_cost_usd(self) -> Decimal:
        # Pricing per 1M tokens (January 2025)
        PRICING = {
            "claude-opus-4-5": (15.0, 75.0),  # (input, output)
            "claude-sonnet-4-5-20250929": (3.0, 15.0),
            "claude-haiku-4-5": (0.8, 4.0),
            "gpt-4o": (5.0, 15.0),
            "gpt-4o-mini": (0.15, 0.6),
        }
        input_rate, output_rate = PRICING.get(self.model, (10.0, 30.0))
        return Decimal(
            (self.input_tokens * input_rate + self.output_tokens * output_rate) / 1_000_000
        )

async def track_agent_run(
    run_result,
    agent_name: str,
    task_type: str
) -> None:
    """Track agent run costs in Logfire."""
    import logfire

    # Extract from PydanticAI result
    usage = run_result.usage() if hasattr(run_result, 'usage') else None
    if usage:
        cost = AgentCost(
            provider=agent_name,
            model=usage.model,
            input_tokens=usage.request_tokens,
            output_tokens=usage.response_tokens
        )
        logfire.metric_counter(
            "agent_tokens_total",
            cost.input_tokens + cost.output_tokens,
            tags={
                "agent": agent_name,
                "task_type": task_type,
                "model": cost.model
            }
        )
        logfire.metric_gauge(
            "agent_cost_usd",
            float(cost.estimated_cost_usd),
            tags={"agent": agent_name}
        )
```

---

## Recommendation

Based on this research, we recommend a **phased implementation** approach:

### Phase 1: Immediate Wins (1-2 days)
1. **Add cost tracking** to `ralph_planner.py` dual-subagent pattern
2. **Implement activity logging** for real-time agent monitoring
3. **Add `disallowed_tools`** to enforce tool restrictions in sprint agents

### Phase 2: Context Engineering (1 week)
1. **Adopt XML-tagged context aggregation** for subagent outputs
2. **Implement hierarchical orchestration** for complex SDLC phases
3. **Add buffer size configuration** for multimodal support

### Phase 3: Full Observability (2 weeks)
1. **MCP server integration** for GitHub CI monitoring
2. **Dashboard metrics** for agent performance and costs
3. **Automated alerts** for cost thresholds

### Recommended Architecture Change

```python
# Current dual-subagent pattern
await _run_planning_agent(prompt, provider="openai", model_name="gpt-4o")
await _run_planning_agent(prompt, provider="anthropic", model_name="claude-sonnet")

# Recommended hierarchical pattern
async def run_hierarchical_planning(prompt: str) -> PlanningInterviewResult:
    # 1. Orchestrator generates task-specific prompts
    extraction_prompt = await generate_extraction_prompt(
        prompt,
        model="claude-opus-4-5"  # Smart orchestrator
    )

    # 2. Parallel extraction with cheaper models
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(
            lambda doc: extract_requirements(doc, extraction_prompt),
            documents,
            model="claude-haiku-4-5"  # Fast, cheap
        ))

    # 3. Synthesis with orchestrator
    return await synthesize_results(
        results,
        model="claude-opus-4-5"
    )
```

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Increased complexity from hierarchical pattern | Medium | Start with dual-subagent, migrate incrementally |
| Cost tracking inaccuracy due to streaming | Low | Use post-run usage() method, not estimates |
| Context overflow with large documents | High | Enforce `max_buffer_size`, use chunking |
| MCP server availability | Low | Docker health checks, fallback to direct API |

---

## Next Steps

1. [ ] **Implement `AgentCost` tracker** in `backend/app/services/cost_tracker.py`
2. [ ] **Add `disallowed_tools`** to `SprintAgent` for filesystem isolation
3. [ ] **Create activity logging** middleware for real-time monitoring
4. [ ] **Evaluate Claude Agent SDK** for potential migration from PydanticAI
5. [ ] **Set up Logfire dashboards** for agent cost visualization

---

## Recommended Skills

Based on this research, the following installed skills are relevant:

| Skill | Category | Why Relevant |
|-------|----------|--------------|
| `ai-research-observability-langsmith` | observability | Alternative observability with evaluation framework |
| `ai-research-observability-phoenix` | observability | Open-source alternative to Logfire |
| `openlit-observability` | observability | Zero-code OpenTelemetry instrumentation |
| `ai-research-agents-crewai` | agents | Multi-agent orchestration patterns |
| `anthropic-claude-sdk` | sdk | Direct SDK usage patterns |
| `openai-agents-sdk` | sdk | OpenAI Responses API patterns |

**How to use:**
```bash
cat skills/ai-research-observability-langsmith/SKILL.md
cat skills/openlit-observability/SKILL.md
cat skills/ai-research-agents-crewai/SKILL.md
```

---

## References

1. [Claude Agent SDK - One-Liner Research Agent](https://platform.claude.com/cookbook/claude-agent-sdk-00-the-one-liner-research-agent)
2. [Claude Agent SDK - Observability Agent](https://platform.claude.com/cookbook/claude-agent-sdk-02-the-observability-agent)
3. [Anthropic Cookbooks - Using Sub-Agents](https://github.com/anthropics/claude-cookbooks/blob/main/multimodal/using_sub_agents.ipynb)
4. [Logfire Documentation](https://logfire.pydantic.dev/docs/)
5. [PydanticAI Documentation](https://ai.pydantic.dev/)

---

## Appendix: Code Snippets for Implementation

### A. Enhanced Telemetry Span with Cost Tracking

```python
# backend/app/core/telemetry.py - Enhancement
@contextmanager
def agent_telemetry_span(
    name: str,
    agent_name: str,
    task_type: str,
    **attrs
) -> Iterator[tuple[str | None, str | None, dict[str, Any]]]:
    """Create a Logfire span with agent cost tracking."""
    start = time.monotonic()
    trace_id: str | None = None
    span_id: str | None = None
    metrics: dict[str, Any] = {"agent_name": agent_name, "task_type": task_type}

    try:
        import logfire
        with logfire.span(name, agent_name=agent_name, task_type=task_type, **attrs):
            trace_id, span_id = get_trace_context()
            yield trace_id, span_id, metrics
    except Exception as exc:
        metrics["error"] = str(exc)
        raise
    finally:
        metrics["duration_ms"] = int((time.monotonic() - start) * 1000)
        _write_telemetry_record(name, {**attrs, **metrics}, trace_id, span_id, metrics["duration_ms"], metrics.get("error"))
```

### B. Subagent Context Isolation Pattern

```python
# backend/app/agents/subagent_orchestrator.py
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class SubagentResult:
    agent_key: str
    output: str
    trace_id: str | None
    cost_estimate_usd: float

async def run_isolated_subagents(
    task_generator: Callable[[str], str],
    executor_fn: Callable[[str, str], str],
    documents: list[str],
    orchestrator_model: str = "claude-opus-4-5",
    executor_model: str = "claude-haiku-4-5",
) -> list[SubagentResult]:
    """Run subagents with isolated contexts in parallel."""

    # 1. Orchestrator generates extraction prompt
    extraction_prompt = task_generator(orchestrator_model)

    # 2. Execute in parallel with isolated contexts
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(executor_fn, doc, extraction_prompt, executor_model)
            for doc in documents
        ]
        for i, future in enumerate(futures):
            output = future.result()
            results.append(SubagentResult(
                agent_key=f"executor_{i}",
                output=output,
                trace_id=None,  # Extracted separately
                cost_estimate_usd=estimate_cost(executor_model, output)
            ))

    return results

def aggregate_subagent_results(results: list[SubagentResult]) -> str:
    """Aggregate results with XML tags for orchestrator parsing."""
    aggregated = ""
    for result in results:
        aggregated += f'<result agent="{result.agent_key}">{result.output}</result>\n'
    return aggregated
```

### C. Tool Restriction Pattern

```python
# backend/app/agents/sprint_agent.py - Enhancement
RESTRICTED_TOOLS = [
    "Bash",  # Prevent arbitrary command execution
    "Task",  # Prevent spawning additional subagents
    "WebFetch",  # Limit external HTTP calls
]

class SprintAgent(AssistantAgent):
    def __init__(self, **kwargs):
        # Add tool restrictions for safety
        kwargs.setdefault("disallowed_tools", RESTRICTED_TOOLS)
        super().__init__(**kwargs)
```

---

*Report generated: 2026-01-22*
*Author: Research Scientist Agent*
*Co-Authored-By: Claude Opus 4.5*
