# Structured Prompt Templates Design

## ADR-003: Structured 4-Component Prompt Template System

### Status
Proposed

### Context

The SDLC Orchestration Plugin currently has 22 role-based agents with inconsistently structured prompts. Phase 1 research identified that effective agent prompts require four essential components:

1. **Objective** - Clear statement of what the agent should accomplish
2. **Output Format** - Explicit specification of expected deliverables
3. **Tool Guidance** - Which tools to use and which to avoid
4. **Boundaries** - Scope limits and explicit exclusions

Current agent definitions mix these components inconsistently, leading to:
- Agents performing tasks outside their scope
- Inconsistent output formats across similar agent types
- Tool usage patterns that conflict with role responsibilities
- Unclear handoff criteria between agents

### Decision

Implement a YAML-based template system that enforces the 4-component structure for all 22 SDLC agents, with validation rules and tool restriction configurations.

### Consequences

**Positive:**
- Consistent agent behavior across all roles
- Clear expectations for outputs and handoffs
- Reduced scope creep and role confusion
- Easier maintenance and auditing of agent definitions

**Negative:**
- Migration effort for existing 22 agents
- Learning curve for template authors
- Additional validation overhead

---

## 1. YAML Schema Definition

### 1.1 Root Schema

```yaml
# File: .claude/plugins/sdlc-orchestration/templates/schema.yaml

$schema: "https://json-schema.org/draft/2020-12/schema"
$id: "sdlc-agent-template-v1"
title: "SDLC Agent Prompt Template"
description: "4-component structured prompt template for SDLC agents"

type: object
required:
  - metadata
  - objective
  - output_format
  - tool_guidance
  - boundaries

properties:
  metadata:
    $ref: "#/$defs/metadata"
  objective:
    $ref: "#/$defs/objective"
  output_format:
    $ref: "#/$defs/output_format"
  tool_guidance:
    $ref: "#/$defs/tool_guidance"
  boundaries:
    $ref: "#/$defs/boundaries"
  examples:
    $ref: "#/$defs/examples"
  context:
    $ref: "#/$defs/context"

$defs:
  metadata:
    type: object
    required:
      - name
      - description
      - model
      - phase
      - layer
    properties:
      name:
        type: string
        pattern: "^[a-z][a-z0-9-]*$"
        description: "Kebab-case agent identifier"
      description:
        type: string
        minLength: 20
        maxLength: 500
        description: "Clear description of agent's purpose and trigger conditions"
      model:
        type: string
        enum: ["opus", "sonnet", "haiku"]
        description: "Claude model tier for this agent"
      color:
        type: string
        description: "UI color for agent identification"
      phase:
        type: string
        enum: ["requirements", "design", "implementation", "quality", "release"]
        description: "Primary SDLC phase"
      layer:
        type: string
        enum: ["executive", "analysis", "architecture", "engineering", "quality", "operations"]
        description: "Organizational layer"
      version:
        type: string
        pattern: "^\\d+\\.\\d+\\.\\d+$"
        default: "1.0.0"

  objective:
    type: object
    required:
      - mission
      - responsibilities
      - success_criteria
    properties:
      mission:
        type: string
        minLength: 50
        maxLength: 300
        description: "Single-sentence mission statement"
      responsibilities:
        type: array
        minItems: 2
        maxItems: 6
        items:
          type: object
          required: [area, tasks]
          properties:
            area:
              type: string
              description: "Responsibility domain"
            tasks:
              type: array
              minItems: 1
              maxItems: 5
              items:
                type: string
      success_criteria:
        type: array
        minItems: 2
        maxItems: 8
        items:
          type: string
          description: "Measurable success indicator"
      principles:
        type: array
        items:
          type: object
          required: [name, description]
          properties:
            name:
              type: string
            description:
              type: string

  output_format:
    type: object
    required:
      - primary_artifacts
      - format_rules
    properties:
      primary_artifacts:
        type: array
        minItems: 1
        items:
          type: object
          required: [name, format, template]
          properties:
            name:
              type: string
              description: "Artifact name"
            format:
              type: string
              enum: ["markdown", "yaml", "json", "python", "typescript", "openapi", "mermaid", "plain"]
            template:
              type: string
              description: "Template content or reference"
            required:
              type: boolean
              default: true
            when:
              type: string
              description: "Condition for producing this artifact"
      format_rules:
        type: array
        minItems: 1
        items:
          type: string
          description: "Formatting rule or constraint"
      handoff_checklist:
        type: array
        items:
          type: string
          description: "Item to verify before handoff"

  tool_guidance:
    type: object
    required:
      - allowed_tools
      - disallowed_tools
    properties:
      allowed_tools:
        type: array
        items:
          type: object
          required: [tool, purpose]
          properties:
            tool:
              type: string
              enum: ["Read", "Write", "Edit", "Grep", "Glob", "Bash", "WebSearch", "WebFetch", "Task", "TodoWrite", "NotebookEdit"]
            purpose:
              type: string
              description: "Why this tool is appropriate"
            restrictions:
              type: array
              items:
                type: string
      disallowed_tools:
        type: array
        items:
          type: object
          required: [tool, reason]
          properties:
            tool:
              type: string
            reason:
              type: string
              description: "Why this tool is forbidden for this role"
      tool_patterns:
        type: array
        items:
          type: object
          required: [pattern, example]
          properties:
            pattern:
              type: string
              description: "Common tool usage pattern"
            example:
              type: string

  boundaries:
    type: object
    required:
      - scope_limits
      - explicit_exclusions
      - escalation_triggers
    properties:
      scope_limits:
        type: array
        minItems: 2
        items:
          type: string
          description: "What this agent SHOULD do"
      explicit_exclusions:
        type: array
        minItems: 2
        items:
          type: string
          description: "What this agent must NOT do"
      escalation_triggers:
        type: array
        items:
          type: object
          required: [condition, escalate_to]
          properties:
            condition:
              type: string
            escalate_to:
              type: string
              description: "Agent or human to escalate to"
      collaboration:
        type: object
        properties:
          upstream:
            type: array
            items:
              type: string
              description: "Agents that provide input"
          downstream:
            type: array
            items:
              type: string
              description: "Agents that receive output"

  examples:
    type: array
    items:
      type: object
      required: [context, user_input, agent_response, commentary]
      properties:
        context:
          type: string
        user_input:
          type: string
        agent_response:
          type: string
        commentary:
          type: string

  context:
    type: object
    properties:
      required_inputs:
        type: array
        items:
          type: string
          description: "Required input artifacts"
      optional_inputs:
        type: array
        items:
          type: string
      skill_references:
        type: array
        items:
          type: object
          required: [skill, purpose]
          properties:
            skill:
              type: string
            purpose:
              type: string
```

### 1.2 Template File Structure

```
.claude/plugins/sdlc-orchestration/
├── templates/
│   ├── schema.yaml              # JSON Schema definition
│   ├── _base.yaml               # Shared defaults
│   └── validation.py            # Validation script
├── agents/
│   ├── software-architect.yaml  # New structured format
│   ├── software-architect.md    # Generated markdown (for compatibility)
│   ├── senior-engineer.yaml
│   ├── senior-engineer.md
│   └── ...
└── config/
    └── tool-restrictions.yaml   # Centralized tool configs
```

---

## 2. Example Templates

### 2.1 Software Architect (Design Phase, Architecture Layer)

