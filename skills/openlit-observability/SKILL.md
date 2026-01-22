---
name: openlit-observability
description: OpenTelemetry-native LLM observability with OpenLIT. Use when implementing LLM tracing, monitoring costs, debugging AI applications, or adding observability to agent workflows.
---

# OpenLIT LLM Observability

OpenLIT provides zero-code OpenTelemetry-native observability for GenAI and LLM applications.

## Quick Start

```python
# Install
pip install openlit

# Initialize (one line!)
import openlit
openlit.init()  # Auto-instruments all LLM calls
```

## Integration with This Project

This project uses Logfire for observability. OpenLIT complements it for LLM-specific tracing:

```python
# In backend/app/core/logfire_setup.py
import openlit

def setup_llm_observability():
    """Initialize OpenLIT for LLM tracing alongside Logfire."""
    openlit.init(
        otlp_endpoint="http://localhost:4318",  # Or your OTLP collector
        application_name="guilde-lite-tdd-sprint",
        environment="development",
    )
```

## Key Features

### 1. Auto-Instrumentation

Automatically traces:
- OpenAI API calls
- Anthropic API calls
- LangChain operations
- LlamaIndex queries
- Vector database operations

### 2. Cost Tracking

```python
# View costs in OpenLIT dashboard
# Tracks token usage and estimated costs per provider
```

### 3. Prompt/Response Logging

```python
import openlit

# Enable prompt logging (disable in production for privacy)
openlit.init(
    disable_batch=False,
    trace_content=True,  # Log prompts and responses
)
```

### 4. Custom Spans

```python
from opentelemetry import trace

tracer = trace.get_tracer("my-agent")

with tracer.start_as_current_span("agent-planning") as span:
    span.set_attribute("agent.name", "ralph_planner")
    span.set_attribute("task.type", "sprint_planning")
    # Your agent code
```

## Dashboard Setup

```bash
# Run OpenLIT dashboard locally
docker run -d -p 3000:3000 openlit/openlit

# Or use hosted version at openlit.io
```

## Environment Variables

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OPENLIT_APPLICATION_NAME=guilde-lite-tdd-sprint
OPENLIT_ENVIRONMENT=development
```

## Integration with PydanticAI

```python
from pydantic_ai import Agent
import openlit

openlit.init()  # Traces all AI calls

agent = Agent(
    model="anthropic:claude-sonnet-4-20250514",
    system_prompt="You are a helpful assistant"
)

# All agent.run() calls are automatically traced
result = await agent.run("Plan a sprint")
```

## Best Practices

1. **Development**: Enable full tracing with `trace_content=True`
2. **Production**: Disable content tracing for privacy
3. **Cost Alerts**: Set up alerts when costs exceed thresholds
4. **Latency Monitoring**: Track P95 latencies for LLM calls

## References

- [OpenLIT GitHub](https://github.com/openlit/openlit)
- [OpenLIT Documentation](https://openlit.io/docs)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
