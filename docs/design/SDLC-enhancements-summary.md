# SDLC Orchestration Enhancements - Design Summary

## Overview

This design document summarizes the architectural enhancements to the SDLC Orchestration plugin based on research findings. The enhancements fall into three categories:

1. **New UI/UX Agent Roles** - 5 specialized agents for user experience
2. **Enhanced Hooks** - Stop, aggregation, and checkpoint hooks
3. **Improved QA Processes** - Pre-flight validation, mutation testing, TDD enforcement

## Design Documents

| Document | Purpose | Location |
|----------|---------|----------|
| ADR-002 | Architecture decision record | `/docs/design/ADR-002-sdlc-uiux-roles-hooks-qa.md` |
| Phase State Template | Updated state management | `/docs/design/SDLC-enhanced-phase-state.json` |
| Hooks Specification | New hook implementations | `/docs/design/SDLC-hooks-enhancement-spec.md` |

## New Agent Definitions

| Agent | Location | Phase(s) | Model |
|-------|----------|----------|-------|
| UX Researcher | `.claude/plugins/sdlc-orchestration/agents/ux-researcher.md` | Requirements, Design | sonnet |
| UI Designer | `.claude/plugins/sdlc-orchestration/agents/ui-designer.md` | Design | sonnet |
| Accessibility Specialist | `.claude/plugins/sdlc-orchestration/agents/accessibility-specialist.md` | Design, Quality | sonnet |
| Frontend Architect | `.claude/plugins/sdlc-orchestration/agents/frontend-architect.md` | Design | opus |
| Design System Engineer | `.claude/plugins/sdlc-orchestration/agents/design-system-engineer.md` | Design, Implementation | sonnet |

## Updated Workflow Diagram

```
================================================================================
                    ENHANCED SDLC WORKFLOW (22 Agents)
================================================================================

PHASE 1: REQUIREMENTS
  Parallel Group:
    +-----------------+  +-----------------+  +-----------------+  +-----------------+
    | CEO/Stakeholder |  | Business        |  | Research        |  | UX Researcher   |
    | (opus)          |  | Analyst         |  | Scientist       |  | (sonnet)        |
    |                 |  | (sonnet)        |  | (opus)          |  |                 |
    | - Business      |  | - User stories  |  | - Feasibility   |  | - User research |
    |   goals         |  | - Acceptance    |  | - Innovation    |  | - Personas      |
    | - ROI           |  |   criteria      |  | - Options       |  | - Journey maps  |
    +-----------------+  +-----------------+  +-----------------+  +-----------------+
                                   |
                    [GATE: Requirements Complete]
                                   |
                                   v

PHASE 2: DESIGN
  Parallel Groups:

  Architecture:
    +-----------------+  +-----------------+  +-----------------+
    | Software        |  | Data Scientist  |  | Network         |
    | Architect       |  | (opus)          |  | Engineer        |
    | (opus)          |  |                 |  | (sonnet)        |
    | - System design |  | - Data models   |  | - Infrastructure|
    | - API contracts |  | - ML specs      |  | - Security      |
    +-----------------+  +-----------------+  +-----------------+

  UI/UX Design:
    +-----------------+  +-----------------+  +-----------------+  +-----------------+
    | Frontend        |  | UI Designer     |  | Accessibility   |  | Design System   |
    | Architect       |  | (sonnet)        |  | Specialist      |  | Engineer        |
    | (opus)          |  |                 |  | (sonnet)        |  | (sonnet)        |
    | - Component     |  | - Wireframes    |  | - WCAG reqs     |  | - Design tokens |
    |   architecture  |  | - Visual design |  | - A11y design   |  | - Component lib |
    | - State mgmt    |  | - Prototypes    |  |                 |  |   spec          |
    +-----------------+  +-----------------+  +-----------------+  +-----------------+
                                   |
                    [GATE: Design Approved + A11y Reviewed]
                                   |
                                   v

PHASE 3: IMPLEMENTATION
  Parallel Group:
    +-----------------+  +-----------------+  +-----------------+  +-----------------+  +-----------------+
    | Staff Engineer  |  | Senior Engineer |  | Junior Engineer |  | DevOps Engineer |  | Design System   |
    | (opus)          |  | (sonnet)        |  | (haiku)         |  | (sonnet)        |  | Engineer        |
    |                 |  |                 |  |                 |  |                 |  | (sonnet)        |
    | - Core arch     |  | - Features      |  | - UI components |  | - CI/CD         |  | - Component     |
    | - Critical path |  | - Integrations  |  | - Utilities     |  | - Environments  |  |   library impl  |
    +-----------------+  +-----------------+  +-----------------+  +-----------------+  +-----------------+
                                   |
                    [GATE: Code Complete + TDD Verified]
                                   |
                                   v

PHASE 4: QUALITY
  Pre-flight Validation:
    +-----------------------------------------------------------------------+
    | Preflight Checks: DB connectivity, Redis, Test fixtures, Env vars     |
    +-----------------------------------------------------------------------+
                                   |
  Parallel Group:
    +-----------------+  +-----------------+  +-----------------+  +-----------------+
    | QA Automation   |  | Code Reviewer   |  | Performance     |  | Accessibility   |
    | (sonnet)        |  | (opus)          |  | Engineer        |  | Specialist      |
    |                 |  |                 |  | (opus)          |  | (sonnet)        |
    | - Test suites   |  | - PR reviews    |  | - Load tests    |  | - WCAG audit    |
    | - Coverage      |  | - Standards     |  | - Optimization  |  | - Screen reader |
    | - Mutation test |  |                 |  |                 |  |   testing       |
    +-----------------+  +-----------------+  +-----------------+  +-----------------+
                                   |
                    [GATE: Quality Approved + Mutation Score > 70%]
                                   |
                                   v

PHASE 5: RELEASE (Sequential)
    +-----------------+     +-----------------+     +-----------------+     +-----------------+
    | CI/CD Engineer  | --> | Canary User     | --> | Documentation   | --> | DevOps Engineer |
    | (sonnet)        |     | (haiku)         |     | Engineer        |     | (sonnet)        |
    |                 |     |                 |     | (sonnet)        |     |                 |
    | - Build         |     | - Beta testing  |     | - User docs     |     | - Production    |
    | - Deploy stage  |     | - Feedback      |     | - Release notes |     |   deploy        |
    +-----------------+     +-----------------+     +-----------------+     +-----------------+
                                   |
                    [CHECKPOINT: Session state saved]

================================================================================
```