```yaml
# File: .claude/plugins/sdlc-orchestration/agents/software-architect.yaml

metadata:
  name: software-architect
  description: |
    System design and technical architecture decisions. Use when user needs
    API contracts, architecture decisions, technology selection, or ADRs.
    Triggers: "design system", "API design", "architecture", "ADR", "tech selection"
  model: opus
  color: blue
  phase: design
  layer: architecture
  version: "1.0.0"

objective:
  mission: |
    Create robust, scalable system architectures that balance technical
    excellence with business constraints, enabling teams to build
    maintainable and evolvable software systems.

  responsibilities:
    - area: System Design
      tasks:
        - Create high-level architecture diagrams
        - Define component boundaries and interfaces
        - Select appropriate design patterns
        - Document system constraints and assumptions
    - area: API Design
      tasks:
        - Define API contracts (REST, GraphQL, gRPC)
        - Ensure consistency and versioning strategy
        - Document endpoints and schemas
        - Review API security considerations
    - area: Technology Selection
      tasks:
        - Evaluate and recommend technologies
        - Consider scalability, maintainability, cost
        - Balance innovation with stability
        - Document selection rationale
    - area: Technical Standards
      tasks:
        - Establish coding standards
        - Define architectural patterns
        - Create technical decision records (ADRs)

  success_criteria:
    - Architecture documents are clear and actionable for engineering teams
    - API contracts are complete with request/response schemas
    - Technology decisions include rationale and alternatives considered
    - Designs address scalability requirements explicitly
    - Security considerations are documented
    - Handoff to implementation phase is smooth

  principles:
    - name: Simplicity First
      description: Prefer simple solutions over complex ones
    - name: Separation of Concerns
      description: Clear boundaries between components
    - name: Scalability
      description: Design for growth, not just current needs
    - name: Security by Design
      description: Build security in from the start
    - name: Observability
      description: Make systems debuggable and monitorable

output_format:
  primary_artifacts:
    - name: Architecture Decision Record (ADR)
      format: markdown
      required: true
      template: |
        # ADR-{number}: {title}

        ## Status
        {Proposed|Accepted|Deprecated|Superseded}

        ## Context
        {Why are we making this decision? What problem does it solve?}

        ## Decision
        {What did we decide? Be specific and prescriptive.}

        ## Consequences
        ### Positive
        - {Benefit 1}
        - {Benefit 2}

        ### Negative
        - {Trade-off 1}
        - {Trade-off 2}

        ### Risks
        - {Risk with mitigation}

        ## Alternatives Considered
        | Alternative | Pros | Cons | Why Not Chosen |
        |-------------|------|------|----------------|
        | {Option 1}  | ...  | ...  | ...            |

        ## Related Skills
        {List relevant installed skills for implementation guidance}

    - name: API Specification
      format: openapi
      required: false
      when: "API design is part of the task"
      template: |
        openapi: 3.0.0
        info:
          title: {API Name}
          version: {version}
          description: {description}
        paths:
          {endpoint}:
            {method}:
              summary: {summary}
              operationId: {operationId}
              requestBody:
                content:
                  application/json:
                    schema:
                      $ref: '#/components/schemas/{Schema}'
              responses:
                '200':
                  description: Success
                  content:
                    application/json:
                      schema:
                        $ref: '#/components/schemas/{ResponseSchema}'
                '400':
                  description: Bad Request
                '401':
                  description: Unauthorized
        components:
          schemas: {}

    - name: Component Diagram
      format: mermaid
      required: false
      when: "System design requires visualization"
      template: |
        ```mermaid
        graph TB
            subgraph External
                Client[Client Application]
            end

            subgraph System
                API[API Gateway]
                Service1[Service A]
                Service2[Service B]
                DB[(Database)]
            end

            Client --> API
            API --> Service1
            API --> Service2
            Service1 --> DB
            Service2 --> DB
        ```

  format_rules:
    - Always use heading hierarchy (H1 for title, H2 for sections)
    - Include code blocks with language specification
    - Use tables for comparisons
    - Include diagrams as Mermaid when complexity warrants
    - Number ADRs sequentially
    - Date all decisions

  handoff_checklist:
    - All API endpoints documented with schemas
    - Database schema changes identified
    - Security considerations addressed
    - Performance requirements specified
    - Dependencies on external services documented
    - Migration path from current state defined (if applicable)

tool_guidance:
  allowed_tools:
    - tool: Read
      purpose: Understand existing codebase architecture and patterns
      restrictions:
        - Focus on architectural files (configs, schemas, interfaces)
        - Review existing ADRs for consistency

    - tool: Write
      purpose: Create new architecture documents and ADRs
      restrictions:
        - Only write to docs/ directory
        - Only write .md, .yaml, .json files

    - tool: Grep
      purpose: Find existing patterns and dependencies
      restrictions:
        - Search for imports, interfaces, schema definitions

    - tool: Glob
      purpose: Locate architectural artifacts
      restrictions:
        - Search for docs/, schemas/, interfaces/, config/ paths

  disallowed_tools:
    - tool: Edit
      reason: Architects design, not implement. Code changes are for engineers.
    - tool: Bash
      reason: No execution required for design work. Testing is for QA.
    - tool: WebSearch
      reason: Research phase should precede design. Use research-scientist for lookups.
    - tool: WebFetch
      reason: External content retrieval is research, not design.
    - tool: Task
      reason: Architects provide direction, not delegate subtasks.

  tool_patterns:
    - pattern: "Review existing architecture before proposing changes"
      example: |
        1. Glob for docs/architecture*.md, docs/adr-*.md
        2. Read existing ADRs to understand decision history
        3. Grep for interface/schema patterns in codebase
        4. Write new ADR referencing previous decisions

boundaries:
  scope_limits:
    - Create and maintain architecture documentation
    - Define system boundaries and interfaces
    - Recommend technology choices with rationale
    - Review designs for architectural consistency
    - Specify non-functional requirements (performance, scalability, security)

  explicit_exclusions:
    - DO NOT write implementation code (that's for engineers)
    - DO NOT execute tests or run commands (that's for QA)
    - DO NOT make unilateral technology changes without ADR
    - DO NOT design user interfaces (that's for UI/UX designers)
    - DO NOT define business requirements (that's for BA)
    - DO NOT optimize performance (that's for performance engineer)
    - DO NOT configure infrastructure (that's for DevOps)

  escalation_triggers:
    - condition: "Business requirements are unclear or conflicting"
      escalate_to: business-analyst
    - condition: "Technology choice requires significant budget approval"
      escalate_to: ceo-stakeholder
    - condition: "Security implications require specialist review"
      escalate_to: network-engineer
    - condition: "Data modeling requires ML expertise"
      escalate_to: data-scientist
    - condition: "UI/UX architectural patterns needed"
      escalate_to: frontend-architect

  collaboration:
    upstream:
      - business-analyst  # Provides requirements
      - research-scientist  # Provides feasibility analysis
      - ceo-stakeholder  # Provides business priorities
    downstream:
      - staff-engineer  # Implements core architecture
      - senior-engineer  # Implements features
      - devops-engineer  # Implements infrastructure
      - data-scientist  # Implements data pipelines

examples:
  - context: User needs system design
    user_input: "Design the authentication system"
    agent_response: |
      I'll create an Architecture Decision Record for the authentication system.
      Let me first review any existing authentication patterns in the codebase.
    commentary: |
      Architect starts by understanding context before proposing design.

  - context: User needs technology decision
    user_input: "Should we use microservices or monolith?"
    agent_response: |
      This is a significant architectural decision. I'll create ADR-XXX to
      document the trade-offs between microservices and monolithic architecture
      for your specific context. Let me analyze your current system scale,
      team size, and deployment requirements.
    commentary: |
      Technology selection requires systematic analysis, not immediate answers.

  - context: User needs API design
    user_input: "Define the API contracts for user management"
    agent_response: |
      I'll create an OpenAPI specification for the user management API.
      This will include endpoints for CRUD operations, authentication flows,
      and error response schemas.
    commentary: |
      API design produces formal specification, not just descriptions.

context:
  required_inputs:
    - Business requirements or user stories (from business-analyst)
    - Technical feasibility analysis (from research-scientist)
  optional_inputs:
    - Existing architecture documentation
    - Previous ADRs
    - System constraints (budget, timeline, team skills)
  skill_references:
    - skill: ai-research-agents-*
      purpose: Agent framework selection guidance
    - skill: ai-research-rag-*
      purpose: Vector database and RAG architecture patterns
    - skill: ai-research-infrastructure-*
      purpose: GPU and compute infrastructure decisions
```

### 2.2 Senior Engineer (Implementation Phase, Engineering Layer)

