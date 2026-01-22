---
name: sdlc-orchestrator
description: |
  Orchestrates parallelized software development lifecycle with role-based agents.
  Use when starting any feature development, sprint execution, or complex implementation.
  Coordinates CEO/stakeholders, PM, architects, engineers, QA, DevOps, and documentation roles
  working in parallel phases for maximum efficiency.
---

# SDLC Orchestrator - Parallel Role-Based Development

This skill orchestrates a complete software development lifecycle using parallelized
role-based agents. Each role contributes specialized expertise at the appropriate
phase of development.

## Orchestration Philosophy

### Parallel Execution Model

The SDLC follows a phased approach where independent tasks run in parallel:

```
Phase 1: Requirements (Parallel)
├── CEO/Stakeholder → Business goals, success criteria
├── Business Analyst → User stories, acceptance criteria
└── Research Scientist → Technical feasibility, innovation opportunities

Phase 2: Design (Parallel)
├── Software Architect → System design, API contracts
├── Data Scientist → Data models, ML requirements
└── Network Engineer → Infrastructure topology

Phase 3: Implementation (Parallel by Layer)
├── Staff Engineer → Core architecture, critical paths
├── Senior Engineers → Feature modules, integrations
├── Junior Engineers → UI components, utilities
└── DevOps → CI/CD pipeline, environments

Phase 4: Quality (Parallel)
├── QA Automation → Test suites, coverage
├── Code Reviewers → PR reviews, standards
├── Performance Engineer → Load testing, optimization
└── Security Auditor → Vulnerability scanning

Phase 5: Release (Sequential with Parallel Monitoring)
├── CI/CD Engineer → Build, deploy to staging
├── Canary Users → Beta testing, feedback
├── Documentation Engineer → User guides, API docs
└── DevOps → Production deployment
```

## Role Definitions

### Executive Layer

| Role | Responsibilities | Parallel Phase |
|------|-----------------|----------------|
| CEO/Stakeholder | Business goals, ROI, strategic alignment | Requirements |
| Project Manager | Timeline, resources, risk management | All phases (coordination) |

### Analysis Layer

| Role | Responsibilities | Parallel Phase |
|------|-----------------|----------------|
| Business Analyst | User stories, requirements, acceptance criteria | Requirements |
| Research Scientist | Technical research, feasibility, innovation | Requirements |
| Data Scientist | Data requirements, ML models, analytics | Design |

### Architecture Layer

| Role | Responsibilities | Parallel Phase |
|------|-----------------|----------------|
| Software Architect | System design, patterns, API contracts | Design |
| Network Engineer | Infrastructure, networking, security topology | Design |

### Engineering Layer

| Role | Responsibilities | Parallel Phase |
|------|-----------------|----------------|
| Staff Engineer | Critical paths, core architecture, mentoring | Implementation |
| Senior Engineer | Feature modules, complex integrations | Implementation |
| Junior Engineer | UI components, utilities, documentation | Implementation |

### Quality Layer

| Role | Responsibilities | Parallel Phase |
|------|-----------------|----------------|
| QA Automation | Test strategy, automation, coverage | Quality |
| Code Reviewer | PR reviews, standards enforcement | Quality |
| Performance Engineer | Load testing, profiling, optimization | Quality |

### Operations Layer

| Role | Responsibilities | Parallel Phase |
|------|-----------------|----------------|
| DevOps | Infrastructure, deployments, monitoring | Implementation/Release |
| CI/CD Engineer | Pipelines, automation, release management | Implementation/Release |
| Canary Users | Beta testing, user feedback, validation | Release |
| Documentation Engineer | User guides, API docs, architecture docs | Release |

## Workflow Invocation

### Full SDLC Workflow

```
/sdlc-orchestration:full-feature "feature description"
```

This triggers all phases with parallel agent execution.

### Phase-Specific Workflows

```
/sdlc-orchestration:requirements "feature description"
/sdlc-orchestration:design "feature description"
/sdlc-orchestration:implement "feature description"
/sdlc-orchestration:quality "feature description"
/sdlc-orchestration:release "feature description"
```

### Role-Specific Invocation

```
/sdlc-orchestration:role architect "design API for user authentication"
/sdlc-orchestration:role senior-engineer "implement OAuth2 flow"
/sdlc-orchestration:role qa "create test suite for auth module"
```

## Parallel Execution Rules

### 1. Independence Principle
Tasks within a phase that don't share state can run in parallel.

### 2. Dependency Gates
Phases complete before dependent phases start.

### 3. Feedback Loops
Quality phase can trigger implementation fixes (iterative).

### 4. Communication Protocol
Agents communicate via structured artifacts:
- Requirements → `requirements.md`
- Design → `design.md`, `api-spec.yaml`
- Implementation → Code files
- Quality → Test results, review comments
- Release → Deployment manifests, docs

