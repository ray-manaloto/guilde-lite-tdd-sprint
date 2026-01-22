# Implementation Plan: [TRACK_NAME]

> **SDLC-Aligned Track** - Follow the 5-phase lifecycle with role-based agents
>
> Use `/sdlc-orchestration:role <role> "task"` for specialized tasks

---

## Phase 1: Requirements [@ba, @research]

**Goal:** Define clear acceptance criteria and validate technical feasibility

- [ ] Task: Gather business requirements [@ba]
    - [ ] Document user stories with acceptance criteria
    - [ ] Identify stakeholder success metrics
- [ ] Task: Technical feasibility analysis [@research]
    - [ ] Evaluate implementation approaches
    - [ ] Identify dependencies and risks

**Gate:** Requirements documented and approved before proceeding

---

## Phase 2: Design [@architect]

**Goal:** Create system design and API contracts

- [ ] Task: System architecture design [@architect]
    - [ ] Define component structure
    - [ ] Create API contracts / schemas
- [ ] Task: Database design (if applicable) [@architect]
    - [ ] Schema changes / migrations
    - [ ] Data flow diagrams

**Gate:** Design approved, contracts defined

---

## Phase 3: Implementation [@staff, @senior, @junior]

**Goal:** Build the feature using TDD (Red → Green → Refactor)

### 3.1 Test Scaffold [@qa]
- [ ] Task: Write failing tests (Red Phase)
    - [ ] Unit tests for new functionality
    - [ ] Integration tests for API endpoints

### 3.2 Core Implementation [@senior]
- [ ] Task: Implement backend logic
    - [ ] Repository layer
    - [ ] Service layer
    - [ ] API routes

### 3.3 Frontend (if applicable) [@junior]
- [ ] Task: Implement UI components
    - [ ] Create components
    - [ ] Connect to API

### 3.4 Infrastructure [@devops]
- [ ] Task: Update CI/CD (if needed)
    - [ ] Add new environment variables
    - [ ] Update deployment configs

**Gate:** All tests passing (Green Phase), coverage >80%

---

## Phase 4: Quality [@qa, @reviewer, @perf]

**Goal:** Validate implementation meets requirements

- [ ] Task: Run full test suite [@qa]
    - [ ] Unit tests pass
    - [ ] Integration tests pass
    - [ ] E2E tests pass (if applicable)
- [ ] Task: Code review [@reviewer]
    - [ ] Review implementation against design
    - [ ] Check for security issues
    - [ ] Verify code style compliance
- [ ] Task: Performance validation [@perf] (if applicable)
    - [ ] Load testing
    - [ ] Query optimization

**Gate:** All quality checks pass, review approved

---

## Phase 5: Release [@cicd, @canary, @docs]

**Goal:** Deploy and document the feature

- [ ] Task: Deploy to staging [@cicd]
    - [ ] Run deployment pipeline
    - [ ] Verify staging environment
- [ ] Task: Manual verification [@canary]
    - [ ] Test user flows
    - [ ] Validate edge cases
- [ ] Task: Update documentation [@docs]
    - [ ] API documentation
    - [ ] User guide updates
    - [ ] Architecture docs (if changed)
- [ ] Task: Conductor checkpoint (Protocol in workflow.md)

**Gate:** Feature deployed, documented, verified

---

## Completion Checklist

- [ ] All phases completed
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Checkpoint commit created
- [ ] Track marked complete in `tracks.md`