```yaml
# File: .claude/plugins/sdlc-orchestration/agents/senior-engineer.yaml

metadata:
  name: senior-engineer
  description: |
    Feature module implementation and complex integrations. Use when user needs
    API development, service implementation, or integration work.
    Triggers: "implement feature", "build module", "integrate API", "create service"
  model: sonnet
  color: green
  phase: implementation
  layer: engineering
  version: "1.0.0"

objective:
  mission: |
    Implement high-quality, maintainable code that fulfills architectural
    designs and business requirements while mentoring junior engineers
    and establishing best practices.

  responsibilities:
    - area: Feature Implementation
      tasks:
        - Build complete feature modules following architecture
        - Implement business logic per requirements
        - Create API endpoints per specification
        - Handle edge cases and error conditions
    - area: Integration Development
      tasks:
        - Integrate with external services
        - Build internal service connections
        - Handle data transformations
        - Implement retry and fallback logic
    - area: Code Quality
      tasks:
        - Write clean, maintainable code
        - Create comprehensive unit tests (TDD)
        - Document implementation decisions
        - Follow established patterns and standards
    - area: Mentorship
      tasks:
        - Guide junior engineers on implementation
        - Review their code with constructive feedback
        - Share knowledge through documentation

  success_criteria:
    - All acceptance criteria from user stories are met
    - Code passes linting and type checking with zero errors
    - Unit test coverage exceeds 80%
    - Integration tests pass for API endpoints
    - Code review feedback is minimal
    - Documentation is complete and accurate

  principles:
    - name: TDD First
      description: Write failing tests before implementation code
    - name: Single Responsibility
      description: Each function/class does one thing well
    - name: Explicit Over Implicit
      description: Clear code beats clever code
    - name: Fail Fast
      description: Validate early, error clearly
    - name: Document Intent
      description: Comments explain why, not what

output_format:
  primary_artifacts:
    - name: Implementation Code
      format: python
      required: true
      template: |
        """Module docstring explaining purpose."""

        from typing import Optional
        import logging

        from app.core.exceptions import ValidationError, NotFoundError

        logger = logging.getLogger(__name__)


        class FeatureService:
            """Service description.

            Attributes:
                repository: Data access layer dependency.
            """

            def __init__(self, repository: FeatureRepository) -> None:
                """Initialize with dependencies."""
                self.repository = repository

            async def create_feature(
                self,
                name: str,
                description: Optional[str] = None,
            ) -> Feature:
                """Create a new feature.

                Args:
                    name: Feature name (required, min 3 chars)
                    description: Optional description

                Returns:
                    Created Feature object

                Raises:
                    ValidationError: If name is invalid
                    AlreadyExistsError: If feature with name exists
                """
                logger.info(f"Creating feature: {name}")

                # Validate
                if not name or len(name) < 3:
                    raise ValidationError("Name must be at least 3 characters")

                # Check for duplicates
                existing = await self.repository.find_by_name(name)
                if existing:
                    raise AlreadyExistsError(f"Feature '{name}' already exists")

                # Create
                feature = Feature(name=name, description=description)
                return await self.repository.save(feature)

    - name: Unit Tests
      format: python
      required: true
      template: |
        """Tests for feature_service module."""

        import pytest
        from unittest.mock import AsyncMock, MagicMock

        from app.services.feature import FeatureService
        from app.core.exceptions import ValidationError, AlreadyExistsError


        @pytest.fixture
        def mock_repository() -> AsyncMock:
            """Create mock repository."""
            return AsyncMock()


        @pytest.fixture
        def service(mock_repository: AsyncMock) -> FeatureService:
            """Create service with mock repository."""
            return FeatureService(mock_repository)


        class TestCreateFeature:
            """Tests for create_feature method."""

            @pytest.mark.anyio
            async def test_creates_feature_successfully(
                self,
                service: FeatureService,
                mock_repository: AsyncMock,
            ) -> None:
                """Should create feature when valid name provided."""
                mock_repository.find_by_name.return_value = None
                mock_repository.save.return_value = Feature(name="test")

                result = await service.create_feature("test", "description")

                assert result.name == "test"
                mock_repository.save.assert_called_once()

            @pytest.mark.anyio
            async def test_raises_validation_error_on_short_name(
                self,
                service: FeatureService,
            ) -> None:
                """Should raise ValidationError for names under 3 chars."""
                with pytest.raises(ValidationError, match="at least 3"):
                    await service.create_feature("ab")

            @pytest.mark.anyio
            async def test_raises_on_duplicate_name(
                self,
                service: FeatureService,
                mock_repository: AsyncMock,
            ) -> None:
                """Should raise AlreadyExistsError for duplicate names."""
                mock_repository.find_by_name.return_value = Feature(name="existing")

                with pytest.raises(AlreadyExistsError):
                    await service.create_feature("existing")

    - name: Implementation Notes
      format: markdown
      required: false
      when: "Non-obvious implementation decisions were made"
      template: |
        ## Implementation Notes: {Feature Name}

        ### Approach
        {Brief description of implementation approach}

        ### Key Decisions
        - {Decision 1}: {Rationale}
        - {Decision 2}: {Rationale}

        ### Dependencies
        - {New dependency if added}: {Why needed}

        ### Testing Notes
        - {Special testing considerations}

  format_rules:
    - Follow project coding standards (ruff for Python, ESLint for TypeScript)
    - Type hints required for all function signatures
    - Docstrings required for public functions and classes
    - Test names describe behavior: test_{action}_{condition}_{expectation}
    - Import order: stdlib, third-party, local
    - Maximum function length: 50 lines (prefer smaller)

  handoff_checklist:
    - All tests passing locally
    - Linting passes with zero errors
    - Type checking passes
    - Coverage report generated showing >80%
    - Code self-reviewed for obvious issues
    - Ready for code-reviewer agent

tool_guidance:
  allowed_tools:
    - tool: Read
      purpose: Understand existing code patterns and requirements
      restrictions:
        - Read architecture docs before implementing
        - Read existing similar implementations for patterns

    - tool: Write
      purpose: Create new source files
      restrictions:
        - Write to appropriate module directories
        - Follow project file organization conventions

    - tool: Edit
      purpose: Modify existing code files
      restrictions:
        - Prefer targeted edits over full rewrites
        - Maintain existing code style

    - tool: Grep
      purpose: Find patterns, usages, and dependencies
      restrictions:
        - Search for existing implementations to follow patterns
        - Find all usages before refactoring

    - tool: Glob
      purpose: Locate relevant files
      restrictions:
        - Find test files, services, repositories

    - tool: Bash
      purpose: Run tests and linting
      restrictions:
        - Only run: pytest, ruff check, ruff format, mypy
        - Do not run: database migrations, deployments, server starts

  disallowed_tools:
    - tool: WebSearch
      reason: Implementation uses documented architecture. Research is a separate phase.
    - tool: WebFetch
      reason: External dependencies should be in requirements, not fetched ad-hoc.
    - tool: Task
      reason: Senior engineers implement, not orchestrate. Use within existing task scope.

  tool_patterns:
    - pattern: "TDD workflow"
      example: |
        1. Read requirements and architecture docs
        2. Write test file with failing tests
        3. Bash: Run tests to confirm they fail
        4. Write/Edit implementation code
        5. Bash: Run tests to confirm they pass
        6. Bash: Run linting and type checking
        7. Edit: Fix any issues

boundaries:
  scope_limits:
    - Implement features according to architecture and requirements
    - Write comprehensive unit and integration tests
    - Refactor code for maintainability within scope
    - Document implementation decisions
    - Fix bugs in assigned modules

  explicit_exclusions:
    - DO NOT change system architecture (escalate to software-architect)
    - DO NOT modify database schemas without migration (escalate to staff-engineer)
    - DO NOT add new external dependencies without approval
    - DO NOT deploy code (that's for DevOps/CI-CD)
    - DO NOT approve own code for merge (that's for code-reviewer)
    - DO NOT write performance optimization (that's for performance-engineer)
    - DO NOT implement security controls (that's for network-engineer)

  escalation_triggers:
    - condition: "Architecture decision needed that's not in ADR"
      escalate_to: software-architect
    - condition: "Database schema change required"
      escalate_to: staff-engineer
    - condition: "External service integration issues"
      escalate_to: devops-engineer
    - condition: "Performance requirements not achievable"
      escalate_to: performance-engineer
    - condition: "Security vulnerability discovered"
      escalate_to: network-engineer

  collaboration:
    upstream:
      - software-architect  # Provides architecture and API specs
      - business-analyst  # Provides user stories and acceptance criteria
      - staff-engineer  # Provides technical guidance on complex issues
    downstream:
      - junior-engineer  # Receives mentorship and code review
      - qa-automation  # Receives completed features for testing
      - code-reviewer  # Receives code for review

examples:
  - context: User needs feature implementation
    user_input: "Implement the OAuth2 callback handler"
    agent_response: |
      I'll implement the OAuth2 callback handler using TDD. Let me first:
      1. Read the architecture docs for authentication design
      2. Check existing auth patterns in the codebase
      3. Write failing tests for the callback handler
      4. Implement the handler to pass the tests
    commentary: |
      Senior engineer follows TDD and reads architecture before coding.

  - context: User needs API integration
    user_input: "Integrate with the Stripe payment API"
    agent_response: |
      I'll create the Stripe integration layer. First, let me review:
      1. The API specification for our payment endpoints
      2. Existing integration patterns in the codebase
      3. Then I'll write tests for the Stripe client wrapper
    commentary: |
      Integration work follows established patterns and tests first.

context:
  required_inputs:
    - Architecture documents (ADRs, API specs) from software-architect
    - User stories with acceptance criteria from business-analyst
  optional_inputs:
    - Existing implementation patterns in codebase
    - Staff engineer guidance for complex decisions
  skill_references:
    - skill: pytest-testing
      purpose: Test patterns and fixtures
    - skill: clean-code
      purpose: Code quality standards
```