---

## CRITICAL: How to Execute Parallel Subagents

**To run agents in parallel, you MUST invoke multiple Task tools in a SINGLE message.**

### Subagent Types (use exact names with plugin prefix)

| Agent | subagent_type |
|-------|---------------|
| CEO/Stakeholder | `sdlc-orchestration:ceo-stakeholder` |
| Project Manager | `sdlc-orchestration:project-manager` |
| Software Architect | `sdlc-orchestration:software-architect` |
| Business Analyst | `sdlc-orchestration:business-analyst` |
| Research Scientist | `sdlc-orchestration:research-scientist` |
| Staff Engineer | `sdlc-orchestration:staff-engineer` |
| Senior Engineer | `sdlc-orchestration:senior-engineer` |
| Junior Engineer | `sdlc-orchestration:junior-engineer` |
| QA Automation | `sdlc-orchestration:qa-automation` |
| Code Reviewer | `sdlc-orchestration:code-reviewer` |
| DevOps Engineer | `sdlc-orchestration:devops-engineer` |
| Network Engineer | `sdlc-orchestration:network-engineer` |
| CI/CD Engineer | `sdlc-orchestration:cicd-engineer` |
| Canary User | `sdlc-orchestration:canary-user` |
| Documentation Engineer | `sdlc-orchestration:documentation-engineer` |
| Performance Engineer | `sdlc-orchestration:performance-engineer` |
| Data Scientist | `sdlc-orchestration:data-scientist` |

### Parallel Execution Example

To run Requirements phase with 3 parallel agents, send ONE message with 3 Task tool calls:

```markdown
# In a single assistant response, invoke:

Task 1: subagent_type="sdlc-orchestration:ceo-stakeholder"
        prompt="Define business goals for: {feature}"

Task 2: subagent_type="sdlc-orchestration:business-analyst"
        prompt="Create user stories for: {feature}"

Task 3: subagent_type="sdlc-orchestration:research-scientist"
        prompt="Evaluate feasibility for: {feature}"
```

**Key Rules:**
1. ALL parallel Task calls must be in ONE message (not sequential messages)
2. Use the full `sdlc-orchestration:agent-name` format
3. Wait for ALL agents to complete before next phase
4. Release phase is SEQUENTIAL (not parallel) for deployment safety

---

## State Management

Track phase progress using the state template at `templates/phase-state.json`.

### State File Location

```
.claude/sdlc-state.json
```

### State Structure

```json
{
  "track_id": "feature-name",
  "current_phase": "implementation",
  "phases": {
    "requirements": { "status": "completed", "agents_completed": [...] },
    "design": { "status": "completed", "agents_completed": [...] },
    "implementation": { "status": "in_progress", "agents_completed": [...] }
  }
}
```

### Backpressure Validation

Hooks automatically enforce gates:
- **Lint check** after Python writes (`ruff`)
- **Type check** after TypeScript writes (`tsc`)
- **Phase gates** prevent skipping phases
- **Deploy gates** block deployments outside release phase

---

## Result Aggregation

**After all parallel agents complete, aggregate results before proceeding.**

### Aggregation Steps

1. **Collect** all agent outputs
2. **Identify** conflicts or gaps between agents
3. **Synthesize** into consolidated artifact
4. **Verify** gate requirements met
5. **Handoff** to next phase with summary

### Example Aggregation

```markdown
# Requirements Summary

## Business Goals (from CEO/Stakeholder)
- Primary goal: [from agent output]
- Success metric: [from agent output]

## User Stories (from Business Analyst)
1. As a user, I want... [from agent output]

## Technical Feasibility (from Research Scientist)
- Recommended approach: [from agent output]
- Risks: [from agent output]

## Handoff to Design
- Approved scope: [list]
- Constraints: [list]
```

---

## Integration with Sprint Workflow

When used with the sprint system:

1. Sprint planning triggers Requirements phase
2. Sprint execution triggers Design → Implementation → Quality
3. Sprint completion triggers Release phase

Each phase updates sprint status and creates checkpoints.

## Example: Hello World Feature

```
User: /sdlc-orchestration:full-feature "Create a Python script that prints 'hello world'"

Phase 1: Requirements (2 agents parallel)
├── BA: "Simple script, single output, no dependencies"
└── Research: "Standard Python, no special requirements"

Phase 2: Design (1 agent)
└── Architect: "Single file hello.py, print() function"

Phase 3: Implementation (1 agent)
└── Junior Engineer: Creates hello.py

Phase 4: Quality (2 agents parallel)
├── QA: Verifies output matches "hello world"
└── Reviewer: Confirms code follows standards

Phase 5: Release
└── Docs Engineer: Updates README if needed

Result: hello.py created and verified
```
