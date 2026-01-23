# Phase 1: Requirements Summary - SDLC Enhancement Research

## Overview

This document consolidates findings from 4 parallel research agents analyzing Anthropic cookbooks and best practices for enhancing our parallel workflow orchestration framework.

---

## Research Agent Outputs

### 1. Orchestrator-Workers Pattern (Research Scientist)

**Key Findings:**

1. **Structured 4-Component Prompts**
   - Every agent prompt needs: Objective, Output Format, Tool Guidance, Boundaries
   - Current prompts missing explicit tool guidance and boundaries

2. **File-Based Artifact Handoffs**
   - Reduces token overhead by 60-80%
   - Pattern: Worker writes to `artifacts/{phase}/{agent}.md`
   - Orchestrator reads consolidated artifacts, not raw outputs

3. **Synthesis Agent Required**
   - After each parallel phase, run synthesis agent to:
     - Identify conflicts between agent outputs
     - Create unified artifact for next phase
     - Flag gaps requiring additional research

4. **Context Window Management**
   - Each subagent gets ~25% of parent's remaining context
   - Use `run_in_background` for long-running research tasks
   - Aggregate results lazily (read files, not inline outputs)

### 2. Evaluator-Optimizer Pattern (Software Architect)

**Key Findings:**

1. **Structured Evaluation Functions**
   - Replace implicit QA with explicit evaluator agents
   - Each evaluator returns: `{pass: bool, score: float, feedback: str}`
   - Evaluator output feeds optimizer for retry logic

2. **Feedback Memory for Retry Loops**
   - Store failed attempt context in `feedback_history[]`
   - Optimizer receives: original task + all previous attempts + feedback
   - Max 3 retries with exponentially increasing context

3. **QA Agent Conversion**
   - Current: QA agent runs tests, reports results
   - Improved: QA evaluator scores each criterion separately
   - Categories: functionality, security, performance, maintainability

4. **Backpressure from Evaluation**
   - Failed evaluation blocks phase transition
   - Optimizer suggests specific fixes, not generic "try again"
   - Human escalation after 3 failed optimization attempts

### 3. Extended Thinking and Evals (Data Scientist)

**Key Findings:**

1. **Token Budget by Role**
   | Role | Thinking Budget | Use Case |
   |------|-----------------|----------|
   | Software Architect | 16,000-32,000 | Complex system design |
   | Code Reviewer | 16,000-32,000 | Security analysis, edge cases |
   | Staff Engineer | 4,000-8,000 | Implementation decisions |
   | Data Scientist | 4,000-8,000 | Algorithm selection |
   | Junior Engineer | 1,000-2,000 | Simple tasks, no deep reasoning |

2. **Deterministic Graders First**
   - Build exact-match graders for code correctness
   - String/regex matching for output format compliance
   - Only use LLM graders for subjective quality

3. **pass@k and pass^k Metrics**
   - pass@k: Probability of success in k attempts
   - pass^k: Probability of k consecutive successes
   - Target: pass@3 > 95% for all automated agents

4. **Eval-Driven Development**
   - Write evals before implementing agent changes
   - Regression test agent behavior with golden datasets
   - Track eval metrics in observability (Langfuse/Logfire)

### 4. Claude Agent SDK Subagent Patterns (DevOps Engineer)

**Key Findings:**

1. **Tool Restriction Strategy**
   ```python
   # Prefer disallowed_tools over allowed_tools
   subagent = Agent(
       disallowed_tools=["Write", "Edit", "Bash"],  # Research-only agent
       # vs allowed_tools which may miss new tools
   )
   ```

2. **XML-Tagged Aggregation**
   ```xml
   <agent-output agent="research-scientist" phase="requirements">
     <findings>...</findings>
     <recommendations>...</recommendations>
     <confidence>0.85</confidence>
   </agent-output>
   ```
   - Structured output enables programmatic parsing
   - Confidence scores help orchestrator prioritize