## Agent Summary Table

### Original Agents (17)

| Agent | Model | Phase(s) |
|-------|-------|----------|
| CEO/Stakeholder | opus | Requirements |
| Project Manager | sonnet | All (coordination) |
| Business Analyst | sonnet | Requirements |
| Research Scientist | opus | Requirements |
| Software Architect | opus | Design |
| Data Scientist | opus | Design |
| Network Engineer | sonnet | Design |
| Staff Engineer | opus | Implementation |
| Senior Engineer | sonnet | Implementation |
| Junior Engineer | haiku | Implementation |
| DevOps Engineer | sonnet | Implementation, Release |
| QA Automation | sonnet | Quality |
| Code Reviewer | opus | Quality |
| Performance Engineer | opus | Quality |
| CI/CD Engineer | sonnet | Release |
| Canary User | haiku | Release |
| Documentation Engineer | sonnet | Release |

### New Agents (5)

| Agent | Model | Phase(s) | Focus Area |
|-------|-------|----------|------------|
| UX Researcher | sonnet | Requirements, Design | User research, personas, journey mapping |
| UI Designer | sonnet | Design | Visual design, wireframes, prototypes |
| Accessibility Specialist | sonnet | Design, Quality | WCAG compliance, a11y audits |
| Frontend Architect | opus | Design | Component architecture, state management |
| Design System Engineer | sonnet | Design, Implementation | Design tokens, component library |

**Total: 22 Agents** (5 opus, 14 sonnet, 3 haiku)

## Hook Enhancements

### New Hook Types

| Hook | Purpose | Trigger |
|------|---------|---------|
| Stop | Halt on quality gate failure | PostToolUse (Bash) |
| SubagentStop | Aggregate parallel results | SubagentComplete |
| Checkpoint | Save state for recovery | PhaseComplete |
| Preflight | Validate services before tests | PhaseStart (quality) |
| TDD | Enforce test-first development | PreToolUse (Write) |

### Hook Scripts Location

```
.claude/plugins/sdlc-orchestration/hooks/scripts/
├── check_quality_gates.sh    # Stop hook
├── aggregate_results.sh      # Subagent aggregation
├── save_checkpoint.sh        # Checkpoint save
├── restore_checkpoint.sh     # Checkpoint restore
├── check_for_checkpoint.sh   # Session start check
├── preflight_validate.sh     # Pre-flight checks
└── tdd_enforce.sh            # TDD enforcement
```

## QA Process Improvements

### 1. Pre-flight Validation

Before Quality phase tests run:
- Database connectivity check
- Redis connectivity check (optional)
- Test fixtures existence
- Required environment variables
- Mock services health

### 2. Mutation Testing

