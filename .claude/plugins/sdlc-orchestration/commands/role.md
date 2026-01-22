---
name: role
description: |
  Invoke a specific SDLC role agent directly for targeted tasks.
  Available roles: ceo, pm, architect, ba, research, staff, senior, junior, qa, reviewer, devops, network, cicd, canary, docs, perf, data.
---

# Role-Specific Agent Invocation

Invoke a specific role-based agent for targeted tasks without running the full SDLC workflow.

## Usage

```
/sdlc-orchestration:role <role> "<task description>"
```

## Available Roles

| Role | Agent | Model | Best For |
|------|-------|-------|----------|
| `ceo` | CEO/Stakeholder | opus | Business decisions, priorities |
| `pm` | Project Manager | sonnet | Planning, coordination, tracking |
| `architect` | Software Architect | opus | System design, API contracts |
| `ba` | Business Analyst | sonnet | Requirements, user stories |
| `research` | Research Scientist | opus | Feasibility, innovation |
| `staff` | Staff Engineer | opus | Critical implementations |
| `senior` | Senior Engineer | sonnet | Feature development |
| `junior` | Junior Engineer | haiku | UI components, utilities |
| `qa` | QA Automation | sonnet | Test strategy, automation |
| `reviewer` | Code Reviewer | opus | PR reviews, quality gates |
| `devops` | DevOps Engineer | sonnet | Infrastructure, deployments |
| `network` | Network Engineer | sonnet | Networking, security topology |
| `cicd` | CI/CD Engineer | sonnet | Pipelines, release automation |
| `canary` | Canary User | haiku | Beta testing, user feedback |
| `docs` | Documentation Engineer | sonnet | Technical writing, API docs |
| `perf` | Performance Engineer | opus | Load testing, optimization |
| `data` | Data Scientist | opus | Data requirements, ML models |

## Examples

### Architecture Design
```
/sdlc-orchestration:role architect "Design microservices architecture for e-commerce platform"
```

### Code Review
```
/sdlc-orchestration:role reviewer "Review the authentication module PR #123"
```

### Performance Analysis
```
/sdlc-orchestration:role perf "Analyze API latency issues in the checkout flow"
```

### Requirements Gathering
```
/sdlc-orchestration:role ba "Create user stories for the reporting dashboard feature"
```

### Infrastructure Setup
```
/sdlc-orchestration:role devops "Set up Kubernetes deployment for the API service"
```

### Test Strategy
```
/sdlc-orchestration:role qa "Design test strategy for the payment integration"
```

### Beta Testing
```
/sdlc-orchestration:role canary "Test the new checkout flow as a beta user"
```

## Role Combinations

For complex tasks, you can invoke multiple roles sequentially:

```bash
# 1. Get requirements
/sdlc-orchestration:role ba "Create user stories for notifications feature"

# 2. Design architecture
/sdlc-orchestration:role architect "Design notification service based on BA requirements"

# 3. Implement
/sdlc-orchestration:role senior "Implement notification service from architect's design"

# 4. Test
/sdlc-orchestration:role qa "Create test suite for notification service"

# 5. Review
/sdlc-orchestration:role reviewer "Review notification service implementation"
```

## Parallel Role Execution

To run multiple roles in parallel, use the Task tool with multiple agents:

```
"Run architect and data roles in parallel to design the recommendation system"
```

This will spawn both agents simultaneously and collect their outputs.

## Output Format

Each role provides structured output following their agent templates:
- Architects: ADRs, API specs, diagrams
- BAs: User stories, requirements docs
- Engineers: Code, tests, documentation
- QA: Test plans, coverage reports
- Reviewers: Review comments, approval status
- DevOps: Infrastructure configs, runbooks
