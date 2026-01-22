# ADR-002: SDLC Orchestration Enhancements - UI/UX Roles, Hooks, and QA Improvements

## Status

**Proposed** - 2026-01-22

## Context

Based on research findings, the SDLC Orchestration plugin requires enhancements in three areas:

1. **UI/UX Coverage Gap**: The current 17-agent roster lacks dedicated UI/UX specialists. Frontend work is handled by Junior Engineer (components) and Senior Engineer (features), but there's no dedicated user research, accessibility, or design system expertise.

2. **Hook Limitations**: Current hooks enforce phase gates and backpressure but lack:
   - Stop hooks for quality gate failures
   - SubagentStop hooks for result aggregation
   - Session checkpoints for crash recovery

3. **QA Process Gaps**: Quality phase needs:
   - Pre-flight service validation before tests run
   - Mutation testing for test quality verification
   - TDD enforcement (failing tests before implementation)

## Decision

### 1. Add 5 UI/UX Agent Roles

Add five new specialized agents to the Design and Quality phases:

| Role | Model | Phase | Responsibilities |
|------|-------|-------|------------------|
| UX Researcher | sonnet | Requirements, Design | User research, personas, journey mapping, usability testing |
| UI Designer | sonnet | Design | Visual design, wireframes, prototypes, design specs |
| Accessibility Specialist | sonnet | Design, Quality | WCAG compliance, a11y audits, assistive tech testing |
| Frontend Architect | opus | Design | Component architecture, state management, build optimization |
| Design System Engineer | sonnet | Design, Implementation | Design tokens, component library, documentation |

### 2. Implement Three New Hook Types

#### 2.1 Stop Hook for Quality Gates

```json
{
  "PostToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'check_quality_gates.sh'",
          "stop_on_failure": true,
          "failure_message": "[SDLC STOP] Quality gate failed. Fix issues before proceeding."
        }
      ]
    }
  ]
}
```

#### 2.2 SubagentStop Hook for Aggregation

```json
{
  "SubagentComplete": [
    {
      "matcher": "sdlc-orchestration:*",
      "hooks": [
        {
          "type": "aggregate",
          "command": "bash -c 'aggregate_results.sh \"$AGENT_TYPE\" \"$AGENT_OUTPUT\"'",
          "collect_until": "phase_agents_complete"
        }
      ]
    }
  ]
}
```

#### 2.3 Session Checkpoint Hook

```json
{
  "PhaseComplete": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "checkpoint",
          "command": "bash -c 'save_checkpoint.sh \"$PHASE\" \"$STATE\"'",
          "restore_on": "SessionStart"
        }
      ]
    }
  ]
}
```

### 3. QA Process Improvements

#### 3.1 Pre-flight Service Validation

Add to Quality phase entry:
- Verify database connectivity
- Check external service mocks
- Validate environment variables
- Confirm test fixtures exist

#### 3.2 Mutation Testing Integration

Add mutation testing step after unit tests:
- Use `mutmut` (Python) or `stryker` (TypeScript)
- Require mutation score > 70% for critical paths
- Generate mutation coverage report

#### 3.3 TDD Enforcement

Add PreToolUse hook for Write operations:
- Detect new function/class creation
- Check for corresponding test file
- Warn if implementation precedes tests

## Consequences

### Positive

- **Better UX outcomes**: Dedicated research and design expertise
- **Accessibility by default**: A11y specialist in design AND quality phases
- **Stronger quality gates**: Stop hooks prevent bad code progression
- **Crash resilience**: Session checkpoints enable recovery
- **Higher test quality**: Mutation testing validates test effectiveness
- **TDD discipline**: Enforcement encourages test-first development

### Negative

- **Increased complexity**: 22 agents instead of 17
- **Longer execution**: More agents = more time per phase
- **Hook overhead**: More hooks = more processing per operation
- **Learning curve**: Teams need to understand new roles

### Mitigations

- UI/UX agents are optional (skip for backend-only features)
- Use Haiku model for lightweight agents where appropriate
- Hook scripts must complete in < 5 seconds
- Provide clear documentation for new roles

## Alternatives Considered

### 1. Expand Existing Roles Instead of New Agents

**Rejected**: Junior Engineer handling UX research dilutes expertise. Specialized roles produce better outcomes.

### 2. Single "Design" Agent Covering All UI/UX

**Rejected**: Too much responsibility for one agent. Parallel specialists enable concurrent work.

### 3. External Hook System (Webhooks)

**Rejected**: Adds network dependency and latency. Local hooks are faster and more reliable.

## Implementation Plan

### Phase 1: Agent Definitions (This ADR)
- Create 5 new agent markdown files
- Update phase-state.json template
- Update workflow documentation

### Phase 2: Hook Implementation
- Implement SubagentComplete hook type
- Add Stop hook logic to existing hooks
- Create checkpoint storage mechanism

### Phase 3: QA Enhancements
- Add pre-flight validation script
- Integrate mutation testing tools
- Implement TDD enforcement hook

## File Structure

