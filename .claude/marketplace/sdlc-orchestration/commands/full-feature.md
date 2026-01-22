---
name: full-feature
description: |
  Execute complete SDLC workflow with all role-based agents working in parallel phases.
  Orchestrates Requirements → Design → Implementation → Quality → Release.
---

# Full Feature Development Workflow

Execute a complete software development lifecycle for a feature using parallelized role-based agents.

## Usage

```
/sdlc-orchestration:full-feature "<feature description>"
```

---

## CRITICAL: Parallel Subagent Execution Pattern

**To achieve true parallelism, invoke multiple Task tools in a SINGLE message.**

### Subagent Types Reference

| Phase | subagent_type values |
|-------|---------------------|
| Requirements | `ceo-stakeholder`, `business-analyst`, `research-scientist` |
| Design | `software-architect`, `data-scientist`, `network-engineer` |
| Implementation | `staff-engineer`, `senior-engineer`, `junior-engineer`, `devops-engineer` |
| Quality | `qa-automation`, `code-reviewer`, `performance-engineer` |
| Release | `cicd-engineer`, `canary-user`, `documentation-engineer` (sequential) |

### Execution Rules

1. **Parallel phases**: Call ALL agents for a phase in ONE message
2. **Sequential phases**: Wait for phase gate before starting next
3. **Release phase**: Run agents one at a time (deployment safety)

---

## Workflow Execution

### Phase 1: Requirements (Parallel Execution)

**PARALLEL: Invoke ALL 3 Task tools in ONE message:**

```
Task(subagent_type="sdlc-orchestration:ceo-stakeholder", prompt="Define business goals, success metrics, and priority for: {feature}")
Task(subagent_type="sdlc-orchestration:business-analyst", prompt="Create user stories with acceptance criteria for: {feature}")
Task(subagent_type="sdlc-orchestration:research-scientist", prompt="Evaluate technical feasibility and research options for: {feature}")
```

Launch the following agents in parallel:

1. **CEO/Stakeholder Agent**
   - Define business objectives and success criteria
   - Set priority and constraints

2. **Business Analyst Agent**
   - Create user stories with acceptance criteria
   - Document functional and non-functional requirements

3. **Research Scientist Agent**
   - Evaluate technical feasibility
   - Identify innovation opportunities

**Gate:** All requirements must be documented before proceeding.

**Aggregation:** After all agents complete:
1. Collect business goals, user stories, feasibility report
2. Create `requirements-summary.md` with consolidated findings
3. Verify no conflicts between agent outputs
4. Update state: `current_phase: "design"`

### Phase 2: Design (Parallel Execution)

**PARALLEL: Invoke ALL 3 Task tools in ONE message:**

```
Task(subagent_type="sdlc-orchestration:software-architect", prompt="Create system design and API contracts based on requirements for: {feature}")
Task(subagent_type="sdlc-orchestration:data-scientist", prompt="Define data models and schemas for: {feature}")
Task(subagent_type="sdlc-orchestration:network-engineer", prompt="Design infrastructure and security topology for: {feature}")
```

Launch the following agents in parallel:

1. **Software Architect Agent**
   - Create system design and API contracts
   - Select technologies and patterns

2. **Data Scientist Agent** (if applicable)
   - Define data requirements
   - Design ML models if needed

3. **Network Engineer Agent** (if applicable)
   - Design infrastructure topology
   - Plan security and connectivity

**Gate:** Architecture must be approved before implementation.

**Aggregation:** After all agents complete:
1. Collect system design, data models, infrastructure plans
2. Create `design-summary.md` with ADR, API spec, schema
3. Verify consistency between architecture, data, and infrastructure
4. Update state: `current_phase: "implementation"`

### Phase 3: Implementation (Parallel by Layer)

**PARALLEL: Invoke ALL 4 Task tools in ONE message:**

```
Task(subagent_type="sdlc-orchestration:staff-engineer", prompt="Implement core architecture and critical paths for: {feature}")
Task(subagent_type="sdlc-orchestration:senior-engineer", prompt="Build feature modules and integrations for: {feature}")
Task(subagent_type="sdlc-orchestration:junior-engineer", prompt="Create UI components and utilities for: {feature}")
Task(subagent_type="sdlc-orchestration:devops-engineer", prompt="Configure CI/CD pipeline and environments for: {feature}")
```

Launch the following agents in parallel:

1. **Staff Engineer Agent**
   - Implement core architecture components
   - Create critical path implementations

2. **Senior Engineer Agent(s)**
   - Build feature modules
   - Implement integrations

3. **Junior Engineer Agent(s)**
   - Create UI components
   - Build utilities and helpers

4. **DevOps Agent**
   - Set up CI/CD pipeline
   - Configure environments

**Gate:** Code must pass linting and basic tests.

**Aggregation:** After all agents complete:
1. Collect all code changes, test files, CI/CD configs
2. Run `ruff check` (Python) or `tsc --noEmit` (TypeScript)
3. Verify all basic tests pass
4. Update state: `current_phase: "quality"`

### Phase 4: Quality (Parallel Execution)

**PARALLEL: Invoke ALL 3 Task tools in ONE message:**