3. **Hierarchical Model Selection**
   | Role | Model | Reasoning |
   |------|-------|-----------|
   | Orchestrator | Opus | Complex multi-agent coordination |
   | Staff/Senior Engineer | Sonnet | Implementation, good code quality |
   | Junior Engineer | Haiku | Simple tasks, fast, cheap |
   | Evaluator | Sonnet | Needs reasoning but not creative |

4. **Context Isolation Pattern**
   - Subagents should NOT see full parent conversation
   - Pass only: task description + relevant artifacts
   - Prevents context pollution and reduces token usage

---

## Consolidated Recommendations

### Immediate Actions (High Priority)

1. **Update All 22 Agent Prompts**
   - Add 4-component structure: Objective, Output, Tools, Boundaries
   - Add explicit tool restrictions per role
   - Estimated effort: 2-3 hours

2. **Add Synthesis Agent**
   - Create `sdlc-orchestration:synthesis` agent
   - Runs after each parallel phase
   - Outputs consolidated artifact for next phase
   - Estimated effort: 1 hour

3. **Implement Evaluator-Optimizer in PhaseRunner**
   - Add `evaluate_phase_output()` method
   - Add `optimize_and_retry()` method with feedback memory
   - Add 3-retry limit with human escalation
   - Estimated effort: 2-3 hours

### Medium-Term Actions

4. **Configure Extended Thinking**
   - Add `thinking_budget` config per agent role
   - Update Task tool calls to include budget parameter
   - Estimated effort: 1 hour

5. **Build Deterministic Evaluators**
   - Code compilation check (Python: `ruff check`, TypeScript: `tsc --noEmit`)
   - Test execution check (pytest, vitest)
   - Coverage threshold check (>80%)
   - Estimated effort: 2 hours

6. **Add Eval Metrics to Logfire**
   - Track pass@k per agent per phase
   - Track retry counts and failure reasons
   - Dashboard for eval trends
   - Estimated effort: 2-3 hours

### Long-Term Actions

7. **Golden Dataset for Regression Testing**
   - Capture successful agent runs as test cases
   - Replay against new agent versions
   - Estimated effort: Ongoing

8. **Hierarchical Model Selection**
   - Configure model per role in agent definitions
   - Cost optimization without quality loss
   - Estimated effort: 1 hour setup, ongoing tuning

---

## Gap Analysis: Current vs Recommended

| Aspect | Current State | Recommended State | Gap |
|--------|--------------|-------------------|-----|
| Agent Prompts | Basic role descriptions | 4-component structured prompts | High |
| Tool Restrictions | None | disallowed_tools per role | High |
| Phase Handoffs | Inline Task outputs | File-based artifacts | Medium |
| QA Automation | Single QA agent | Evaluator + Optimizer loop | High |
| Retry Logic | None | 3 retries with feedback memory | High |
| Extended Thinking | Not configured | Role-based token budgets | Medium |
| Observability | Basic Logfire | Eval metrics + dashboards | Medium |
| Model Selection | All Sonnet | Hierarchical Opus/Sonnet/Haiku | Low |

---

## Phase 2 Design Requirements

Based on this research, Phase 2 should design:

1. **Evaluator-Optimizer Architecture**
   - Interface for evaluator functions
   - Feedback memory data structure
   - Integration points in PhaseRunner

2. **Structured Prompt Templates**
   - YAML/JSON schema for 4-component prompts
   - Validation for required sections
   - Per-role tool restriction configs

3. **Artifact Management System**
   - Directory structure for phase artifacts
   - Naming conventions for agent outputs
   - Synthesis agent input/output format

4. **Eval Metrics Schema**
   - Logfire span attributes for evals
   - Dashboard queries and visualizations
   - Alert thresholds for pass@k degradation

---

## Appendix: Research Sources

- Anthropic Cookbook: Orchestrator-Workers Pattern
- Anthropic Cookbook: Prompt Optimization with Evals
- Anthropic Cookbook: Extended Thinking Deep Dive
- Claude Agent SDK Documentation
- Building Effective Agents (Anthropic Engineering Blog)
