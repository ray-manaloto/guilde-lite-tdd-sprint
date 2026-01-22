---
name: litellm
description: Use when routing non-OpenAI models (e.g., Anthropic) through LiteLLM or integrating LiteLLM with OpenAI Agents SDK in Python.
version: 0.1.0
---

# LiteLLM (Python)

## When to use

- Running Anthropic models inside the Agents SDK workflow.
- Standardizing model access via `anthropic/` prefixes.

## Setup

- Install `openai-agents[litellm]` (includes LiteLLM integration).
- Set `ANTHROPIC_API_KEY` in the environment.
- If serializer warnings appear, set:
  `OPENAI_AGENTS_ENABLE_LITELLM_SERIALIZER_PATCH=true`.

## Agents SDK integration

```python
from agents import Agent, Runner, ModelSettings
from agents.extensions.models.litellm_model import LitellmModel

agent = Agent(
    name="AnthropicPlanner",
    instructions="Produce a plan.",
    model=LitellmModel(
        model="anthropic/claude-opus-4-5-20251101",
        api_key=os.environ["ANTHROPIC_API_KEY"],
    ),
    model_settings=ModelSettings(include_usage=True),
)

result = await Runner.run(agent, "Create a phased plan.")
print(result.final_output)
```

## Notes

- Use `anthropic/<model>` prefixes for LiteLLM routing.
- For structured outputs, ensure the target model supports them.
- Treat LiteLLM usage as provider-specific; use native OpenAI models directly.