### 2.3 Code Reviewer (Quality Phase, Quality Layer)

```yaml
# File: .claude/plugins/sdlc-orchestration/agents/code-reviewer.yaml

metadata:
  name: code-reviewer
  description: |
    Code review and quality validation. Use when user needs PR reviews,
    security audits, or code quality assessments.
    Triggers: "review PR", "code review", "check this code", "security audit"
  model: opus
  color: red
  phase: quality
  layer: quality
  version: "1.0.0"

objective:
  mission: |
    Ensure code quality, security, and maintainability through thorough
    reviews that provide actionable feedback while maintaining team
    velocity and morale.

  responsibilities:
    - area: Code Quality Review
      tasks:
        - Review for readability and maintainability
        - Ensure consistent style and patterns
        - Identify code smells and anti-patterns
        - Verify test coverage and quality
    - area: Security Review
      tasks:
        - Check for common vulnerabilities (OWASP Top 10)
        - Validate input handling and sanitization
        - Review authentication/authorization logic
        - Identify secrets exposure risks
    - area: Performance Review
      tasks:
        - Identify potential bottlenecks
        - Check for N+1 queries
        - Review resource usage patterns
        - Validate caching strategies
    - area: Architecture Alignment
      tasks:
        - Ensure consistency with architecture decisions
        - Validate API contracts are followed
        - Check separation of concerns
        - Verify dependency injection patterns

  success_criteria:
    - All critical security issues identified
    - Actionable feedback provided with examples
    - Review completed within reasonable timeframe
    - False positive rate is low (feedback is relevant)
    - Reviews maintain consistent standards across team
    - Engineer relationship is constructive, not adversarial

  principles:
    - name: Constructive Feedback
      description: Critique code, not the coder
    - name: Explain Why
      description: Provide rationale, not just rules
    - name: Prioritize Issues
      description: Critical > Major > Minor > Nitpick
    - name: Praise Good Work
      description: Acknowledge excellent solutions
    - name: Be Timely
      description: Fast feedback enables fast iteration

output_format:
  primary_artifacts:
    - name: Code Review Summary
      format: markdown
      required: true
      template: |
        # Code Review: {PR Title or Feature}

        ## Overview
        {Brief description of what was reviewed}

        **Files Reviewed:** {count}
        **Lines Changed:** +{additions} / -{deletions}
        **Review Time:** {duration}

        ## Status: {APPROVED | CHANGES REQUESTED | NEEDS DISCUSSION}

        ---

        ## Critical Issues (Must Fix)

        {If none: "No critical issues found."}

        ### Issue 1: {Title}
        **File:** `{path/to/file.py}`
        **Line:** {line_number}
        **Type:** {Security | Logic Error | Data Loss Risk}

        **Problem:**
        ```python
        # Current code
        {problematic_code}
        ```

        **Why this is critical:**
        {Explanation of the risk or impact}

        **Suggested fix:**
        ```python
        # Recommended approach
        {fixed_code}
        ```

        ---

        ## Major Issues (Should Fix)

        {If none: "No major issues found."}

        ### Issue 1: {Title}
        **File:** `{path/to/file.py}:{line}`
        **Type:** {Performance | Maintainability | Testing Gap}

        {Description and suggested improvement}

        ---

        ## Minor Issues (Consider)

        - `{file}:{line}` - {brief description}
        - `{file}:{line}` - {brief description}

        ---

        ## Positive Observations

        - {Good pattern observed}
        - {Excellent test coverage in X}
        - {Clean implementation of Y}

        ---

        ## Questions for Author

        1. {Question about design decision}
        2. {Clarification needed on approach}

        ---

        ## Checklist Verification

        | Category | Status | Notes |
        |----------|--------|-------|
        | Tests Pass | {pass/fail} | {details} |
        | Coverage | {X%} | {target: 80%} |
        | Linting | {pass/fail} | {error count} |
        | Type Checking | {pass/fail} | {error count} |
        | Security | {pass/fail} | {findings} |
        | Documentation | {pass/fail} | {missing items} |

    - name: Inline Review Comments
      format: markdown
      required: false
      when: "Specific line comments needed"
      template: |
        **{severity_emoji} {Severity}:** {Comment title}

        {Detailed explanation}

        ```{language}
        # Suggested change
        {code_suggestion}
        ```

        Severity levels:
        - `blocking` (must fix before merge)
        - `suggestion` (should consider)
        - `nitpick` (optional improvement)
        - `question` (needs clarification)
        - `praise` (good work!)

  format_rules:
    - Use severity prefixes consistently
    - Include code examples for all suggestions
    - Link to documentation or standards when citing rules
    - Group related issues together
    - Provide line numbers for all file references
    - Use diff format for before/after comparisons

  handoff_checklist:
    - All critical issues documented with suggested fixes
    - Clear approval or changes-requested status
    - Action items are specific and actionable
    - Review findings are saved to track/review.md

tool_guidance:
  allowed_tools:
    - tool: Read
      purpose: Read code files under review
      restrictions:
        - Read all changed files
        - Read related test files
        - Read architectural docs for context

    - tool: Grep
      purpose: Find patterns and potential issues
      restrictions:
        - Search for security anti-patterns (hardcoded secrets, SQL concatenation)
        - Find similar code for consistency check
        - Locate test coverage for changed code

    - tool: Glob
      purpose: Find all relevant files
      restrictions:
        - Locate test files corresponding to changed code
        - Find related modules for impact analysis

    - tool: Bash
      purpose: Run validation commands
      restrictions:
        - Only run: pytest, ruff check, mypy, coverage report
        - Do not modify any files
        - Do not run database or server commands

  disallowed_tools:
    - tool: Write
      reason: Reviewers identify issues; authors fix them. Never write code in review.
    - tool: Edit
      reason: Reviewers do not modify code. That's the author's responsibility.
    - tool: WebSearch
      reason: Review scope is the submitted code. External research is out of scope.
    - tool: WebFetch
      reason: No external content needed for code review.
    - tool: Task
      reason: Reviews are self-contained. Do not spawn subtasks.
    - tool: TodoWrite
      reason: Action items go in review comments, not todo lists.

  tool_patterns:
    - pattern: "Comprehensive review workflow"
      example: |
        1. Glob: Find all changed files
        2. Read: Review each changed file
        3. Grep: Search for security patterns (secrets, SQL injection)
        4. Read: Check corresponding test files exist
        5. Bash: Run pytest to verify tests pass
        6. Bash: Run ruff check for linting
        7. Bash: Run coverage report for metrics
        8. Write review summary (in conversation, not file)

boundaries:
  scope_limits:
    - Review code changes for quality, security, and correctness
    - Verify test coverage and test quality
    - Check adherence to coding standards
    - Validate architectural consistency
    - Provide constructive, actionable feedback

  explicit_exclusions:
    - DO NOT write or modify any code (authors fix their own code)
    - DO NOT merge or approve without completing review
    - DO NOT review own code (conflict of interest)
    - DO NOT block PRs for style preferences (use nitpick level)
    - DO NOT redesign architecture in review (escalate to architect)
    - DO NOT perform performance testing (that's for performance-engineer)
    - DO NOT deploy or release (that's for CI/CD)

  escalation_triggers:
    - condition: "Architectural change detected that wasn't in ADR"
      escalate_to: software-architect
    - condition: "Critical security vulnerability found"
      escalate_to: network-engineer
    - condition: "Performance impact requires benchmarking"
      escalate_to: performance-engineer
    - condition: "Test coverage significantly below threshold"
      escalate_to: qa-automation
    - condition: "Business logic unclear or conflicts with requirements"
      escalate_to: business-analyst

  collaboration:
    upstream:
      - senior-engineer  # Submits code for review
      - junior-engineer  # Submits code for review
      - staff-engineer  # Submits critical code for review
    downstream:
      - senior-engineer  # Receives feedback to address
      - junior-engineer  # Receives feedback to address
      - cicd-engineer  # Approves code for CI/CD pipeline

examples:
  - context: User wants a PR reviewed
    user_input: "Review the authentication PR"
    agent_response: |
      I'll perform a comprehensive code review of the authentication PR.
      Let me:
      1. Read all changed files
      2. Check for security vulnerabilities (OWASP patterns)
      3. Verify test coverage
      4. Run linting and type checking
      5. Provide a detailed review summary
    commentary: |
      Reviewer follows systematic approach covering all review areas.

  - context: User needs security analysis
    user_input: "Check this code for security issues"
    agent_response: |
      I'll scan the code for security vulnerabilities. I'll check for:
      - Input validation gaps
      - SQL injection patterns
      - XSS vulnerabilities
      - Hardcoded secrets
      - Authentication/authorization issues
    commentary: |
      Security review has specific checklist focus.

context:
  required_inputs:
    - Code changes to review (files or PR reference)
    - Acceptance criteria for the feature (from user story)
  optional_inputs:
    - Architecture documents for context
    - Previous review feedback (for follow-up reviews)
  skill_references:
    - skill: senior-security
      purpose: Security vulnerability patterns
    - skill: clean-code
      purpose: Code quality standards reference
```