```
Task(subagent_type="sdlc-orchestration:qa-automation", prompt="Create and execute test suite with coverage for: {feature}")
Task(subagent_type="sdlc-orchestration:code-reviewer", prompt="Review all code changes and ensure quality standards for: {feature}")
Task(subagent_type="sdlc-orchestration:performance-engineer", prompt="Run load tests and identify bottlenecks for: {feature}")
```

Launch the following agents in parallel:

1. **QA Automation Agent**
   - Create and run test suites
   - Measure coverage

2. **Code Reviewer Agent**
   - Review all PRs
   - Ensure quality standards

3. **Performance Engineer Agent**
   - Run load tests
   - Identify bottlenecks

4. **Security Auditor** (implicit)
   - Scan for vulnerabilities
   - Validate security controls

**Gate:** All tests must pass, reviews approved.

**Aggregation:** After all agents complete:
1. Collect test results, review feedback, performance metrics
2. Create `quality-summary.md` with coverage %, review status, perf results
3. Verify: tests pass, review approved, no critical performance issues
4. Update state: `current_phase: "release"`

### Phase 5: Release (Sequential - NOT Parallel)

**SEQUENTIAL: Invoke Task tools ONE AT A TIME, waiting for each to complete:**

```
# Step 1: Deploy to staging
result = Task(subagent_type="sdlc-orchestration:cicd-engineer", prompt="Build and deploy to staging: {feature}")
# Wait for success...

# Step 2: Beta validation
result = Task(subagent_type="sdlc-orchestration:canary-user", prompt="Perform beta testing and validation: {feature}")
# Wait for approval...

# Step 3: Documentation
result = Task(subagent_type="sdlc-orchestration:documentation-engineer", prompt="Update documentation and release notes: {feature}")

# Step 4: Production
result = Task(subagent_type="sdlc-orchestration:devops-engineer", prompt="Deploy to production and monitor: {feature}")
```

Execute sequentially:

1. **CI/CD Engineer Agent**
   - Build release artifacts
   - Deploy to staging

2. **Canary User Agent**
   - Perform beta testing
   - Provide feedback

3. **Documentation Engineer Agent**
   - Update user documentation
   - Create release notes

4. **DevOps Agent**
   - Deploy to production
   - Monitor release

**Gate:** Successful canary validation required.

## Parallel Execution Model

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: REQUIREMENTS                                            │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                 │
│ │ CEO/Stake-  │ │ Business    │ │ Research    │  ← PARALLEL     │
│ │ holder      │ │ Analyst     │ │ Scientist   │                 │
│ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘                 │
│        └───────────────┼───────────────┘                        │
│                        ▼                                        │
│                   [GATE: Requirements Complete]                  │
└────────────────────────┼────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: DESIGN                                                  │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                 │
│ │ Software    │ │ Data        │ │ Network     │  ← PARALLEL     │
│ │ Architect   │ │ Scientist   │ │ Engineer    │                 │
│ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘                 │
│        └───────────────┼───────────────┘                        │
│                        ▼                                        │
│                   [GATE: Design Approved]                        │
└────────────────────────┼────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: IMPLEMENTATION                                          │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ Staff       │ │ Senior      │ │ Junior      │ │ DevOps      │ │
│ │ Engineer    │ │ Engineer    │ │ Engineer    │ │ Engineer    │ │
│ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ │
│        └───────────────┴───────────────┴───────────────┘        │
│                        ▼                              ← PARALLEL │
│                   [GATE: Code Complete]                          │
└────────────────────────┼────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 4: QUALITY                                                 │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                 │
│ │ QA          │ │ Code        │ │ Performance │  ← PARALLEL     │
│ │ Automation  │ │ Reviewer    │ │ Engineer    │                 │
│ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘                 │
│        └───────────────┼───────────────┘                        │
│                        ▼                                        │
│                   [GATE: Quality Approved]                       │
└────────────────────────┼────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 5: RELEASE                                                 │
│ CI/CD → Canary → Docs → Production                 ← SEQUENTIAL │
└─────────────────────────────────────────────────────────────────┘
```

## Integration with Sprint System

When used with sprints:

1. Creates sprint items for each phase
2. Updates sprint status as phases complete
3. Stores telemetry in sprint artifacts
4. Links all agent runs to sprint ID

## Example

```
User: /sdlc-orchestration:full-feature "User authentication with OAuth2 and social login"

Phase 1 Output:
- Business goals: Reduce signup friction, increase conversion
- User stories: 5 stories with acceptance criteria
- Feasibility: OAuth2 well-supported, recommend Auth0

Phase 2 Output:
- API design: /auth/*, /users/* endpoints
- Database schema: users, oauth_tokens tables
- Security: JWT tokens, HTTPS required

Phase 3 Output:
- auth_service.py: OAuth2 flow implementation
- auth_routes.py: API endpoints
- AuthButton.tsx: UI component
- CI pipeline configured

Phase 4 Output:
- 95% test coverage
- All PRs approved
- Load test: 1000 RPS sustained
- Security scan: No vulnerabilities

Phase 5 Output:
- Deployed to staging
- Beta feedback: Positive
- Docs updated
- Production deployment complete

Result: Feature complete and deployed
```
