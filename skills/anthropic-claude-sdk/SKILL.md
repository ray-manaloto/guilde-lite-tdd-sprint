---
name: anthropic-claude-sdk
description: Build AI agents using the Anthropic Claude Agent SDK and Claude API. Use when building agents, using tool use, implementing streaming, or integrating Claude into applications.
---

# Anthropic Claude SDK & Agent SDK

Build AI agents and applications using Claude's APIs and the Agent SDK.

## Claude API (anthropic-sdk-python)

### Installation

```bash
pip install anthropic
```

### Basic Usage

```python
from anthropic import Anthropic

client = Anthropic()

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude!"}
    ]
)
print(message.content[0].text)
```

### Async Usage

```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic()

async def chat():
    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hello!"}]
    )
    return message.content[0].text
```

### Streaming

```python
with client.messages.stream(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a story"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

### Tool Use

```python
tools = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"}
            },
            "required": ["location"]
        }
    }
]

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    tools=tools,
    messages=[{"role": "user", "content": "What's the weather in Tokyo?"}]
)

# Handle tool use
for block in response.content:
    if block.type == "tool_use":
        tool_name = block.name
        tool_input = block.input
        # Execute tool and continue conversation
```

## Claude Agent SDK

The Claude Agent SDK powers Claude Code and can build custom agents.

### Installation

```bash
pip install claude-agent-sdk
```

### Basic Agent

```python
from claude_agent_sdk import Agent, Tool

# Define tools
@Tool
def read_file(path: str) -> str:
    """Read a file from the filesystem."""
    with open(path) as f:
        return f.read()

@Tool
def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    with open(path, "w") as f:
        f.write(content)
    return f"Wrote {len(content)} bytes to {path}"

# Create agent
agent = Agent(
    model="claude-sonnet-4-20250514",
    tools=[read_file, write_file],
    system_prompt="You are a helpful coding assistant."
)

# Run agent
result = agent.run("Read the README.md and summarize it")
```

### With PydanticAI (This Project's Approach)

```python
from pydantic_ai import Agent
from pydantic import BaseModel

class SprintPlan(BaseModel):
    title: str
    goals: list[str]
    tasks: list[str]

agent = Agent(
    model="anthropic:claude-sonnet-4-20250514",
    result_type=SprintPlan,
    system_prompt="You are a sprint planning assistant."
)

# Structured output
result = await agent.run("Plan a sprint for user authentication")
plan: SprintPlan = result.data
```

## Integration with This Project

### Agent Configuration

Located in `backend/app/agents/`:

```python
# backend/app/agents/assistant.py
from pydantic_ai import Agent
from app.core.config import settings

assistant = Agent(
    model=f"anthropic:{settings.ANTHROPIC_MODEL}",
    system_prompt="...",
)
```

### Multi-Provider Support

```python
# Support both Anthropic and OpenAI
from pydantic_ai import Agent

# Anthropic
agent_claude = Agent(model="anthropic:claude-sonnet-4-20250514")

# OpenAI
agent_gpt = Agent(model="openai:gpt-4o")

# Switch based on config
agent = Agent(model=settings.AI_MODEL)
```

## Best Practices

1. **Use async** for production workloads
2. **Stream responses** for better UX
3. **Structure outputs** with Pydantic models
4. **Handle rate limits** with exponential backoff
5. **Log all interactions** for debugging

## Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

## References

- [Anthropic API Docs](https://docs.anthropic.com/)
- [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python)
- [PydanticAI](https://ai.pydantic.dev/)
- [Building Agents Guide](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