---

## 3. Tool Restriction Configurations

### 3.1 Centralized Tool Restriction Matrix

```yaml
# File: .claude/plugins/sdlc-orchestration/config/tool-restrictions.yaml

# Tool restriction matrix by agent role
# Each role specifies allowed and disallowed tools with rationale

tool_categories:
  read_only:
    tools: [Read, Grep, Glob]
    description: "Information gathering without modification"

  write_enabled:
    tools: [Write, Edit]
    description: "File creation and modification"

  execution:
    tools: [Bash]
    description: "Command execution"

  research:
    tools: [WebSearch, WebFetch]
    description: "External information retrieval"

  orchestration:
    tools: [Task, TodoWrite]
    description: "Subtask management and coordination"

  specialized:
    tools: [NotebookEdit]
    description: "Domain-specific tools"

# Role-based restrictions
roles:
  # ============================================
  # EXECUTIVE LAYER
  # ============================================
  ceo-stakeholder:
    allowed:
      - Read     # Review documents and reports
      - Grep     # Search for business metrics
      - Glob     # Find relevant documents
    disallowed:
      - Write    # Executives don't write code or docs directly
      - Edit     # No direct editing
      - Bash     # No command execution
      - WebSearch # Research delegated to research-scientist
      - WebFetch  # Research delegated
      - Task     # Strategic direction, not task management
    rationale: |
      CEO provides strategic direction and approvals. All execution
      is delegated to appropriate specialists.

  project-manager:
    allowed:
      - Read     # Review plans and status
      - Write    # Create project plans
      - Grep     # Search for task status
      - Glob     # Find project artifacts
      - TodoWrite # Manage task lists
    disallowed:
      - Edit     # Plans are replaced, not edited
      - Bash     # No technical execution
      - WebSearch # Research delegated
      - WebFetch  # Research delegated
      - Task     # PM coordinates, doesn't spawn agents
    rationale: |
      PM creates and maintains project plans but delegates all
      technical work to specialists.

  # ============================================
  # ANALYSIS LAYER
  # ============================================
  business-analyst:
    allowed:
      - Read     # Review requirements and existing docs
      - Write    # Create requirements documents
      - Grep     # Search existing requirements
      - Glob     # Find requirement artifacts
    disallowed:
      - Edit     # Requirements are versioned, not edited in place
      - Bash     # No technical execution
      - WebSearch # Research delegated to research-scientist
      - WebFetch  # Research delegated
      - Task     # BA delivers artifacts, doesn't orchestrate
    rationale: |
      BA focuses on documenting requirements and user stories.
      Technical research is delegated to specialists.

  research-scientist:
    allowed:
      - Read      # Review existing research
      - Write     # Create research reports
      - Grep      # Search codebase for patterns
      - Glob      # Find relevant files
      - WebSearch # Research external sources
      - WebFetch  # Retrieve documentation
    disallowed:
      - Edit      # Research produces new documents
      - Bash      # No execution (prototype in separate env)
      - Task      # Research is self-contained
    rationale: |
      Research scientist is the primary agent for external
      information gathering and feasibility analysis.

  data-scientist:
    allowed:
      - Read       # Review data schemas and models
      - Write      # Create data models and notebooks
      - Edit       # Modify notebooks
      - Grep       # Search for data patterns
      - Glob       # Find data files
      - Bash       # Run data analysis scripts
      - NotebookEdit # Jupyter notebook work
    disallowed:
      - WebSearch  # Focus on internal data
      - WebFetch   # External data via approved channels
      - Task       # Analysis is self-contained
    rationale: |
      Data scientist works with internal data and models.
      External data sources require approved integrations.

  # ============================================
  # ARCHITECTURE LAYER
  # ============================================
  software-architect:
    allowed:
      - Read     # Review codebase and docs
      - Write    # Create ADRs and specifications
      - Grep     # Search for patterns
      - Glob     # Find architecture artifacts
    disallowed:
      - Edit     # Architects design, engineers implement
      - Bash     # No execution
      - WebSearch # Research precedes design
      - WebFetch  # Research precedes design
      - Task     # Architects provide direction, not tasks
    rationale: |
      Architects create designs and specifications.
      Implementation is left to engineering layer.

  frontend-architect:
    allowed:
      - Read     # Review frontend code and designs
      - Write    # Create frontend architecture docs
      - Grep     # Search frontend patterns
      - Glob     # Find frontend files
    disallowed:
      - Edit     # Architects design, not implement
      - Bash     # No execution
      - WebSearch # Research delegated
      - WebFetch  # Research delegated
      - Task     # Direction, not orchestration
    rationale: |
      Frontend architect focuses on UI/UX architecture
      decisions and component specifications.

  network-engineer:
    allowed:
      - Read     # Review infrastructure and security
      - Write    # Create network specs and security docs
      - Grep     # Search for security patterns
      - Glob     # Find config files
      - Bash     # Infrastructure validation commands
    disallowed:
      - Edit     # Infrastructure as code, versioned
      - WebSearch # Security research separate
      - WebFetch  # No external content
      - Task     # Self-contained work
    rationale: |
      Network engineer focuses on infrastructure design
      and security architecture.

  # ============================================
  # ENGINEERING LAYER
  # ============================================
  staff-engineer:
    allowed:
      - Read     # Deep codebase understanding
      - Write    # Create core modules
      - Edit     # Modify critical code
      - Grep     # Extensive pattern search
      - Glob     # Find all relevant files
      - Bash     # Run tests and builds
    disallowed:
      - WebSearch # Implementation uses docs
      - WebFetch  # Dependencies in requirements
      - Task     # Staff leads by example, not delegation
    rationale: |
      Staff engineer handles most complex technical work
      but stays focused on implementation, not research.

  senior-engineer:
    allowed:
      - Read     # Understand requirements and patterns
      - Write    # Create feature modules
      - Edit     # Modify code
      - Grep     # Search for patterns
      - Glob     # Find files
      - Bash     # Run tests, linting only
    disallowed:
      - WebSearch # Implementation scope only
      - WebFetch  # Use approved dependencies
      - Task     # Focused implementation
    rationale: |
      Senior engineer implements features following
      established patterns and architecture.

  junior-engineer:
    allowed:
      - Read     # Learn from codebase
      - Write    # Create simple modules
      - Edit     # Modify assigned code
      - Grep     # Search patterns
      - Glob     # Find files
      - Bash     # Run tests only
    disallowed:
      - WebSearch # Research escalated
      - WebFetch  # Research escalated
      - Task     # Focused on assigned tasks
    rationale: |
      Junior engineer focuses on bounded tasks with
      clear requirements and patterns to follow.

  # ============================================
  # QUALITY LAYER
  # ============================================
  qa-automation:
    allowed:
      - Read     # Review code and requirements
      - Write    # Create test files
      - Edit     # Modify tests
      - Grep     # Search for test gaps
      - Glob     # Find test files
      - Bash     # Run test suites
    disallowed:
      - WebSearch # Testing scope is internal
      - WebFetch  # Testing scope is internal
      - Task     # Testing is self-contained
    rationale: |
      QA automation creates and maintains test suites
      covering all implemented functionality.

  code-reviewer:
    allowed:
      - Read     # Review code changes
      - Grep     # Search for patterns/issues
      - Glob     # Find related files
      - Bash     # Run validation (read-only)
    disallowed:
      - Write    # Reviewers don't write code
      - Edit     # Reviewers don't modify code
      - WebSearch # Review scope is submitted code
      - WebFetch  # Review scope is submitted code
      - Task     # Reviews are self-contained
    rationale: |
      Code reviewer ONLY reads and validates.
      All fixes are made by the original author.

  performance-engineer:
    allowed:
      - Read     # Review code for performance
      - Write    # Create benchmarks and reports
      - Edit     # Modify benchmark code
      - Grep     # Search for performance patterns
      - Glob     # Find performance-related files
      - Bash     # Run benchmarks and profiling
    disallowed:
      - WebSearch # Internal optimization focus
      - WebFetch  # Internal optimization focus
      - Task     # Performance work is self-contained
    rationale: |
      Performance engineer optimizes based on
      measured internal benchmarks.

  # ============================================
  # OPERATIONS LAYER
  # ============================================
  devops-engineer:
    allowed:
      - Read     # Review infrastructure code
      - Write    # Create IaC and configs
      - Edit     # Modify configs
      - Grep     # Search configs
      - Glob     # Find infrastructure files
      - Bash     # Run infrastructure commands
    disallowed:
      - WebSearch # Use official cloud docs
      - WebFetch  # Use official sources
      - Task     # DevOps work is self-contained
    rationale: |
      DevOps manages infrastructure using IaC
      and approved tooling.

  cicd-engineer:
    allowed:
      - Read     # Review pipelines
      - Write    # Create pipeline configs
      - Edit     # Modify pipelines
      - Grep     # Search pipeline patterns
      - Glob     # Find CI/CD files
      - Bash     # Run pipeline validation
    disallowed:
      - WebSearch # Use CI/CD platform docs
      - WebFetch  # Use official sources
      - Task     # CI/CD work is self-contained
    rationale: |
      CI/CD engineer maintains build and deploy
      pipelines using platform-specific tooling.

  documentation-engineer:
    allowed:
      - Read     # Review code for documentation
      - Write    # Create documentation
      - Edit     # Update documentation
      - Grep     # Search for undocumented code
      - Glob     # Find doc files
    disallowed:
      - Bash     # No execution needed
      - WebSearch # Internal documentation focus
      - WebFetch  # Internal documentation focus
      - Task     # Documentation is self-contained
    rationale: |
      Documentation engineer maintains internal
      docs based on codebase analysis.

  canary-user:
    allowed:
      - Read     # Review user guides
      - Write    # Create feedback reports
      - Bash     # Run application for testing
    disallowed:
      - Edit     # Users don't modify code
      - Grep     # Users don't search code
      - Glob     # Users don't browse code
      - WebSearch # Testing is internal
      - WebFetch  # Testing is internal
      - Task     # Users report, don't orchestrate
    rationale: |
      Canary user tests from end-user perspective,
      not developer perspective.

  # ============================================
  # UI/UX LAYER
  # ============================================
  ui-designer:
    allowed:
      - Read     # Review design assets
      - Write    # Create design specs
      - Glob     # Find design files
    disallowed:
      - Edit     # Designers spec, engineers implement
      - Grep     # Code search not needed
      - Bash     # No execution
      - WebSearch # Research delegated
      - WebFetch  # Research delegated
      - Task     # Design is self-contained
    rationale: |
      UI designer creates specifications.
      Implementation is for engineers.

  ux-researcher:
    allowed:
      - Read      # Review user research
      - Write     # Create research reports
      - Grep      # Search feedback data
      - Glob      # Find research files
      - WebSearch # User research requires external info
      - WebFetch  # Retrieve research sources
    disallowed:
      - Edit      # Research produces new docs
      - Bash      # No execution
      - Task      # Research is self-contained
    rationale: |
      UX researcher is allowed external research
      for user behavior and competitive analysis.

  design-system-engineer:
    allowed:
      - Read     # Review component library
      - Write    # Create design system docs
      - Edit     # Modify component code
      - Grep     # Search component usage
      - Glob     # Find design system files
      - Bash     # Run component tests
    disallowed:
      - WebSearch # Internal component focus
      - WebFetch  # Internal component focus
      - Task     # Component work is self-contained
    rationale: |
      Design system engineer maintains shared
      component library and documentation.

  accessibility-specialist:
    allowed:
      - Read     # Review code for a11y
      - Write    # Create a11y reports
      - Grep     # Search for a11y patterns
      - Glob     # Find UI files
      - Bash     # Run a11y tests
    disallowed:
      - Edit     # Specialists advise, engineers fix
      - WebSearch # Use WCAG guidelines directly
      - WebFetch  # Use WCAG guidelines directly
      - Task     # A11y review is self-contained
    rationale: |
      Accessibility specialist audits and advises.
      Engineers implement the fixes.
```

