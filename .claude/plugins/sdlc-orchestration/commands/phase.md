---
name: phase
description: |
  Execute a specific SDLC phase with parallel agent coordination.
  Available phases: requirements, design, implement, quality, release.
---

# Phase-Specific Workflow Execution

Execute a specific phase of the SDLC with all relevant agents working in parallel.

## Usage

```
/sdlc-orchestration:phase <phase> "<context/description>"
```

---

## CRITICAL: Parallel Subagent Execution

**To run agents in parallel, you MUST invoke multiple Task tools in a SINGLE message.**

### Example: Requirements Phase (3 agents parallel)

```
# In a SINGLE assistant message, call ALL THREE Task tools:

<Task tool call 1>
  subagent_type: "ceo-stakeholder"
  prompt: "Define business goals for: [feature]"
</Task tool call 1>

<Task tool call 2>
  subagent_type: "business-analyst"
  prompt: "Create user stories for: [feature]"
</Task tool call 2>

<Task tool call 3>
  subagent_type: "research-scientist"
  prompt: "Evaluate technical feasibility for: [feature]"
</Task tool call 3>
```

**Key Rules:**
1. All parallel Task calls must be in ONE message
2. Use the exact `subagent_type` from the agents/ folder (kebab-case)
3. Each agent gets focused prompt for their role
4. Wait for ALL to complete before proceeding to next phase

---

## Available Phases

### requirements

Gather and document all requirements with parallel agents.

**Agents (run in parallel):**

| Agent | subagent_type | Focus |
|-------|---------------|-------|
| CEO/Stakeholder | `ceo-stakeholder` | Business goals, ROI, priority |
| Business Analyst | `business-analyst` | User stories, acceptance criteria |
| Research Scientist | `research-scientist` | Technical feasibility |
| UX Researcher | `ux-researcher` | User research, personas (if UI feature) |

**Parallel Execution Pattern:**
```python
# Invoke these 3-4 Task tools in ONE message:
Task(subagent_type="sdlc-orchestration:ceo-stakeholder", prompt="Define business goals for: {feature}")
Task(subagent_type="sdlc-orchestration:business-analyst", prompt="Create user stories for: {feature}")
Task(subagent_type="sdlc-orchestration:research-scientist", prompt="Evaluate feasibility for: {feature}")
# Optional for UI features:
Task(subagent_type="sdlc-orchestration:ux-researcher", prompt="Research user needs for: {feature}")
```

**Output:**
- Business objectives document
- User stories with acceptance criteria
- Technical feasibility report

```
/sdlc-orchestration:phase requirements "Build a real-time chat feature"
```

### design

Create technical design with parallel architecture agents.

**Agents (run in parallel):**

| Agent | subagent_type | Focus |
|-------|---------------|-------|
| Software Architect | `software-architect` | System design, API contracts |
| Data Scientist | `data-scientist` | Data models, ML requirements |
| Network Engineer | `network-engineer` | Infrastructure, security |
| UI Designer | `ui-designer` | Visual design, component styling (if UI feature) |
| Frontend Architect | `frontend-architect` | Frontend architecture, state management |
| Design System Engineer | `design-system-engineer` | Component specs, design tokens |

**Parallel Execution Pattern:**
```python
# Invoke these 3-6 Task tools in ONE message:
Task(subagent_type="sdlc-orchestration:software-architect", prompt="Design system architecture for: {feature}")
Task(subagent_type="sdlc-orchestration:data-scientist", prompt="Define data models for: {feature}")
Task(subagent_type="sdlc-orchestration:network-engineer", prompt="Plan infrastructure for: {feature}")
# Optional for UI features:
Task(subagent_type="sdlc-orchestration:ui-designer", prompt="Create visual design for: {feature}")
Task(subagent_type="sdlc-orchestration:frontend-architect", prompt="Design frontend architecture for: {feature}")
Task(subagent_type="sdlc-orchestration:design-system-engineer", prompt="Specify components for: {feature}")
```

**Output:**
- Architecture Decision Record (ADR)
- API specifications
- Database schema
- Infrastructure diagram

