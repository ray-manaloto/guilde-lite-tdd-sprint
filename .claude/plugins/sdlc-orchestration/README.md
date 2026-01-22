# SDLC Orchestration Plugin

Parallelized software development lifecycle with role-based agents working in parallel phases.

## Overview

This plugin implements a complete software development lifecycle using 17 specialized role-based agents that work in parallel within each phase. Inspired by the [wshobson/agents](https://github.com/wshobson/agents) multi-agent workflow patterns.

## Features

- **17 Role-Based Agents** - From CEO to Junior Engineer
- **5 SDLC Phases** - Requirements, Design, Implementation, Quality, Release
- **Parallel Execution** - Agents within each phase run concurrently
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
│  └── Research Scientist → Feasibility                       │
│                         ↓                                    │
│  Phase 2: DESIGN (Parallel)                                  │
│  ├── Software Architect → System design                     │
│  ├── Data Scientist → Data models                           │
│  └── Network Engineer → Infrastructure                      │
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
│  └── Performance Engineer → Load tests                      │
│                         ↓                                    │
│  Phase 5: RELEASE (Sequential)                               │
│  ├── CI/CD Engineer → Build & deploy                        │
│  ├── Canary User → Beta testing                             │
│  ├── Documentation Engineer → Docs                          │
│  └── DevOps Engineer → Production                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

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
