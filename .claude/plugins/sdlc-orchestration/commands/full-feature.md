---
name: full-feature
description: |
  Execute complete SDLC workflow with all role-based agents working in parallel phases.
  Orchestrates Requirements → Design → Implementation → Quality → Release.
  Includes UI/UX agents for comprehensive user experience design.
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
| Requirements | `ceo-stakeholder`, `business-analyst`, `research-scientist`, `ux-researcher` |
| Design | `software-architect`, `data-scientist`, `network-engineer`, `ui-designer`, `accessibility-specialist`, `frontend-architect` |
| Implementation | `staff-engineer`, `senior-engineer`, `junior-engineer`, `devops-engineer`, `design-system-engineer` |
| Quality | `qa-automation`, `code-reviewer`, `performance-engineer`, `accessibility-specialist` |
| Release | `cicd-engineer`, `canary-user`, `documentation-engineer` (sequential) |

### Execution Rules

1. **Parallel phases**: Call ALL agents for a phase in ONE message
2. **Sequential phases**: Wait for phase gate before starting next
3. **Release phase**: Run agents one at a time (deployment safety)

---

## Workflow Execution

### Phase 1: Requirements (Parallel Execution)

**PARALLEL: Invoke ALL 4 Task tools in ONE message:**

```
Task(subagent_type="sdlc-orchestration:ceo-stakeholder", prompt="Define business goals, success metrics, and priority for: {feature}")
Task(subagent_type="sdlc-orchestration:business-analyst", prompt="Create user stories with acceptance criteria for: {feature}")
Task(subagent_type="sdlc-orchestration:research-scientist", prompt="Evaluate technical feasibility and research options for: {feature}")
Task(subagent_type="sdlc-orchestration:ux-researcher", prompt="Conduct user research, create personas, and map user journeys for: {feature}")
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

4. **UX Researcher Agent** (NEW)
   - Conduct user research and create personas
   - Map user journeys with pain points
   - Define usability metrics and success criteria

**Gate:** All requirements must be documented before proceeding.

**Aggregation:** After all agents complete:
1. Collect business goals, user stories, feasibility report, UX research
2. Create `requirements-summary.md` with consolidated findings
3. Verify no conflicts between agent outputs
4. Update state: `current_phase: "design"`

### Phase 2: Design (Parallel Execution)

**PARALLEL: Invoke ALL 6 Task tools in ONE message:**

```
Task(subagent_type="sdlc-orchestration:software-architect", prompt="Create system design and API contracts based on requirements for: {feature}")
Task(subagent_type="sdlc-orchestration:data-scientist", prompt="Define data models and schemas for: {feature}")
Task(subagent_type="sdlc-orchestration:network-engineer", prompt="Design infrastructure and security topology for: {feature}")
Task(subagent_type="sdlc-orchestration:ui-designer", prompt="Create wireframes, mockups, and design specifications for: {feature}")
Task(subagent_type="sdlc-orchestration:accessibility-specialist", prompt="Review designs for WCAG 2.1 AA compliance and provide accessibility requirements for: {feature}")
Task(subagent_type="sdlc-orchestration:frontend-architect", prompt="Design component architecture, state management, and frontend patterns for: {feature}")
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

4. **UI Designer Agent** (NEW)
   - Create wireframes and visual designs
   - Document design specifications
   - Define component states and interactions

5. **Accessibility Specialist Agent** (NEW)
   - Review designs for WCAG compliance
   - Define accessibility requirements
   - Recommend inclusive design patterns

6. **Frontend Architect Agent** (NEW)
   - Design component architecture
   - Plan state management approach
   - Define frontend patterns and standards

**Gate:** Architecture must be approved before implementation.

**Aggregation:** After all agents complete:
1. Collect system design, data models, infrastructure plans, UI specs, a11y requirements
2. Create `design-summary.md` with ADR, API spec, schema, UI spec, a11y checklist
3. Verify consistency between architecture, data, infrastructure, and UI
4. Update state: `current_phase: "implementation"`

### Phase 3: Implementation (Parallel by Layer)

**PARALLEL: Invoke ALL 5 Task tools in ONE message:**

```
Task(subagent_type="sdlc-orchestration:staff-engineer", prompt="Implement core architecture and critical paths for: {feature}")
Task(subagent_type="sdlc-orchestration:senior-engineer", prompt="Build feature modules and integrations for: {feature}")
Task(subagent_type="sdlc-orchestration:junior-engineer", prompt="Create UI components and utilities for: {feature}")
Task(subagent_type="sdlc-orchestration:devops-engineer", prompt="Configure CI/CD pipeline and environments for: {feature}")
Task(subagent_type="sdlc-orchestration:design-system-engineer", prompt="Implement design tokens, component library additions, and ensure design consistency for: {feature}")
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

5. **Design System Engineer Agent** (NEW)
   - Implement design tokens and variables
   - Add components to design system library
   - Ensure visual consistency across implementations

**Gate:** Code must pass linting and basic tests.

**Aggregation:** After all agents complete:
1. Collect all code changes, test files, CI/CD configs, design system updates
2. Run `ruff check` (Python) or `tsc --noEmit` (TypeScript)
3. Verify all basic tests pass
4. Update state: `current_phase: "quality"`

### Phase 4: Quality (Parallel Execution)

**PARALLEL: Invoke ALL 4 Task tools in ONE message:**

```
Task(subagent_type="sdlc-orchestration:qa-automation", prompt="Create and execute test suite with coverage for: {feature}")
Task(subagent_type="sdlc-orchestration:code-reviewer", prompt="Review all code changes and ensure quality standards for: {feature}")
Task(subagent_type="sdlc-orchestration:performance-engineer", prompt="Run load tests and identify bottlenecks for: {feature}")
Task(subagent_type="sdlc-orchestration:accessibility-specialist", prompt="Conduct accessibility audit and verify WCAG compliance for: {feature}")
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

