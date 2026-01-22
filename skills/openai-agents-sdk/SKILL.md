---
name: openai-agents-sdk
description: Use when building or integrating OpenAI Agents SDK (Python) workflows, agents, tools, Runner orchestration, tracing, or structured outputs.
version: 0.1.0
---

# OpenAI Agents SDK (Python)

## When to use

- Implementing or refactoring agent orchestration with the Agents SDK.
- Creating role-based agents and runners for parallel workflows.
- Using structured outputs, tracing, or usage metrics.

## Setup

- Ensure `openai-agents` and `openai` are installed.
- Use `OPENAI_API_KEY` and the configured `OPENAI_MODEL` env vars.

## Minimal pattern

```python
from agents import Agent, Runner, ModelSettings

agent = Agent(
    name="Planner",
    instructions="Plan the task and output JSON.",
    model="openai-responses:gpt-5.2-codex",
    model_settings=ModelSettings(include_usage=True),
)

result = await Runner.run(agent, "Create a phased plan.")
print(result.final_output)
```

## Orchestration guidance

- Create one agent per role and run them in parallel using asyncio.
- For paired OpenAI + Anthropic runs, execute two agents and pass both outputs
  to a judge agent.
- Persist outputs to Conductor artifacts; do not write directly to DB without
  also updating Conductor files.

## Structured outputs

- Prefer JSON schema outputs for plan/spec responses.
- Store the schema with the artifact for reproducibility.

## Tracing and telemetry

- Capture `result.context_wrapper.usage` when `include_usage=True`.
- Persist trace IDs and URLs alongside artifacts.
