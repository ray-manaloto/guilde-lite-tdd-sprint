# Conductor Workflow Initiation Prompt

Use a Conductor-led, context-driven workflow with parallel orchestration.
Run research in parallel before planning.

Inputs:

- Conductor context: conductor/product.md, conductor/tech-stack.md,
  conductor/workflow.md, conductor/tooling.md, conductor/evals.md
- Alignment docs: docs/conductor-alignment.md, docs/agents-sdk-research.md
- Starting prompt: docs/starting-prompt.md

Objectives:

1. Use Agents SDK as the orchestration layer.
2. Keep Conductor artifacts canonical; DB mirrors them.
3. CLI-first sprint interview to generate spec + plan.
4. Resolve vagueness via repeated interview questions.
5. Manual confirmation only when confidence is low.
6. OpenAI models run natively; Anthropic via LiteLLM only.
7. Make integration tests pass.
8. Use role-based parallel orchestration with paired subagents.
9. Use the Deep Research API during planning.
10. Follow the phase role matrix (requirements/design/implement/quality/release).

Traceability Requirements:

- For each role, run a paired subagent: one OpenAI, one Anthropic.
- Run a judge/eval for each paired subagent output.
- Use LLM-as-judge for evaluations unless an alternate eval workflow is specified.
- Capture Deep Research API outputs as planning artifacts.
- Store each agent response as Markdown and per-agent state JSON.
- Mirror all artifact writes and Logfire/telemetry events into the DB.
- During Deep Research, discover relevant Codex skills. Create missing skills
  before coding.
- Store each agent response as a Markdown/spec artifact.
- Store per-agent state:
  - context/token usage
  - number of context compactions
  - skills used
  - plugins used
  - slash commands used
  - model used
  - tools used
- Persist Logfire trace IDs/URLs for each agent run.

Deliverables:

- A refined spec and plan for this track.
- A CLI interview flow that writes Conductor artifacts.
- An Agents SDK runner that updates plan status.
- Integration tests passing.