4. **Accessibility Specialist Agent** (Quality Phase)
   - Conduct automated a11y testing
   - Perform manual keyboard/screen reader testing
   - Verify WCAG 2.1 AA compliance

5. **Security Auditor** (implicit)
   - Scan for vulnerabilities
   - Validate security controls

**Gate:** All tests must pass, reviews approved.

**Aggregation:** After all agents complete:
1. Collect test results, review feedback, performance metrics, a11y audit
2. Create `quality-summary.md` with coverage %, review status, perf results, a11y score
3. Verify: tests pass, review approved, no critical performance/a11y issues
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
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: REQUIREMENTS                                                        │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│ │ CEO/Stake-  │ │ Business    │ │ Research    │ │ UX          │  ← PARALLEL │
│ │ holder      │ │ Analyst     │ │ Scientist   │ │ Researcher  │             │
│ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘             │
│        └───────────────┴───────────────┴───────────────┘                    │
│                                 ▼                                            │
│                   [GATE: Requirements Complete]                              │
└─────────────────────────────────┼────────────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: DESIGN                                                              │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │
│ │Software │ │ Data    │ │ Network │ │ UI      │ │ A11y    │ │Frontend │    │
│ │Architect│ │Scientist│ │Engineer │ │Designer │ │Specialist│ │Architect│   │
│ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘    │
│      └──────────┴──────────┴──────────┴──────────┴──────────┘  ← PARALLEL  │
│                                 ▼                                            │
│                   [GATE: Design Approved]                                    │
└─────────────────────────────────┼────────────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: IMPLEMENTATION                                                      │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐             │
│ │ Staff   │ │ Senior  │ │ Junior  │ │ DevOps  │ │Design System│             │
│ │Engineer │ │Engineer │ │Engineer │ │Engineer │ │  Engineer   │             │
│ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └──────┬──────┘             │
│      └──────────┴──────────┴──────────┴───────────────┘        ← PARALLEL  │
│                                 ▼                                            │
│                   [GATE: Code Complete]                                      │
└─────────────────────────────────┼────────────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: QUALITY                                                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│ │ QA          │ │ Code        │ │ Performance │ │Accessibility│  ← PARALLEL │
│ │ Automation  │ │ Reviewer    │ │ Engineer    │ │ Specialist  │             │
│ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘             │
│        └───────────────┴───────────────┴───────────────┘                    │
│                                 ▼                                            │
│                   [GATE: Quality Approved]                                   │
└─────────────────────────────────┼────────────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: RELEASE                                                             │
│ CI/CD → Canary → Docs → Production                              ← SEQUENTIAL│
└─────────────────────────────────────────────────────────────────────────────┘
```

## Agent Roles Per Phase (Regeneration Reference)

Each phase uses specialized agents with distinct responsibilities. Use `/sdlc-orchestration:role <role-name>` to invoke individual agents.

### Phase 1: Requirements Agents

| Agent | subagent_type | Core Responsibilities |
|-------|---------------|----------------------|
| **CEO/Stakeholder** | `ceo-stakeholder` | Business goals, P0/P1/P2 priority, success metrics, ROI |
| **Business Analyst** | `business-analyst` | User stories, acceptance criteria, INVEST format |
| **Research Scientist** | `research-scientist` | Technical feasibility, competitive analysis, innovation |
| **UX Researcher** | `ux-researcher` | User research, personas, journey maps, usability metrics |

**Regenerate Phase 1 agents:**
```
/sdlc-orchestration:role ceo-stakeholder "Reassess business priority for: {feature}"
/sdlc-orchestration:role business-analyst "Refine user stories based on feedback for: {feature}"
/sdlc-orchestration:role research-scientist "Deep-dive technical research for: {feature}"
/sdlc-orchestration:role ux-researcher "Conduct additional user research for: {feature}"
```

### Phase 2: Design Agents

| Agent | subagent_type | Core Responsibilities |
|-------|---------------|----------------------|
| **Software Architect** | `software-architect` | System design, API contracts, ADRs, tech selection |
| **Data Scientist** | `data-scientist` | Data models, schemas, ML architecture, analytics |
| **Network Engineer** | `network-engineer` | Infrastructure topology, security, networking |
| **UI Designer** | `ui-designer` | Wireframes, mockups, design specs, visual language |
| **Accessibility Specialist** | `accessibility-specialist` | WCAG compliance, inclusive design, a11y patterns |
| **Frontend Architect** | `frontend-architect` | Component architecture, state management, frontend patterns |

**Regenerate Phase 2 agents:**
```
/sdlc-orchestration:role software-architect "Revise architecture based on requirements changes for: {feature}"
/sdlc-orchestration:role data-scientist "Update data model for new requirements: {feature}"
/sdlc-orchestration:role network-engineer "Adjust infrastructure design for: {feature}"
/sdlc-orchestration:role ui-designer "Iterate on UI designs based on feedback for: {feature}"
/sdlc-orchestration:role accessibility-specialist "Review updated designs for a11y compliance: {feature}"
/sdlc-orchestration:role frontend-architect "Update component architecture for: {feature}"
```

### Phase 3: Implementation Agents

| Agent | subagent_type | Core Responsibilities |
|-------|---------------|----------------------|
| **Staff Engineer** | `staff-engineer` | Core architecture, critical paths, tech leadership |
| **Senior Engineer** | `senior-engineer` | Feature modules, integrations, mentoring |
| **Junior Engineer** | `junior-engineer` | UI components, utilities, learning tasks |
| **DevOps Engineer** | `devops-engineer` | CI/CD, environments, deployment automation |
| **Design System Engineer** | `design-system-engineer` | Design tokens, component library, visual consistency |

**Regenerate Phase 3 agents:**
```
/sdlc-orchestration:role staff-engineer "Refactor core implementation for: {feature}"
/sdlc-orchestration:role senior-engineer "Add integration tests and fixes for: {feature}"
/sdlc-orchestration:role junior-engineer "Update UI components based on feedback for: {feature}"
/sdlc-orchestration:role devops-engineer "Fix CI/CD pipeline issues for: {feature}"
/sdlc-orchestration:role design-system-engineer "Update design tokens for: {feature}"
```

### Phase 4: Quality Agents

| Agent | subagent_type | Core Responsibilities |
|-------|---------------|----------------------|
| **QA Automation** | `qa-automation` | Test suites, coverage, E2E tests, regression |
| **Code Reviewer** | `code-reviewer` | PR reviews, code quality, standards enforcement |
| **Performance Engineer** | `performance-engineer` | Load testing, profiling, bottleneck analysis |
| **Accessibility Specialist** | `accessibility-specialist` | A11y audits, screen reader testing, WCAG verification |

**Regenerate Phase 4 agents:**
```
/sdlc-orchestration:role qa-automation "Add missing test cases for: {feature}"
/sdlc-orchestration:role code-reviewer "Re-review after fixes applied for: {feature}"
/sdlc-orchestration:role performance-engineer "Run additional load tests for: {feature}"
/sdlc-orchestration:role accessibility-specialist "Re-audit after a11y fixes for: {feature}"
```

### Phase 5: Release Agents

| Agent | subagent_type | Core Responsibilities |
|-------|---------------|----------------------|
| **CI/CD Engineer** | `cicd-engineer` | Build artifacts, staging deployment, release |
| **Canary User** | `canary-user` | Beta testing, user validation, feedback |
| **Documentation Engineer** | `documentation-engineer` | User docs, API docs, release notes |

**Regenerate Phase 5 agents:**
```
/sdlc-orchestration:role cicd-engineer "Rollback and redeploy to staging for: {feature}"
/sdlc-orchestration:role canary-user "Validate hotfix in beta for: {feature}"
/sdlc-orchestration:role documentation-engineer "Update docs with API changes for: {feature}"
```

---

## UI/UX Agent Quick Reference

The following UI/UX agents are now integrated into the workflow:

| Agent | Phase(s) | Key Deliverables |
|-------|----------|------------------|
| **UX Researcher** | Requirements | Personas, journey maps, usability metrics |
| **UI Designer** | Design | Wireframes, mockups, design specs |
| **Accessibility Specialist** | Design, Quality | WCAG checklists, a11y audits |
| **Frontend Architect** | Design | Component architecture, state patterns |
| **Design System Engineer** | Implementation | Design tokens, component library |

---

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
- UX Research: 3 personas, login journey map, usability metrics defined

Phase 2 Output:
- API design: /auth/*, /users/* endpoints
- Database schema: users, oauth_tokens tables
- Security: JWT tokens, HTTPS required
- UI Design: Login wireframes, OAuth button specs
- A11y: Focus management, error states, ARIA labels
- Frontend: AuthContext, useAuth hook, OAuth callback flow

Phase 3 Output:
- auth_service.py: OAuth2 flow implementation
- auth_routes.py: API endpoints
- AuthButton.tsx: UI component
- CI pipeline configured
- Design tokens: auth-related colors, spacing

Phase 4 Output:
- 95% test coverage
- All PRs approved
- Load test: 1000 RPS sustained
- Security scan: No vulnerabilities
- A11y audit: WCAG 2.1 AA compliant

Phase 5 Output:
- Deployed to staging
- Beta feedback: Positive
- Docs updated
- Production deployment complete

Result: Feature complete and deployed
```