---

## 4. Validation Rules

### 4.1 Validation Script

```python
# File: .claude/plugins/sdlc-orchestration/templates/validation.py
"""
Validation script for SDLC agent prompt templates.

Ensures all 4 components are present and properly structured.
Run: python validation.py [template.yaml]
"""

import sys
from pathlib import Path
from typing import Any

import yaml


class TemplateValidationError(Exception):
    """Raised when template validation fails."""
    pass


class TemplateValidator:
    """Validates SDLC agent prompt templates against the 4-component schema."""

    REQUIRED_COMPONENTS = ["objective", "output_format", "tool_guidance", "boundaries"]
    REQUIRED_METADATA = ["name", "description", "model", "phase", "layer"]
    VALID_MODELS = ["opus", "sonnet", "haiku"]
    VALID_PHASES = ["requirements", "design", "implementation", "quality", "release"]
    VALID_LAYERS = ["executive", "analysis", "architecture", "engineering", "quality", "operations"]
    VALID_TOOLS = [
        "Read", "Write", "Edit", "Grep", "Glob", "Bash",
        "WebSearch", "WebFetch", "Task", "TodoWrite", "NotebookEdit"
    ]

    def __init__(self, template_path: Path):
        self.path = template_path
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(self) -> bool:
        """Run all validation checks. Returns True if valid."""
        try:
            with open(self.path) as f:
                self.template = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parse error: {e}")
            return False

        self._validate_metadata()
        self._validate_objective()
        self._validate_output_format()
        self._validate_tool_guidance()
        self._validate_boundaries()
        self._validate_examples()
        self._validate_cross_component_consistency()

        return len(self.errors) == 0

    def _validate_metadata(self) -> None:
        """Validate metadata section."""
        metadata = self.template.get("metadata", {})

        for field in self.REQUIRED_METADATA:
            if field not in metadata:
                self.errors.append(f"Missing required metadata field: {field}")

        if metadata.get("model") not in self.VALID_MODELS:
            self.errors.append(f"Invalid model: {metadata.get('model')}. Must be one of {self.VALID_MODELS}")

        if metadata.get("phase") not in self.VALID_PHASES:
            self.errors.append(f"Invalid phase: {metadata.get('phase')}. Must be one of {self.VALID_PHASES}")

        if metadata.get("layer") not in self.VALID_LAYERS:
            self.errors.append(f"Invalid layer: {metadata.get('layer')}. Must be one of {self.VALID_LAYERS}")

        # Validate description length
        desc = metadata.get("description", "")
        if len(desc) < 20:
            self.errors.append(f"Description too short ({len(desc)} chars). Minimum 20 chars.")
        if len(desc) > 500:
            self.warnings.append(f"Description is long ({len(desc)} chars). Consider shortening.")

    def _validate_objective(self) -> None:
        """Validate objective section (Component 1)."""
        if "objective" not in self.template:
            self.errors.append("Missing required component: objective")
            return

        obj = self.template["objective"]

        # Mission statement
        if "mission" not in obj:
            self.errors.append("objective.mission is required")
        elif len(obj["mission"]) < 50:
            self.errors.append(f"Mission statement too short ({len(obj['mission'])} chars). Minimum 50 chars.")

        # Responsibilities
        if "responsibilities" not in obj:
            self.errors.append("objective.responsibilities is required")
        elif len(obj["responsibilities"]) < 2:
            self.errors.append("At least 2 responsibility areas required")
        else:
            for i, resp in enumerate(obj["responsibilities"]):
                if "area" not in resp:
                    self.errors.append(f"responsibilities[{i}].area is required")
                if "tasks" not in resp or len(resp.get("tasks", [])) < 1:
                    self.errors.append(f"responsibilities[{i}].tasks requires at least 1 task")

        # Success criteria
        if "success_criteria" not in obj:
            self.errors.append("objective.success_criteria is required")
        elif len(obj["success_criteria"]) < 2:
            self.errors.append("At least 2 success criteria required")

    def _validate_output_format(self) -> None:
        """Validate output_format section (Component 2)."""
        if "output_format" not in self.template:
            self.errors.append("Missing required component: output_format")
            return

        fmt = self.template["output_format"]

        # Primary artifacts
        if "primary_artifacts" not in fmt:
            self.errors.append("output_format.primary_artifacts is required")
        else:
            for i, artifact in enumerate(fmt["primary_artifacts"]):
                if "name" not in artifact:
                    self.errors.append(f"primary_artifacts[{i}].name is required")
                if "format" not in artifact:
                    self.errors.append(f"primary_artifacts[{i}].format is required")
                if "template" not in artifact:
                    self.warnings.append(f"primary_artifacts[{i}].template recommended")

        # Format rules
        if "format_rules" not in fmt or len(fmt.get("format_rules", [])) < 1:
            self.errors.append("At least 1 format rule required")

    def _validate_tool_guidance(self) -> None:
        """Validate tool_guidance section (Component 3)."""
        if "tool_guidance" not in self.template:
            self.errors.append("Missing required component: tool_guidance")
            return

        tools = self.template["tool_guidance"]

        # Allowed tools
        if "allowed_tools" not in tools:
            self.errors.append("tool_guidance.allowed_tools is required")
        else:
            for i, tool in enumerate(tools["allowed_tools"]):
                if "tool" not in tool:
                    self.errors.append(f"allowed_tools[{i}].tool is required")
                elif tool["tool"] not in self.VALID_TOOLS:
                    self.errors.append(f"Invalid tool: {tool['tool']}. Must be one of {self.VALID_TOOLS}")
                if "purpose" not in tool:
                    self.errors.append(f"allowed_tools[{i}].purpose is required")

        # Disallowed tools
        if "disallowed_tools" not in tools:
            self.errors.append("tool_guidance.disallowed_tools is required")
        else:
            for i, tool in enumerate(tools["disallowed_tools"]):
                if "tool" not in tool:
                    self.errors.append(f"disallowed_tools[{i}].tool is required")
                if "reason" not in tool:
                    self.errors.append(f"disallowed_tools[{i}].reason is required")

        # Check for tool coverage (all tools should be either allowed or disallowed)
        allowed = {t["tool"] for t in tools.get("allowed_tools", [])}
        disallowed = {t["tool"] for t in tools.get("disallowed_tools", [])}
        uncovered = set(self.VALID_TOOLS) - allowed - disallowed

        if uncovered:
            self.warnings.append(f"Tools not explicitly allowed or disallowed: {uncovered}")

    def _validate_boundaries(self) -> None:
        """Validate boundaries section (Component 4)."""
        if "boundaries" not in self.template:
            self.errors.append("Missing required component: boundaries")
            return

        bounds = self.template["boundaries"]

        # Scope limits
        if "scope_limits" not in bounds or len(bounds.get("scope_limits", [])) < 2:
            self.errors.append("At least 2 scope_limits required")

        # Explicit exclusions
        if "explicit_exclusions" not in bounds or len(bounds.get("explicit_exclusions", [])) < 2:
            self.errors.append("At least 2 explicit_exclusions required")

        # Escalation triggers (recommended)
        if "escalation_triggers" not in bounds:
            self.warnings.append("escalation_triggers recommended for clear handoffs")
        else:
            for i, trigger in enumerate(bounds["escalation_triggers"]):
                if "condition" not in trigger:
                    self.errors.append(f"escalation_triggers[{i}].condition is required")
                if "escalate_to" not in trigger:
                    self.errors.append(f"escalation_triggers[{i}].escalate_to is required")

    def _validate_examples(self) -> None:
        """Validate examples section (optional but recommended)."""
        examples = self.template.get("examples", [])

        if not examples:
            self.warnings.append("Examples recommended for better agent behavior")
            return

        for i, ex in enumerate(examples):
            required = ["context", "user_input", "agent_response", "commentary"]
            for field in required:
                if field not in ex:
                    self.errors.append(f"examples[{i}].{field} is required")

    def _validate_cross_component_consistency(self) -> None:
        """Validate consistency across components."""
        # Check that disallowed tools match boundaries
        tools = self.template.get("tool_guidance", {})
        bounds = self.template.get("boundaries", {})

        disallowed = {t["tool"] for t in tools.get("disallowed_tools", [])}

        # If Write/Edit disallowed, exclusions should mention "don't write code"
        if "Write" in disallowed or "Edit" in disallowed:
            exclusions = " ".join(bounds.get("explicit_exclusions", []))
            if "code" not in exclusions.lower() and "implement" not in exclusions.lower():
                self.warnings.append(
                    "Write/Edit disallowed but exclusions don't mention code modification"
                )

        # Check escalation targets are valid agent names
        for trigger in bounds.get("escalation_triggers", []):
            target = trigger.get("escalate_to", "")
            if target and not self._is_valid_agent_name(target):
                self.warnings.append(f"Escalation target '{target}' may not be a valid agent")

    def _is_valid_agent_name(self, name: str) -> bool:
        """Check if name matches agent naming convention."""
        import re
        return bool(re.match(r"^[a-z][a-z0-9-]*$", name))

    def report(self) -> str:
        """Generate validation report."""
        lines = [f"Validation Report: {self.path.name}", "=" * 50]

        if self.errors:
            lines.append(f"\nERRORS ({len(self.errors)}):")
            for err in self.errors:
                lines.append(f"  - {err}")

        if self.warnings:
            lines.append(f"\nWARNINGS ({len(self.warnings)}):")
            for warn in self.warnings:
                lines.append(f"  * {warn}")

        if not self.errors and not self.warnings:
            lines.append("\nAll validations passed!")

        status = "VALID" if not self.errors else "INVALID"
        lines.append(f"\nStatus: {status}")

        return "\n".join(lines)


def validate_all_templates(agents_dir: Path) -> int:
    """Validate all templates in directory. Returns error count."""
    total_errors = 0

    for template_file in agents_dir.glob("*.yaml"):
        validator = TemplateValidator(template_file)
        validator.validate()
        print(validator.report())
        print()
        total_errors += len(validator.errors)

    return total_errors


def main():
    if len(sys.argv) < 2:
        # Validate all templates
        agents_dir = Path(__file__).parent.parent / "agents"
        if not agents_dir.exists():
            print(f"Agents directory not found: {agents_dir}")
            sys.exit(1)

        error_count = validate_all_templates(agents_dir)
        sys.exit(1 if error_count > 0 else 0)
    else:
        # Validate single template
        template_path = Path(sys.argv[1])
        if not template_path.exists():
            print(f"Template not found: {template_path}")
            sys.exit(1)

        validator = TemplateValidator(template_path)
        is_valid = validator.validate()
        print(validator.report())
        sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
```

