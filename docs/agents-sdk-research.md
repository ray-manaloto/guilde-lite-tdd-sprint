# Agents SDK Research for Conductor Alignment

This document maps OpenAI cookbook resources to Conductor phases and proposes a
phased adoption plan. Conductor artifacts remain canonical; DB mirrors them.

## Sources

- https://cookbook.openai.com/examples/agentkit/agentkit_walkthrough
- https://cookbook.openai.com/articles/codex_exec_plans
- https://cookbook.openai.com/examples/codex/build_code_review_with_codex_sdk
- https://cookbook.openai.com/examples/partners/eval_driven_system_design/receipt_inspection
- https://cookbook.openai.com/examples/partners/self_evolving_agents/autonomous_agent_retraining
- https://developers.openai.com/cookbook/examples/deep_research_api/introduction_to_deep_research_api_agents
- https://cookbook.openai.com/examples/deep_research_api/introduction_to_deep_research_api
- https://raw.githubusercontent.com/openai/openai-cookbook/main/examples/partners/temporal_agents_with_knowledge_graphs/temporal_agents.ipynb
- https://cookbook.openai.com/examples/gpt-5/gpt-5-2_prompting_guide
- https://cookbook.openai.com/articles/gpt-oss-safeguard-guide
- https://cookbook.openai.com/articles/gpt-oss/build-your-own-fact-checker-cerebras

## Conductor Phase Mapping

### Context

- GPT-5.2 prompting guide: ambiguity handling + output shape controls.
- gpt-oss safeguard: policy-guided guardrails for allowed actions/tools.

### Spec

- Codex exec plans: plan-of-record discipline and living spec requirements.
- Eval-driven system design: problem framing, evals as the backbone of specs.

### Plan

- Codex exec plans: structured planning artifacts and checkpoints.
- Temporal agents: planner patterns for multi-hop task decomposition.
- Deep Research API: planning-stage synthesis and evidence gathering.

### Implement

- AgentKit/Agents SDK: multi-agent orchestration and tool wiring.
- Codex code review: reviewer/fixer stages as structured outputs.

### Verify / Improve

- Eval-driven system design: evals tied to business impact.
- Self-evolving agents: improvement loops with judge feedback.
- Fact checker: evidence-based verification when external checks are needed.

## Phased Adoption Plan

Phase 0: Alignment (Docs Only)

- Introduce Conductor canonical artifacts.
- Add plan gating and approval rules.
- Define tool/MCP allowlist and guardrails.

Phase 1: Execution Baseline

- Implement Conductor commands in-repo.
- Wire runner to read/update `conductor/tracks/<id>/plan.md`.
- Add a reviewer/fixer loop using structured outputs.
- Use Deep Research API in the planning stage for evidence gathering.

Phase 2: Parallel Orchestration

- Introduce a task DAG per track.
- Parallelize independent tasks with concurrency limits.
- Add planner to update DAG with new discoveries.

Phase 3: Evals and Improvement

- Add eval harness tied to acceptance criteria.
- Track drift and failure patterns.
- Introduce judge loops and optional auto-iteration.

Phase 4: Safety and Policy

- Enforce policy guardrails via safety model or policy prompts.
- Evidence-backed verification for external facts.
- Require explicit approval for high-risk tool usage.

## How This Fits Conductor Canonical Artifacts

- `conductor/product.md`: goals, non-goals, success metrics.
- `conductor/tech-stack.md`: tool policies and allowed SDKs.
- `conductor/workflow.md`: plan gating, parallelization rules, approvals.
- `conductor/tracks/<id>/spec.md`: acceptance criteria and eval hooks.
- `conductor/tracks/<id>/plan.md`: task DAG, dependencies, checkpoints.

## Recommendation

Use Agents SDK for execution only, not as the source of truth. The Conductor
plan/spec remain canonical; SDK agents operate strictly against those artifacts.

Model routing:

- OpenAI models run via native Agents SDK models.
- Anthropic models run via LiteLLM adapter where required.
