# Research Digest: Multi-Agent Orchestration Best Practices (Last 6 Months)

## Summary

Use the evaluation flywheel as the system-level process, and keep LLM-as-judge
as a grader inside that process. Combine Conductor plan-of-record discipline
with parallel multi-agent orchestration, structured outputs, and tool guardrails.

## Key Sources and Takeaways

### Evaluation Flywheel (Oct 6, 2025)

- Continuous analyze -> measure -> improve loop.
- Build datasets and graders to quantify failure modes.
- Judges fit into the "measure" stage; flywheel is the process.

Source:
https://developers.openai.com/cookbook/examples/evaluation/building_resilient_prompts_using_an_evaluation_flywheel

### AgentKit Walkthrough (Oct 17, 2025)

- Multi-agent workflows, structured outputs, eval optimization.
- Agents SDK export supports production orchestration.

Source:
https://cookbook.openai.com/examples/agentkit/agentkit_walkthrough

### Codex Exec Plans (Oct 7, 2025)

- Living plan-of-record discipline for long tasks.
- Use a canonical plan file to gate implementation.

Source:
https://cookbook.openai.com/articles/codex_exec_plans

### Codex Code Review (Oct 21, 2025)

- Structured reviewer/fixer outputs with confidence scores.
- Useful for per-task evaluation and gate checks.

Source:
https://cookbook.openai.com/examples/codex/build_code_review_with_codex_sdk

### GPT-5.2 Prompting Guide (Dec 11, 2025)

- Enforce ambiguity gates, verbosity control, and compaction.
- Use explicit prompts for clarification before execution.

Source:
https://cookbook.openai.com/examples/gpt-5/gpt-5-2_prompting_guide

### gpt-oss Safeguard Guide (Oct 29, 2025)

- Policy-driven guardrails for tool use and safety checks.
- Use structured policy prompts for audits.

Source:
https://cookbook.openai.com/articles/gpt-oss-safeguard-guide

### gpt-oss Fact Checker (Jan 13, 2026)

- Evidence-based verification for high-risk claims.

Source:
https://cookbook.openai.com/articles/gpt-oss/build-your-own-fact-checker-cerebras

### Deep Research API (Jun 25, 2025)

- Planning-stage research agent with web search + synthesis.
- Use multi-agent enrichment prompts before deep research.

Sources:
https://developers.openai.com/cookbook/examples/deep_research_api/introduction_to_deep_research_api_agents
https://cookbook.openai.com/examples/deep_research_api/introduction_to_deep_research_api

## Implications for This Track

- Keep Conductor artifacts canonical.
- Use paired subagents per role (OpenAI + Anthropic) with judge per pair.
- Use the evaluation flywheel for system-level improvement.
- Use Deep Research API during planning to gather evidence and best practices.