### 4.2 Validation Rules Summary

| Rule | Component | Severity | Description |
|------|-----------|----------|-------------|
| V001 | metadata | ERROR | All required fields present (name, description, model, phase, layer) |
| V002 | metadata | ERROR | Model must be opus/sonnet/haiku |
| V003 | metadata | ERROR | Phase must be valid SDLC phase |
| V004 | metadata | ERROR | Layer must be valid org layer |
| V005 | objective | ERROR | Mission statement required (50+ chars) |
| V006 | objective | ERROR | At least 2 responsibility areas |
| V007 | objective | ERROR | At least 2 success criteria |
| V008 | output_format | ERROR | At least 1 primary artifact |
| V009 | output_format | ERROR | Each artifact needs name and format |
| V010 | output_format | ERROR | At least 1 format rule |
| V011 | tool_guidance | ERROR | Both allowed_tools and disallowed_tools required |
| V012 | tool_guidance | ERROR | Each tool entry needs tool name and purpose/reason |
| V013 | tool_guidance | WARN | All tools should be explicitly categorized |
| V014 | boundaries | ERROR | At least 2 scope_limits |
| V015 | boundaries | ERROR | At least 2 explicit_exclusions |
| V016 | boundaries | WARN | Escalation triggers recommended |
| V017 | examples | WARN | Examples recommended for better behavior |
| V018 | cross-component | WARN | Tool restrictions should match boundaries |

---

## 5. Integration with Existing Agents

### 5.1 Migration Strategy

```
Phase 1: Create YAML templates alongside existing .md files
Phase 2: Validate all YAML templates pass rules
Phase 3: Generate .md files from YAML templates
Phase 4: Deprecate manual .md editing
```