```
/sdlc-orchestration:phase design "Design architecture for chat feature based on requirements"
```

### implement

Build the feature with parallel engineering agents.

**Agents (run in parallel):**

| Agent | subagent_type | Focus |
|-------|---------------|-------|
| Staff Engineer | `staff-engineer` | Core architecture, critical paths |
| Senior Engineer | `senior-engineer` | Feature modules, integrations |
| Junior Engineer | `junior-engineer` | UI components, utilities |
| DevOps Engineer | `devops-engineer` | CI/CD, environments |

**Parallel Execution Pattern:**
```python
# Invoke these 4 Task tools in ONE message:
Task(subagent_type="sdlc-orchestration:staff-engineer", prompt="Implement core architecture for: {feature}")
Task(subagent_type="sdlc-orchestration:senior-engineer", prompt="Build feature modules for: {feature}")
Task(subagent_type="sdlc-orchestration:junior-engineer", prompt="Create UI components for: {feature}")
Task(subagent_type="sdlc-orchestration:devops-engineer", prompt="Configure CI/CD for: {feature}")
```

**Output:**
- Production code
- Unit tests
- CI/CD pipeline
- Development documentation

```
/sdlc-orchestration:phase implement "Implement chat feature based on design"
```

### quality

Validate quality with parallel testing and review agents.

**Agents (run in parallel):**

| Agent | subagent_type | Focus |
|-------|---------------|-------|
| QA Automation | `qa-automation` | Test suites, coverage |
| Code Reviewer | `code-reviewer` | PR reviews, standards |
| Performance Engineer | `performance-engineer` | Load tests, optimization |
| Accessibility Specialist | `accessibility-specialist` | WCAG compliance, a11y testing (if UI feature) |

**Parallel Execution Pattern:**
```python
# Invoke these 3-4 Task tools in ONE message:
Task(subagent_type="sdlc-orchestration:qa-automation", prompt="Create and run test suite for: {feature}")
Task(subagent_type="sdlc-orchestration:code-reviewer", prompt="Review implementation of: {feature}")
Task(subagent_type="sdlc-orchestration:performance-engineer", prompt="Performance test: {feature}")
# Optional for UI features:
Task(subagent_type="sdlc-orchestration:accessibility-specialist", prompt="Audit accessibility for: {feature}")
```

**Output:**
- Test results and coverage
- Code review feedback
- Performance test results
- Security scan results

```
/sdlc-orchestration:phase quality "Validate chat feature implementation"
```

### release

Deploy to production with **sequential** release steps (not parallel).

**Agents (run sequentially):**

| Order | Agent | subagent_type | Focus |
|-------|-------|---------------|-------|
| 1 | CI/CD Engineer | `cicd-engineer` | Build, deploy to staging |
| 2 | Canary User | `canary-user` | Beta testing, feedback |
| 3 | Documentation Engineer | `documentation-engineer` | User docs, release notes |
| 4 | DevOps Engineer | `devops-engineer` | Production deployment |

**Sequential Execution Pattern:**
```python
# Run ONE at a time, wait for completion:
result1 = Task(subagent_type="sdlc-orchestration:cicd-engineer", prompt="Deploy to staging: {feature}")
# Wait for staging success...
result2 = Task(subagent_type="sdlc-orchestration:canary-user", prompt="Beta test: {feature}")
# Wait for beta approval...
result3 = Task(subagent_type="sdlc-orchestration:documentation-engineer", prompt="Document: {feature}")
result4 = Task(subagent_type="sdlc-orchestration:devops-engineer", prompt="Deploy to production: {feature}")
```

**Output:**
- Release artifacts
- Beta test feedback
- Updated documentation
- Production deployment

```
/sdlc-orchestration:phase release "Release chat feature to production"
```

## Phase Dependencies

```
requirements → design → implement → quality → release
     │            │          │          │         │
     └────────────┴──────────┴──────────┴─────────┘
                  Each phase gates the next
```

## Phase Execution Details