```
.claude/plugins/sdlc-orchestration/
├── agents/
│   ├── ux-researcher.md          # NEW
│   ├── ui-designer.md            # NEW
│   ├── accessibility-specialist.md  # NEW
│   ├── frontend-architect.md     # NEW
│   ├── design-system-engineer.md # NEW
│   ├── ... (existing agents)
├── commands/
│   ├── full-feature.md           # UPDATE (add new agents)
│   ├── phase.md                  # UPDATE (add new agents)
│   └── ...
├── hooks/
│   ├── hooks.json                # UPDATE (add new hook types)
│   └── scripts/
│       ├── check_quality_gates.sh   # NEW
│       ├── aggregate_results.sh     # NEW
│       ├── save_checkpoint.sh       # NEW
│       ├── restore_checkpoint.sh    # NEW
│       ├── preflight_validate.sh    # NEW
│       └── tdd_enforce.sh           # NEW
├── skills/
│   └── sdlc-orchestrator/
│       ├── SKILL.md              # UPDATE
│       └── templates/
│           └── phase-state.json  # UPDATE
└── README.md                     # UPDATE
```

## Related Skills

The following installed skills provide implementation guidance:

- `ai-research-agents-langchain` - For multi-agent orchestration patterns
- `ai-research-observability-langsmith` - For agent telemetry and tracing
- `playwright-skill` - For UI/UX testing automation

Read with: `cat skills/<skill-name>/SKILL.md`

---

## Appendix A: Agent Definition Files

### A.1 UX Researcher Agent

See: `.claude/plugins/sdlc-orchestration/agents/ux-researcher.md`

### A.2 UI Designer Agent

See: `.claude/plugins/sdlc-orchestration/agents/ui-designer.md`

### A.3 Accessibility Specialist Agent

See: `.claude/plugins/sdlc-orchestration/agents/accessibility-specialist.md`

### A.4 Frontend Architect Agent

See: `.claude/plugins/sdlc-orchestration/agents/frontend-architect.md`

### A.5 Design System Engineer Agent

See: `.claude/plugins/sdlc-orchestration/agents/design-system-engineer.md`

---

## Appendix B: Updated Workflow Diagram

```
                            ENHANCED SDLC WORKFLOW
================================================================================

Phase 1: REQUIREMENTS (Parallel)
├── CEO/Stakeholder      → Business goals, ROI
├── Business Analyst     → User stories, acceptance criteria
├── Research Scientist   → Technical feasibility
└── UX Researcher        → User research, personas, journey maps   [NEW]
                         ↓
                    [GATE: Requirements Complete]
                         ↓

Phase 2: DESIGN (Parallel)
├── Software Architect   → System design, API contracts
├── Data Scientist       → Data models, schemas
├── Network Engineer     → Infrastructure topology
├── Frontend Architect   → Component architecture, state mgmt     [NEW]
├── UI Designer          → Visual design, wireframes, prototypes  [NEW]
├── Accessibility Spec   → WCAG requirements, a11y design        [NEW]
└── Design System Eng    → Design tokens, component specs        [NEW]
                         ↓
                    [GATE: Design Approved]
                         ↓

Phase 3: IMPLEMENTATION (Parallel by Layer)
├── Staff Engineer       → Core architecture, critical paths
├── Senior Engineer      → Feature modules, integrations
├── Junior Engineer      → UI components, utilities
├── DevOps Engineer      → CI/CD, environments
└── Design System Eng    → Component library implementation       [SHARED]
                         ↓
                    [GATE: Code Complete + TDD Verified]          [ENHANCED]
                         ↓

Phase 4: QUALITY (Parallel)
├── QA Automation        → Test suites, coverage
├── Code Reviewer        → PR reviews, standards
├── Performance Engineer → Load tests, optimization
├── Accessibility Spec   → WCAG audit, screen reader testing     [SHARED]
└── Pre-flight Validator → Service health, env validation        [NEW STEP]
                         ↓
                    [GATE: Quality Approved + Mutation Score > 70%] [ENHANCED]
                         ↓

Phase 5: RELEASE (Sequential)
├── CI/CD Engineer       → Build, deploy to staging
├── Canary User          → Beta testing, feedback
├── Documentation Engineer → User docs, release notes
└── DevOps Engineer      → Production deployment
                         ↓
                    [CHECKPOINT: Session state saved]             [NEW]

================================================================================
```

---

## Appendix C: Updated Phase State Template

```json
{
  "agents_by_phase": {
    "requirements": [
      "ceo-stakeholder",
      "business-analyst",
      "research-scientist",
      "ux-researcher"
    ],
    "design": [
      "software-architect",
      "data-scientist",
      "network-engineer",
      "frontend-architect",
      "ui-designer",
      "accessibility-specialist",
      "design-system-engineer"
    ],
    "implementation": [
      "staff-engineer",
      "senior-engineer",
      "junior-engineer",
      "devops-engineer",
      "design-system-engineer"
    ],
    "quality": [
      "qa-automation",
      "code-reviewer",
      "performance-engineer",
      "accessibility-specialist"
    ],
    "release": [
      "cicd-engineer",
      "canary-user",
      "documentation-engineer",
      "devops-engineer"
    ]
  },
  "gates": {
    "requirements": [
      "all_agents_complete",
      "artifacts_validated",
      "stakeholder_approved",
      "personas_defined"
    ],
    "design": [
      "architecture_reviewed",
      "api_contract_approved",
      "security_reviewed",
      "a11y_requirements_defined",
      "design_system_spec_approved"
    ],
    "implementation": [
      "code_complete",
      "unit_tests_pass",
      "lint_pass",
      "type_check_pass",
      "tdd_verified",
      "design_tokens_implemented"
    ],
    "quality": [
      "preflight_validated",
      "integration_tests_pass",
      "code_review_approved",
      "performance_validated",
      "security_scan_pass",
      "mutation_score_pass",
      "a11y_audit_pass"
    ],
    "release": [
      "staging_deployed",
      "canary_validated",
      "docs_updated",
      "production_approved",
      "checkpoint_saved"
    ]
  }
}
```