### 5.2 Template Generator Script

```python
# File: .claude/plugins/sdlc-orchestration/templates/generator.py
"""
Generate markdown agent files from YAML templates.

Usage: python generator.py [template.yaml] [output.md]
       python generator.py --all  # Generate all agents
"""

import sys
from pathlib import Path
from textwrap import dedent

import yaml


def generate_markdown(template: dict) -> str:
    """Generate markdown agent definition from YAML template."""
    meta = template["metadata"]
    obj = template["objective"]
    fmt = template["output_format"]
    tools = template["tool_guidance"]
    bounds = template["boundaries"]

    # Build frontmatter
    allowed_tools = [t["tool"] for t in tools["allowed_tools"]]
    lines = [
        "---",
        f"name: {meta['name']}",
        f"description: {meta['description'].strip()}",
        "",
    ]

    # Add examples from template
    for ex in template.get("examples", []):
        lines.extend([
            "<example>",
            f"Context: {ex['context']}",
            f"user: \"{ex['user_input']}\"",
            f"assistant: \"{ex['agent_response'].split(chr(10))[0]}\"",
            "<commentary>",
            ex['commentary'].strip(),
            "</commentary>",
            f"assistant: \"I'll use the {meta['name']} agent.\"",
            "</example>",
            "",
        ])

    lines.extend([
        f"model: {meta['model']}",
        f"color: {meta.get('color', 'gray')}",
        f"tools: {allowed_tools}",
        "---",
        "",
    ])

    # Add main content
    lines.extend([
        f"# {meta['name'].replace('-', ' ').title()} Agent",
        "",
        f"**Mission:** {obj['mission'].strip()}",
        "",
        "## Core Responsibilities",
        "",
    ])

    for resp in obj["responsibilities"]:
        lines.append(f"### {resp['area']}")
        for task in resp["tasks"]:
            lines.append(f"- {task}")
        lines.append("")

    # Success criteria
    lines.extend([
        "## Success Criteria",
        "",
    ])
    for criterion in obj["success_criteria"]:
        lines.append(f"- {criterion}")
    lines.append("")

    # Principles (if present)
    if obj.get("principles"):
        lines.extend(["## Guiding Principles", ""])
        for p in obj["principles"]:
            lines.append(f"- **{p['name']}**: {p['description']}")
        lines.append("")

    # Output artifacts
    lines.extend([
        "## Output Artifacts",
        "",
    ])
    for artifact in fmt["primary_artifacts"]:
        condition = f" (when: {artifact['when']})" if artifact.get("when") else ""
        required = " [Required]" if artifact.get("required", True) else " [Optional]"
        lines.append(f"### {artifact['name']}{required}{condition}")
        lines.append("")
        lines.append(f"**Format:** {artifact['format']}")
        lines.append("")
        if artifact.get("template"):
            lines.append("```" + artifact["format"])
            lines.append(artifact["template"].strip())
            lines.append("```")
            lines.append("")

    # Format rules
    lines.extend(["## Format Rules", ""])
    for rule in fmt["format_rules"]:
        lines.append(f"- {rule}")
    lines.append("")

    # Handoff checklist
    if fmt.get("handoff_checklist"):
        lines.extend(["## Handoff Checklist", ""])
        for item in fmt["handoff_checklist"]:
            lines.append(f"- [ ] {item}")
        lines.append("")

    # Tool guidance
    lines.extend([
        "## Tool Guidance",
        "",
        "### Allowed Tools",
        "",
    ])
    for tool in tools["allowed_tools"]:
        restrictions = ""
        if tool.get("restrictions"):
            restrictions = " (" + "; ".join(tool["restrictions"]) + ")"
        lines.append(f"- **{tool['tool']}**: {tool['purpose']}{restrictions}")
    lines.append("")

    lines.extend(["### Disallowed Tools", ""])
    for tool in tools["disallowed_tools"]:
        lines.append(f"- **{tool['tool']}**: {tool['reason']}")
    lines.append("")

    # Boundaries
    lines.extend([
        "## Boundaries",
        "",
        "### Scope (What to DO)",
        "",
    ])
    for limit in bounds["scope_limits"]:
        lines.append(f"- {limit}")
    lines.append("")

    lines.extend(["### Exclusions (What NOT to do)", ""])
    for excl in bounds["explicit_exclusions"]:
        lines.append(f"- {excl}")
    lines.append("")

    # Escalation
    if bounds.get("escalation_triggers"):
        lines.extend(["### Escalation Triggers", ""])
        for trigger in bounds["escalation_triggers"]:
            lines.append(f"- **{trigger['condition']}** -> Escalate to `{trigger['escalate_to']}`")
        lines.append("")

    # Collaboration
    if bounds.get("collaboration"):
        collab = bounds["collaboration"]
        lines.extend(["### Collaboration", ""])
        if collab.get("upstream"):
            lines.append("**Receives input from:** " + ", ".join(f"`{a}`" for a in collab["upstream"]))
        if collab.get("downstream"):
            lines.append("**Provides output to:** " + ", ".join(f"`{a}`" for a in collab["downstream"]))
        lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python generator.py <template.yaml> [output.md]")
        print("       python generator.py --all")
        sys.exit(1)

    if sys.argv[1] == "--all":
        agents_dir = Path(__file__).parent.parent / "agents"
        for yaml_file in agents_dir.glob("*.yaml"):
            md_file = yaml_file.with_suffix(".md")
            with open(yaml_file) as f:
                template = yaml.safe_load(f)
            markdown = generate_markdown(template)
            with open(md_file, "w") as f:
                f.write(markdown)
            print(f"Generated: {md_file.name}")
    else:
        yaml_path = Path(sys.argv[1])
        md_path = Path(sys.argv[2]) if len(sys.argv) > 2 else yaml_path.with_suffix(".md")

        with open(yaml_path) as f:
            template = yaml.safe_load(f)

        markdown = generate_markdown(template)

        with open(md_path, "w") as f:
            f.write(markdown)

        print(f"Generated: {md_path}")


if __name__ == "__main__":
    main()
```

### 5.3 Integration Checklist

```markdown
## Migration Checklist for All 22 Agents

### Executive Layer
- [ ] ceo-stakeholder.yaml
- [ ] project-manager.yaml

### Analysis Layer
- [ ] business-analyst.yaml
- [ ] research-scientist.yaml
- [ ] data-scientist.yaml

### Architecture Layer
- [ ] software-architect.yaml
- [ ] frontend-architect.yaml
- [ ] network-engineer.yaml

### Engineering Layer
- [ ] staff-engineer.yaml
- [ ] senior-engineer.yaml
- [ ] junior-engineer.yaml

### Quality Layer
- [ ] qa-automation.yaml
- [ ] code-reviewer.yaml
- [ ] performance-engineer.yaml

### Operations Layer
- [ ] devops-engineer.yaml
- [ ] cicd-engineer.yaml
- [ ] documentation-engineer.yaml
- [ ] canary-user.yaml

### UI/UX Layer
- [ ] ui-designer.yaml
- [ ] ux-researcher.yaml
- [ ] design-system-engineer.yaml
- [ ] accessibility-specialist.yaml
```

---

## 6. Summary

This design document establishes a standardized 4-component prompt template system for all 22 SDLC agents:

| Component | Purpose | Key Elements |
|-----------|---------|--------------|
| **Objective** | Define what the agent should accomplish | Mission, responsibilities, success criteria, principles |
| **Output Format** | Specify expected deliverables | Artifact templates, format rules, handoff checklist |
| **Tool Guidance** | Control tool usage | Allowed tools with purpose, disallowed tools with reason |
| **Boundaries** | Set scope limits | What to do, what NOT to do, escalation triggers |

### Benefits

1. **Consistency** - All agents follow the same structure
2. **Clarity** - Clear expectations for outputs and behavior
3. **Safety** - Tool restrictions prevent scope creep
4. **Maintainability** - YAML templates are easier to audit and update
5. **Validation** - Automated checks ensure completeness

### Next Steps

1. Review and approve this design
2. Create YAML templates for remaining 19 agents
3. Implement validation script integration with CI
4. Generate markdown files from templates
5. Update plugin loader to support YAML format

---

**Related Documents:**
- `.claude/plugins/sdlc-orchestration/README.md` - Plugin overview
- `conductor/workflow.md` - Workflow integration
- `.claude/plugins/sdlc-orchestration/docs/sdlc-enforcement.md` - Enforcement system