### Requirements Phase Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    REQUIREMENTS PHASE                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input: Feature description                                 │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ CEO/Stake-  │  │ Business    │  │ Research    │         │
│  │ holder      │  │ Analyst     │  │ Scientist   │         │
│  │             │  │             │  │             │         │
│  │ • Goals     │  │ • Stories   │  │ • Feasib-   │         │
│  │ • Priority  │  │ • Criteria  │  │   ility     │         │
│  │ • ROI       │  │ • NFRs      │  │ • Research  │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          ▼                                  │
│              ┌─────────────────────┐                        │
│              │ Requirements.md     │                        │
│              │ UserStories.md      │                        │
│              │ Feasibility.md      │                        │
│              └─────────────────────┘                        │
│                                                             │
│  Output: Complete requirements package                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Design Phase Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      DESIGN PHASE                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input: Requirements package                                │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Software    │  │ Data        │  │ Network     │         │
│  │ Architect   │  │ Scientist   │  │ Engineer    │         │
│  │             │  │             │  │             │         │
│  │ • System    │  │ • Data      │  │ • Infra     │         │
│  │   design    │  │   models    │  │   topology  │         │
│  │ • APIs      │  │ • ML specs  │  │ • Security  │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          ▼                                  │
│              ┌─────────────────────┐                        │
│              │ ADR-001.md          │                        │
│              │ api-spec.yaml       │                        │
│              │ schema.sql          │                        │
│              │ infra-diagram.md    │                        │
│              └─────────────────────┘                        │
│                                                             │
│  Output: Complete design package                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Result Aggregation

**After all parallel agents complete, you MUST aggregate results before proceeding.**

### Aggregation Protocol

```markdown
## Phase Summary: {phase_name}

### Agent Outputs
| Agent | Status | Key Findings | Artifacts |
|-------|--------|--------------|-----------|
| [agent-1] | completed | [summary] | [files] |
| [agent-2] | completed | [summary] | [files] |
| [agent-3] | completed | [summary] | [files] |

### Synthesis
[Combined insights from all agents]

### Conflicts/Gaps
[Any disagreements or missing information]

### Handoff to Next Phase
[What the next phase needs to know]

### Gate Verification
- [ ] All agents completed
- [ ] Artifacts validated
- [ ] No blocking conflicts
- [ ] Ready for next phase
```

### Phase-Specific Aggregation

**Requirements Phase:**
```markdown
# Requirements Summary

## Business Goals (from CEO/Stakeholder)
[Consolidated business objectives]

## User Stories (from Business Analyst)
[Prioritized story list with acceptance criteria]

## Technical Feasibility (from Research Scientist)
[Feasibility assessment, recommended approaches]

## Handoff to Design
- Approved scope: [list items]
- Technical constraints: [list constraints]
- Priority order: [P0, P1, P2 items]
```

**Design Phase:**
```markdown
# Design Summary

## Architecture (from Software Architect)
[System design, API contracts, patterns]

## Data Model (from Data Scientist)
[Schema, data flows, ML requirements]

## Infrastructure (from Network Engineer)
[Topology, security, scaling plan]

## Handoff to Implementation
- API spec: api-spec.yaml
- Schema: schema.sql
- ADR: ADR-001.md
```

**Quality Phase:**
```markdown
# Quality Summary

## Test Results (from QA Automation)
[Coverage %, pass/fail counts, gaps]

## Code Review (from Code Reviewer)
[Issues found, approvals, blockers]

## Performance (from Performance Engineer)
[Benchmarks, bottlenecks, optimizations needed]

## Handoff to Release
- Tests passing: [yes/no]
- Review approved: [yes/no]
- Performance acceptable: [yes/no]
- Release blockers: [list or none]
```

---

## Example Workflow

```bash
# Step 1: Gather requirements
/sdlc-orchestration:phase requirements "User notification system with email and push"

# Step 2: Create design (after requirements approved)
/sdlc-orchestration:phase design "Design notification system per requirements"

# Step 3: Implement (after design approved)
/sdlc-orchestration:phase implement "Build notification system per design"

# Step 4: Validate quality (after implementation complete)
/sdlc-orchestration:phase quality "Validate notification system"

# Step 5: Release (after quality approved)
/sdlc-orchestration:phase release "Deploy notification system to production"
```