| Tool | Language | Threshold |
|------|----------|-----------|
| mutmut | Python | 70% (critical), 50% (standard) |
| stryker | TypeScript | 70% (critical), 50% (standard) |

### 3. TDD Enforcement

- Detects new function/class creation
- Warns if no corresponding test file exists
- Suggests test file naming convention
- Non-blocking (warning only)

## Phase Gate Updates

### Enhanced Gates

| Phase | New/Updated Gates |
|-------|-------------------|
| Requirements | `personas_defined`, `journey_maps_created` |
| Design | `a11y_requirements_defined`, `design_system_spec_approved`, `wireframes_approved`, `design_tokens_defined` |
| Implementation | `tdd_verified`, `design_tokens_implemented`, `component_library_complete` |
| Quality | `preflight_validated`, `mutation_score_pass`, `a11y_audit_pass`, `screen_reader_tested` |
| Release | `checkpoint_saved`, `a11y_certification` |

## Implementation Roadmap

### Phase 1: Agent Definitions (Complete)
- [x] Create 5 new agent markdown files
- [x] Define phase participation
- [x] Specify model assignments and tools
- [x] Create ADR document

### Phase 2: Hook Implementation (Next)
- [ ] Implement SubagentComplete hook handler
- [ ] Add Stop hook logic to quality checks
- [ ] Create checkpoint save/restore scripts
- [ ] Integrate preflight validation

### Phase 3: QA Enhancements
- [ ] Add mutation testing integration
- [ ] Implement TDD enforcement hook
- [ ] Update phase-state.json with new gates

### Phase 4: Documentation & Testing
- [ ] Update README.md with new agents
- [ ] Update full-feature.md command
- [ ] Update phase.md command
- [ ] Create integration tests

## Usage Examples

### Invoking New Agents

```bash
# UX Research in Requirements phase
/sdlc-orchestration:role ux-researcher "Conduct user research for dashboard redesign"

# UI Design in Design phase
/sdlc-orchestration:role ui-designer "Create wireframes for settings page"

# Accessibility audit in Quality phase
/sdlc-orchestration:role accessibility-specialist "Audit login form for WCAG 2.1 AA compliance"

# Frontend architecture in Design phase
/sdlc-orchestration:role frontend-architect "Design state management strategy for real-time features"

# Design system in Design/Implementation
/sdlc-orchestration:role design-system-engineer "Create design tokens for color palette"
```

### Updated Full Feature Workflow

```bash
/sdlc-orchestration:full-feature "User dashboard with real-time notifications"

# Phase 1: Requirements (4 agents parallel)
# - CEO: Business goals
# - BA: User stories
# - Research: Technical feasibility
# - UX Researcher: User personas, journey maps

# Phase 2: Design (7 agents parallel)
# - Architect: System design
# - Data Scientist: Data models
# - Network: Infrastructure
# - Frontend Architect: Component architecture
# - UI Designer: Wireframes, visual design
# - A11y Specialist: Accessibility requirements
# - Design System: Design tokens

# Phase 3: Implementation (5 agents parallel)
# - Staff: Core architecture
# - Senior: Features
# - Junior: UI components
# - DevOps: CI/CD
# - Design System: Component library

# Phase 4: Quality (4 agents parallel + preflight)
# - Pre-flight validation
# - QA: Tests + mutation testing
# - Reviewer: Code review
# - Performance: Load tests
# - A11y Specialist: WCAG audit

# Phase 5: Release (sequential + checkpoint)
# - CI/CD: Deploy staging
# - Canary: Beta test
# - Docs: Documentation
# - DevOps: Production
# - Checkpoint saved
```

## File Locations Summary

| File | Purpose |
|------|---------|
| `/docs/design/ADR-002-sdlc-uiux-roles-hooks-qa.md` | Architecture Decision Record |
| `/docs/design/SDLC-enhanced-phase-state.json` | Updated state template |
| `/docs/design/SDLC-hooks-enhancement-spec.md` | Hook implementation specs |
| `/docs/design/SDLC-enhancements-summary.md` | This summary document |
| `.claude/plugins/sdlc-orchestration/agents/ux-researcher.md` | UX Researcher agent |
| `.claude/plugins/sdlc-orchestration/agents/ui-designer.md` | UI Designer agent |
| `.claude/plugins/sdlc-orchestration/agents/accessibility-specialist.md` | Accessibility Specialist agent |
| `.claude/plugins/sdlc-orchestration/agents/frontend-architect.md` | Frontend Architect agent |
| `.claude/plugins/sdlc-orchestration/agents/design-system-engineer.md` | Design System Engineer agent |
