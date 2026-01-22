# SDLC Orchestration Plugin

Parallelized software development lifecycle with role-based agents working in parallel phases.

## Overview

This plugin implements a complete software development lifecycle using 22 specialized role-based agents that work in parallel within each phase. Inspired by the [wshobson/agents](https://github.com/wshobson/agents) multi-agent workflow patterns and enhanced with the [Anthropic Evaluator-Optimizer pattern](https://github.com/anthropics/anthropic-cookbook).

## Features

- **22 Role-Based Agents** - From CEO to Junior Engineer, including UI/UX specialists
- **5 SDLC Phases** - Requirements, Design, Implementation, Quality, Release
- **Parallel Execution** - Agents within each phase run concurrently
- **Evaluator-Optimizer Pattern** - Structured evaluation with feedback-driven retry loops
- **Model Optimization** - Opus for critical decisions, Sonnet for complex tasks, Haiku for fast operations
- **Workflow Enforcement** - Hooks ensure proper SDLC discipline

## Roles

### Executive Layer
| Role | Model | Responsibilities |
|------|-------|-----------------|
| CEO/Stakeholder | opus | Business goals, ROI, priorities |
| Project Manager | sonnet | Planning, coordination, risk management |

### Analysis Layer
| Role | Model | Responsibilities |
|------|-------|-----------------|
| Business Analyst | sonnet | User stories, requirements, acceptance criteria |
| Research Scientist | opus | Technical feasibility, innovation research |
| Data Scientist | opus | Data requirements, ML models, analytics |

### Architecture Layer
| Role | Model | Responsibilities |
|------|-------|-----------------|
| Software Architect | opus | System design, APIs, technology selection |
| Network Engineer | sonnet | Infrastructure topology, security |

### Engineering Layer
| Role | Model | Responsibilities |
|------|-------|-----------------|
| Staff Engineer | opus | Critical paths, core architecture |
| Senior Engineer | sonnet | Feature modules, integrations |
| Junior Engineer | haiku | UI components, utilities |

### Quality Layer
| Role | Model | Responsibilities |
|------|-------|-----------------|
| QA Automation | sonnet | Test strategy, automation, coverage |
| Code Reviewer | opus | PR reviews, standards enforcement |
| Performance Engineer | opus | Load testing, optimization |

### Operations Layer
| Role | Model | Responsibilities |
|------|-------|-----------------|
| DevOps Engineer | sonnet | Infrastructure, deployments, monitoring |
| CI/CD Engineer | sonnet | Pipelines, release automation |
| Canary User | haiku | Beta testing, user feedback |
| Documentation Engineer | sonnet | User guides, API docs |

### UI/UX Layer
| Role | Model | Responsibilities |
|------|-------|-----------------|
| UI Designer | sonnet | Visual design, component styling, design systems |
| UX Researcher | sonnet | User research, usability testing, journey mapping |
| Accessibility Specialist | sonnet | WCAG compliance, a11y testing, inclusive design |
| Frontend Architect | opus | Frontend architecture, performance, state management |
| Design System Engineer | sonnet | Component libraries, design tokens, documentation |

## Commands

### Full Feature Workflow
```
/sdlc-orchestration:full-feature "feature description"
```
Executes all 5 phases with parallel agent coordination.

### Phase-Specific Execution
```
/sdlc-orchestration:phase requirements "feature description"
/sdlc-orchestration:phase design "feature description"
/sdlc-orchestration:phase implement "feature description"
/sdlc-orchestration:phase quality "feature description"
/sdlc-orchestration:phase release "feature description"
```

### Role-Specific Invocation
```
/sdlc-orchestration:role architect "design API for authentication"
/sdlc-orchestration:role senior "implement OAuth2 flow"
/sdlc-orchestration:role qa "create test suite for auth module"
```

## Workflow Phases

```
┌──────────────────────────────────────────────────────────────┐
│                        SDLC WORKFLOW                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Phase 1: REQUIREMENTS (Parallel)                            │
│  ├── CEO/Stakeholder  → Business goals                      │
│  ├── Business Analyst → User stories                        │
│  ├── Research Scientist → Feasibility                       │
│  └── UX Researcher → User research (if UI feature)          │
│                         ↓                                    │
│  Phase 2: DESIGN (Parallel)                                  │
│  ├── Software Architect → System design                     │
│  ├── Data Scientist → Data models                           │
│  ├── Network Engineer → Infrastructure                      │
│  ├── UI Designer → Visual design (if UI feature)            │
│  ├── Frontend Architect → Frontend architecture             │
│  └── Design System Engineer → Component specs               │
│                         ↓                                    │
│  Phase 3: IMPLEMENT (Parallel by Layer)                      │
│  ├── Staff Engineer → Core architecture                     │
│  ├── Senior Engineer → Feature modules                      │
│  ├── Junior Engineer → UI components                        │
│  └── DevOps Engineer → CI/CD                                │
│                         ↓                                    │
│  Phase 4: QUALITY (Parallel)                                 │
│  ├── QA Automation → Test suites                            │
│  ├── Code Reviewer → PR reviews                             │
│  ├── Performance Engineer → Load tests                      │
│  └── Accessibility Specialist → A11y testing                │
│                         ↓                                    │
│  Phase 5: RELEASE (Sequential)                               │
│  ├── CI/CD Engineer → Build & deploy                        │
│  ├── Canary User → Beta testing                             │
│  ├── Documentation Engineer → Docs                          │
│  └── DevOps Engineer → Production                           │
│                                                              │
│  [Evaluator-Optimizer Loop]                                  │
│  After each phase, evaluators validate output:               │
│  ├── Deterministic: Ruff lint, pytest, type check           │
│  └── LLM-based: Quality assessment, completeness            │
│  Failed evaluations trigger retry with feedback memory       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Evaluator-Optimizer Pattern

The SDLC orchestration integrates an **Evaluator-Optimizer pattern** for structured validation with feedback-driven retry loops. This ensures quality gates are enforced automatically.

### How It Works

1. **Phase Execution**: Agent completes phase work
2. **Evaluation**: Multiple evaluators assess the output
   - **Deterministic**: Ruff lint, pytest, type checking (fast, reliable)
   - **LLM-based**: Quality assessment, completeness checks (deeper analysis)
3. **Pass/Retry Decision**: If evaluations pass, proceed; if not, retry with feedback
4. **Feedback Memory**: Failed attempts accumulate context for the optimizer
   - Attempt 1: Original task only
   - Attempt 2: Task + previous feedback
   - Attempt 3: Task + full history + detailed analysis
5. **Escalation**: After 3 failed attempts, escalate to human review

### Evaluators by Phase

| Phase | Evaluators |
|-------|------------|
| Verification | Ruff lint, pytest, type check |
| Coding | Ruff lint, pytest, type check |
| All phases | Ruff lint (global) |

### FeedbackMemory

Tracks retry history with exponentially increasing context:

```python
FeedbackMemory(
    sprint_id=uuid,
    phase="verification",
    original_goal="Build hello world script",
    max_attempts=3,
    attempts=[AttemptRecord(...), ...],
    accumulated_insights={"recurring_issues": [...]}
)
```

See [Evaluator-Optimizer Documentation](docs/evaluator-optimizer.md) for details.

## Integration with Sprint System

When used with the guilde-lite-tdd-sprint system:

1. Sprint planning triggers Requirements phase
2. Sprint execution triggers Design → Implementation → Quality
3. Sprint completion triggers Release phase
4. All agent runs are linked to sprint ID
5. Telemetry is stored in sprint artifacts

## Hooks

### enforce-sdlc
Triggers when implementing features, prompts for proper SDLC workflow.

### parallel-agents
Coordinates parallel execution of agents within phases.

### confirmation-enforcement
Blocks research tools (WebSearch, WebFetch) until user confirms workflow choice. See [SDLC Enforcement Documentation](docs/sdlc-enforcement.md) for details.

### documentation-sync
Monitors code, requirements, and documentation changes to ensure they stay in sync. Triggers documentation subagent when drift is detected.

## Documentation

- **[SDLC Enforcement System](docs/sdlc-enforcement.md)** - Comprehensive guide to confirmation-based workflow enforcement, state files, blocking mechanisms, and backpressure validation

## Example Usage

```
User: /sdlc-orchestration:full-feature "User authentication with OAuth2"

[Phase 1: Requirements - 3 agents in parallel]
CEO: Business goal is to reduce signup friction by 30%
BA: Created 5 user stories with acceptance criteria
Research: OAuth2 is well-supported, recommend Auth0 integration

[Phase 2: Design - 3 agents in parallel]
Architect: Created ADR-001 for OAuth2 architecture
Data: Designed users and oauth_tokens schema
Network: VPC design with WAF for API protection

[Phase 3: Implementation - 4 agents in parallel]
Staff: Implemented core auth service
Senior: Built OAuth2 flow and social login
Junior: Created login/signup UI components
DevOps: Set up CI/CD with secrets management

[Phase 4: Quality - 3 agents in parallel]
QA: 95% test coverage, all tests passing
Reviewer: All PRs approved, no security issues
Perf: Handles 1000 RPS, p99 < 200ms

[Phase 5: Release - Sequential]
CI/CD: Built and deployed to staging
Canary: Beta feedback positive
Docs: Updated API documentation
DevOps: Deployed to production

✅ Feature complete and deployed
```

## Installation

This plugin is included in the guilde-lite-tdd-sprint project at `.claude/plugins/sdlc-orchestration/`.

To use:
1. The plugin is auto-loaded when Claude Code starts in this project
2. Use the slash commands as documented above
3. The hooks will enforce SDLC discipline automatically

## See Also

- [wshobson/agents](https://github.com/wshobson/agents) - Inspiration for multi-agent workflows
- [Sprint System Documentation](../../../docs/sprints.md) - Integration with sprint workflow
