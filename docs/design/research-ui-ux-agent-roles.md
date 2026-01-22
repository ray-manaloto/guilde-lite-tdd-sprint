# Research Report: UI/UX Roles for AI Agentic Parallel Software Development Teams

## Executive Summary

This research report analyzes modern best practices for adding UI/UX specialized roles to an AI agentic software development team. Based on research from Anthropic's agent patterns, industry trends in 2026, and analysis of the existing SDLC orchestration system, we recommend adding **5 new UI/UX-focused agents** that integrate across the SDLC phases with specific focus on user-centered design principles.

**Key Findings:**
- Multi-agent systems are experiencing explosive growth (1,445% surge in inquiries per Gartner)
- UI/UX agents should operate across multiple SDLC phases, not just Design
- Context engineering is critical for agent coordination - use orchestrator-worker pattern
- Accessibility must be a first-class concern, not an afterthought
- Design systems automation can reduce development time from months to minutes

## Research Question

What UI/UX roles should be added to an AI agent team, which SDLC phases should they operate in, and how should they coordinate using context engineering best practices?

## Methodology

1. Analyzed Anthropic's official agent architecture documentation
2. Reviewed claude-cookbooks orchestrator-workers pattern implementation
3. Researched 2026 industry trends in AI UX design and agentic development
4. Examined existing SDLC orchestration plugin structure
5. Evaluated context engineering best practices for multi-agent systems

---

## Findings

### Recommended UI/UX Roles

| Role | Model | SDLC Phases | Parallel Capability |
|------|-------|-------------|---------------------|
| **UX Researcher** | opus | Requirements, Quality | Yes |
| **UI Designer** | sonnet | Design, Implementation | Yes |
| **Accessibility Specialist** | opus | Requirements, Design, Quality | Yes |
| **Frontend Architect** | opus | Design, Implementation | Yes |
| **Design System Engineer** | sonnet | Design, Implementation | Yes |

---

## Role 1: UX Researcher Agent

### Responsibilities

1. **User Research**
   - Conduct user interview analysis
   - Create personas and journey maps
   - Identify pain points and opportunities
   - Competitive analysis

2. **Usability Research**
   - Heuristic evaluations
   - Cognitive walkthrough analysis
   - Task flow optimization
   - Information architecture validation

3. **Data-Driven Insights**
   - Analytics interpretation
   - A/B test analysis
   - User feedback synthesis
   - Behavioral pattern identification

### SDLC Phase Mapping

| Phase | Activities | Parallel With |
|-------|------------|---------------|
| **Requirements** | User research, personas, journey maps | BA, Research Scientist |
| **Quality** | Usability testing, user validation | QA Automation |

### Agent Specification

```yaml
name: ux-researcher
description: User research, personas, usability studies, and user-centered insight generation
model: opus
color: purple
tools: ["Read", "Write", "Grep", "Glob", "WebSearch", "WebFetch"]
phases: [requirements, quality]
```

### Output Artifacts

**Persona Template:**
```markdown
# Persona: [Name]

## Demographics
- Age: [range]
- Role: [job title/context]
- Tech Savviness: [Low/Medium/High]

## Goals
- [Primary goal]
- [Secondary goal]

## Pain Points
- [Frustration 1]
- [Frustration 2]

## Behaviors
- [Key behavior pattern]
- [Device/platform preferences]

## Scenarios
"[Quotes representing user needs]"
```

**Journey Map Template:**
```markdown
# User Journey: [Journey Name]

## Persona
[Link to persona]

## Stages

### 1. Awareness
- **Actions:** [What user does]
- **Thoughts:** [What user thinks]
- **Emotions:** [Feeling level: -2 to +2]
- **Pain Points:** [Frustrations]
- **Opportunities:** [Improvements]

### 2. Consideration
[Same structure...]

### 3. Decision
[Same structure...]

### 4. Retention
[Same structure...]
```

---

## Role 2: UI Designer Agent

### Responsibilities

1. **Visual Design**
   - Create wireframes and mockups
   - Define visual hierarchy
   - Color palette and typography
   - Component-level design

2. **Interaction Design**
   - User flow diagrams
   - Micro-interaction patterns
   - State management (hover, active, disabled)
   - Responsive behavior specifications

3. **Prototyping**
   - Low-fidelity wireframes
   - High-fidelity mockups
   - Interactive prototype specifications
   - Design-to-code handoff documentation

### SDLC Phase Mapping

| Phase | Activities | Parallel With |
|-------|------------|---------------|
| **Design** | Wireframes, visual design, interaction patterns | Architect, Design System Engineer |
| **Implementation** | Design handoff, component specs, visual QA | Senior Engineer, Junior Engineer |

### Agent Specification

```yaml
name: ui-designer
description: Visual design, wireframes, mockups, interaction patterns, and design handoff
model: sonnet
color: pink
tools: ["Read", "Write", "Glob", "Grep"]
phases: [design, implementation]
```

### Output Artifacts

**Wireframe Specification:**
```markdown
# Wireframe: [Screen Name]

## Purpose
[What this screen accomplishes]

## Layout Grid
- Columns: [12-column grid]
- Gutter: [spacing]
- Margins: [responsive breakpoints]

## Components

### Header
- Logo: [placement]
- Navigation: [items]
- Actions: [CTAs]

### Main Content
[Component hierarchy with rough dimensions]

### Footer
[Component list]

## Responsive Behavior
- Desktop (1200px+): [layout]
- Tablet (768-1199px): [layout]
- Mobile (<768px): [layout]

## Interactions
- [Element]: [Interaction type] -> [Result]
```

**Design Token Specification:**
```json
{
  "colors": {
    "primary": {"value": "#007AFF", "description": "Primary brand color"},
    "secondary": {"value": "#5856D6", "description": "Secondary actions"},
    "success": {"value": "#34C759", "description": "Success states"},
    "warning": {"value": "#FF9500", "description": "Warning states"},
    "error": {"value": "#FF3B30", "description": "Error states"}
  },
  "spacing": {
    "xs": "4px",
    "sm": "8px",
    "md": "16px",
    "lg": "24px",
    "xl": "32px"
  },
  "typography": {
    "heading-1": {"size": "32px", "weight": "700", "lineHeight": "1.2"},
    "body": {"size": "16px", "weight": "400", "lineHeight": "1.5"}
  }
}
```

---

## Role 3: Accessibility Specialist Agent

### Responsibilities

1. **Standards Compliance**
   - WCAG 2.2 AA/AAA compliance audits
   - Section 508 requirements
   - ADA compliance verification
   - International accessibility standards

2. **Inclusive Design**
   - Color contrast validation
   - Screen reader compatibility
   - Keyboard navigation patterns
   - Cognitive accessibility considerations

3. **Automated Testing**
   - Accessibility test automation (axe-core, Pa11y)
   - CI/CD integration for a11y checks
   - Regression testing for accessibility
   - Assistive technology testing specifications

### SDLC Phase Mapping

| Phase | Activities | Parallel With |
|-------|------------|---------------|
| **Requirements** | Define accessibility requirements, WCAG targets | BA, UX Researcher |
| **Design** | Review wireframes for a11y, color contrast, focus states | UI Designer |
| **Quality** | Automated a11y audits, manual screen reader testing | QA Automation |

### Agent Specification

```yaml
name: accessibility-specialist
description: WCAG compliance, inclusive design, accessibility audits, and assistive technology testing
model: opus
color: green
tools: ["Read", "Write", "Edit", "Grep", "Glob", "Bash"]
phases: [requirements, design, quality]
```

### Output Artifacts

**Accessibility Audit Report:**
```markdown
# Accessibility Audit: [Feature/Page Name]

## Compliance Target
- WCAG Version: 2.2
- Conformance Level: AA

## Audit Summary
| Category | Issues | Severity | Status |
|----------|--------|----------|--------|
| Perceivable | [count] | [Critical/Major/Minor] | [Pass/Fail] |
| Operable | [count] | [Critical/Major/Minor] | [Pass/Fail] |
| Understandable | [count] | [Critical/Major/Minor] | [Pass/Fail] |
| Robust | [count] | [Critical/Major/Minor] | [Pass/Fail] |

## Critical Issues (Must Fix)

### A11Y-001: [Issue Title]
- **WCAG Criterion:** [e.g., 1.4.3 Contrast Minimum]
- **Element:** [selector/description]
- **Current State:** [what's wrong]
- **Required Fix:** [how to fix]
- **Code Example:**
```html
<!-- Before -->
<button style="color: #999;">Submit</button>

<!-- After -->
<button style="color: #595959;">Submit</button>
```

## Recommendations
- [ ] [Improvement 1]
- [ ] [Improvement 2]

## Testing Tools Used
- axe-core v[version]
- WAVE
- VoiceOver / NVDA manual testing
```

**Accessibility Requirements Checklist:**
```markdown
# Accessibility Requirements: [Feature Name]

## Perceivable
- [ ] All images have meaningful alt text
- [ ] Color is not the only visual means of conveying information
- [ ] Text contrast ratio meets 4.5:1 (AA) or 7:1 (AAA)
- [ ] Text can be resized up to 200% without loss of content

## Operable
- [ ] All functionality available via keyboard
- [ ] No keyboard traps
- [ ] Focus order is logical and intuitive
- [ ] Focus indicators are visible
- [ ] Skip links provided for main content

## Understandable
- [ ] Language of page is identified
- [ ] Labels and instructions are clear
- [ ] Error messages are descriptive
- [ ] Consistent navigation patterns

## Robust
- [ ] Valid HTML markup
- [ ] ARIA roles used correctly
- [ ] Name, role, value exposed to assistive technology
```

---

## Role 4: Frontend Architect Agent

### Responsibilities

1. **Frontend Architecture**
   - Component architecture patterns
   - State management strategy
   - Performance architecture (code splitting, lazy loading)
   - Rendering strategy (SSR, SSG, CSR, ISR)

2. **Technology Selection**
   - Framework evaluation and selection
   - Build tool configuration
   - Testing infrastructure
   - CI/CD for frontend

3. **Standards Definition**
   - Coding standards for frontend
   - Component API patterns
   - Error handling patterns
   - Performance budgets

### SDLC Phase Mapping

| Phase | Activities | Parallel With |
|-------|------------|---------------|
| **Design** | Frontend ADRs, technology selection, architecture diagrams | Software Architect |
| **Implementation** | Scaffold structure, core patterns, code reviews | Staff Engineer |

### Agent Specification

```yaml
name: frontend-architect
description: Frontend architecture, component patterns, state management, performance optimization
model: opus
color: cyan
tools: ["Read", "Write", "Edit", "Grep", "Glob", "Bash"]
phases: [design, implementation]
```

### Output Artifacts

**Frontend ADR Template:**
```markdown
# ADR-FE-001: [Decision Title]

## Status
[Proposed/Accepted/Deprecated]

## Context
[Frontend-specific challenge or requirement]

## Decision

### Component Architecture
[Pattern chosen: Atomic Design, Feature-Sliced, etc.]

### State Management
[Strategy: React Query, Zustand, Redux, Context, etc.]

### Rendering Strategy
| Route Type | Strategy | Reason |
|------------|----------|--------|
| Marketing pages | SSG | SEO, performance |
| Dashboard | CSR | Dynamic content |
| Product pages | ISR | Balance of SEO + freshness |

### Performance Budget
| Metric | Target | Tool |
|--------|--------|------|
| LCP | < 2.5s | Lighthouse |
| FID | < 100ms | Web Vitals |
| CLS | < 0.1 | Web Vitals |
| Bundle Size | < 200KB (initial) | Webpack Analyzer |

## Consequences

### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Trade-off 1]
- [Trade-off 2]

### Risks
- [Risk with mitigation]
```

**Component Architecture Diagram:**
```
src/
├── components/
│   ├── atoms/           # Basic UI elements
│   │   ├── Button/
│   │   ├── Input/
│   │   └── Icon/
│   ├── molecules/       # Combinations of atoms
│   │   ├── FormField/
│   │   ├── SearchBar/
│   │   └── NavItem/
│   ├── organisms/       # Complex UI sections
│   │   ├── Header/
│   │   ├── Sidebar/
│   │   └── DataTable/
│   └── templates/       # Page layouts
│       ├── DashboardLayout/
│       └── AuthLayout/
├── features/            # Feature-based modules
│   ├── auth/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── api/
│   │   └── store/
│   └── dashboard/
├── hooks/               # Shared hooks
├── utils/               # Utilities
├── styles/              # Global styles
└── types/               # TypeScript types
```

---

## Role 5: Design System Engineer Agent

### Responsibilities

1. **Component Library**
   - Build reusable UI components
   - Document component APIs
   - Maintain Storybook/documentation
   - Version and publish components

2. **Design Tokens**
   - Implement design tokens
   - Theme support (light/dark/custom)
   - CSS-in-JS or CSS variables
   - Token documentation

3. **Design-Dev Bridge**
   - Figma-to-code automation
   - Design token synchronization
   - Component parity verification
   - Style guide maintenance

### SDLC Phase Mapping

| Phase | Activities | Parallel With |
|-------|------------|---------------|
| **Design** | Design token implementation, theme architecture | UI Designer |
| **Implementation** | Component library building, Storybook docs | Senior/Junior Engineer |

### Agent Specification

```yaml
name: design-system-engineer
description: Component library, design tokens, theming, Storybook documentation
model: sonnet
color: orange
tools: ["Read", "Write", "Edit", "Grep", "Glob", "Bash"]
phases: [design, implementation]
```

### Output Artifacts

**Component Specification:**
```markdown
# Component: Button

## Variants
| Variant | Use Case |
|---------|----------|
| primary | Main CTAs |
| secondary | Secondary actions |
| ghost | Tertiary actions |
| destructive | Delete/dangerous actions |

## Props API
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| variant | 'primary' \| 'secondary' \| 'ghost' \| 'destructive' | 'primary' | Visual style |
| size | 'sm' \| 'md' \| 'lg' | 'md' | Button size |
| disabled | boolean | false | Disabled state |
| loading | boolean | false | Loading state |
| leftIcon | ReactNode | - | Icon before label |
| rightIcon | ReactNode | - | Icon after label |
| fullWidth | boolean | false | 100% width |

## Accessibility
- Role: button
- Keyboard: Enter/Space to activate
- Focus: Visible focus ring
- Disabled: aria-disabled="true"
- Loading: aria-busy="true"

## Usage Examples

### Basic
```tsx
<Button variant="primary">Click me</Button>
```

### With Icon
```tsx
<Button leftIcon={<PlusIcon />}>Add Item</Button>
```

### Loading State
```tsx
<Button loading>Saving...</Button>
```

## Design Tokens Used
- `--color-primary`
- `--spacing-md`
- `--radius-md`
- `--font-weight-semibold`
```

**Design Token Implementation:**
```css
/* tokens.css */
:root {
  /* Colors - Light Theme */
  --color-background: #ffffff;
  --color-foreground: #0a0a0a;
  --color-primary: #007aff;
  --color-primary-foreground: #ffffff;
  --color-secondary: #f4f4f5;
  --color-secondary-foreground: #18181b;
  --color-muted: #f4f4f5;
  --color-muted-foreground: #71717a;
  --color-accent: #f4f4f5;
  --color-destructive: #ef4444;
  --color-border: #e4e4e7;
  --color-ring: #007aff;

  /* Spacing */
  --spacing-1: 0.25rem;
  --spacing-2: 0.5rem;
  --spacing-3: 0.75rem;
  --spacing-4: 1rem;
  --spacing-6: 1.5rem;
  --spacing-8: 2rem;

  /* Typography */
  --font-sans: system-ui, -apple-system, sans-serif;
  --font-mono: ui-monospace, monospace;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;

  /* Borders */
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

[data-theme="dark"] {
  --color-background: #0a0a0a;
  --color-foreground: #fafafa;
  --color-primary: #3b82f6;
  /* ... dark theme overrides */
}
```

---

## Context Engineering Best Practices

### Orchestrator-Workers Pattern for UI/UX

Based on Anthropic's research, the orchestrator-workers pattern is optimal for UI/UX agent coordination:

```
┌─────────────────────────────────────────────────────────────┐
│                    SDLC ORCHESTRATOR                         │
│  (Central coordinator - determines subtasks dynamically)     │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  UX Researcher  │  │  UI Designer    │  │  Accessibility  │
│  (Worker)       │  │  (Worker)       │  │  (Worker)       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │   SYNTHESIZER   │
                    │  (Aggregates    │
                    │   results)      │
                    └─────────────────┘
```

### Context Isolation Levels

From the research on subagent best practices:

| Level | Context Passed | Use Case | UI/UX Application |
|-------|----------------|----------|-------------------|
| **Level 1: Complete Isolation** | Only the specific task | 80% of cases | Component spec generation, individual audits |
| **Level 2: Filtered Context** | Curated relevant background | 15% of cases | Cross-referencing design tokens with wireframes |
| **Level 3: Windowed Context** | Last N messages | 5% of cases | Iterative design feedback loops |

### Context Engineering Rules

1. **Minimize Context Pollution**
   - Each UI/UX agent receives only relevant design artifacts
   - Don't pass entire design system to accessibility auditor
   - Pass specific component specs, not the whole library

2. **Compress and Summarize**
   - Personas: Pass summary, not full research transcripts
   - Design tokens: Pass relevant subset for current component
   - Audit results: Pass critical issues only, not full reports

3. **Single Responsibility**
   - UX Researcher: Only user research, not visual design
   - Accessibility Specialist: Only a11y, not performance
   - Design System Engineer: Only components, not page layouts

4. **Stateless Subagents**
   - Each agent call is like a pure function
   - No shared memory between agent invocations
   - Enables parallel execution without conflicts

### Delegation Example

```python
# Orchestrator delegates to UI/UX workers in parallel
class UIUXOrchestrator:
    async def design_feature(self, feature: str, context: dict):
        # Phase 1: Requirements (parallel)
        research_results = await asyncio.gather(
            self.delegate("ux-researcher", "Create personas for " + feature, context),
            self.delegate("accessibility-specialist", "Define a11y requirements for " + feature, context),
        )

        # Phase 2: Design (parallel, with requirements context)
        design_context = {**context, "personas": research_results[0], "a11y_reqs": research_results[1]}
        design_results = await asyncio.gather(
            self.delegate("ui-designer", "Create wireframes for " + feature, design_context),
            self.delegate("frontend-architect", "Define component architecture for " + feature, design_context),
            self.delegate("design-system-engineer", "Identify required design tokens for " + feature, design_context),
        )

        return self.synthesize(research_results, design_results)
```

---

## Updated SDLC Workflow with UI/UX Agents

```
┌──────────────────────────────────────────────────────────────┐
│                    SDLC WORKFLOW (UPDATED)                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Phase 1: REQUIREMENTS (Parallel)                            │
│  ├── CEO/Stakeholder  → Business goals                      │
│  ├── Business Analyst → User stories                        │
│  ├── Research Scientist → Feasibility                       │
│  ├── UX Researcher → Personas, journey maps           [NEW] │
│  └── Accessibility Specialist → A11y requirements     [NEW] │
│                         ↓                                    │
│  Phase 2: DESIGN (Parallel)                                  │
│  ├── Software Architect → System design                     │
│  ├── Data Scientist → Data models                           │
│  ├── Network Engineer → Infrastructure                      │
│  ├── Frontend Architect → FE architecture             [NEW] │
│  ├── UI Designer → Wireframes, visual design          [NEW] │
│  ├── Design System Engineer → Design tokens           [NEW] │
│  └── Accessibility Specialist → A11y review           [NEW] │
│                         ↓                                    │
│  Phase 3: IMPLEMENT (Parallel by Layer)                      │
│  ├── Staff Engineer → Core architecture                     │
│  ├── Senior Engineer → Feature modules                      │
│  ├── Junior Engineer → UI components                        │
│  ├── DevOps Engineer → CI/CD                                │
│  ├── Frontend Architect → FE scaffolding              [NEW] │
│  ├── UI Designer → Design handoff, visual QA          [NEW] │
│  └── Design System Engineer → Component library       [NEW] │
│                         ↓                                    │
│  Phase 4: QUALITY (Parallel)                                 │
│  ├── QA Automation → Test suites                            │
│  ├── Code Reviewer → PR reviews                             │
│  ├── Performance Engineer → Load tests                      │
│  ├── UX Researcher → Usability testing                [NEW] │
│  └── Accessibility Specialist → A11y audit            [NEW] │
│                         ↓                                    │
│  Phase 5: RELEASE (Sequential)                               │
│  ├── CI/CD Engineer → Build & deploy                        │
│  ├── Canary User → Beta testing                             │
│  ├── Documentation Engineer → Docs                          │
│  └── DevOps Engineer → Production                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Recommendation

### Primary Recommendation

Add all 5 UI/UX roles to the SDLC orchestration system:

| Priority | Role | Justification |
|----------|------|---------------|
| **P0** | Accessibility Specialist | Legal compliance, reaches across all phases |
| **P0** | UI Designer | Core visual design capability |
| **P1** | Frontend Architect | Technical leadership for frontend |
| **P1** | Design System Engineer | Enables component reusability |
| **P2** | UX Researcher | Enhances user-centered approach |

### Implementation Order

1. **Sprint 1:** Add Accessibility Specialist (cross-phase, high ROI)
2. **Sprint 2:** Add UI Designer + Design System Engineer (paired)
3. **Sprint 3:** Add Frontend Architect (architecture focus)
4. **Sprint 4:** Add UX Researcher (research capability)

### Model Allocation

| Role | Recommended Model | Rationale |
|------|-------------------|-----------|
| UX Researcher | opus | Complex analysis, synthesis |
| UI Designer | sonnet | Creative + structured output |
| Accessibility Specialist | opus | Critical compliance decisions |
| Frontend Architect | opus | Architecture decisions |
| Design System Engineer | sonnet | Implementation-focused |

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Context explosion with 22 agents | High | Strict context isolation, hierarchical orchestration |
| UI/UX agents conflict with engineering decisions | Medium | Clear ownership boundaries, escalation to Architect |
| Accessibility audits block releases | Medium | Shift-left a11y into Requirements/Design phases |
| Design token drift between agents | Low | Single source of truth in Design System Engineer |
| Increased token costs | Medium | Use Haiku for simple tasks, cache common outputs |

---

## Next Steps

1. [ ] Create agent definition files for 5 new UI/UX roles
2. [ ] Update SDLC orchestration workflow to include new agents
3. [ ] Define inter-agent communication protocols (XML format)
4. [ ] Create role annotation shortcuts (`[@ux]`, `[@a11y]`, `[@ui]`, etc.)
5. [ ] Build example feature workflow with UI/UX agents
6. [ ] Add accessibility audit to CI/CD quality gate
7. [ ] Create design token pipeline for Design System Engineer

---

## References

### Anthropic Documentation
- [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) - Core agent patterns
- [Orchestrator-Workers Pattern](https://platform.claude.com/cookbook/patterns-agents-orchestrator-workers) - Delegation pattern
- [Claude Cookbooks - Agents](https://github.com/anthropics/claude-cookbooks/tree/main/patterns/agents) - Reference implementations

### Industry Research (2026)
- [State of UX in 2026 - NN/G](https://www.nngroup.com/articles/state-of-ux-2026/) - UX trends and AI integration
- [2026: The Year of Agentic Development](https://dev.to/mikulg/2026-the-year-of-agentic-development-4507) - Multi-agent system trends
- [5 Key Trends Shaping Agentic Development in 2026](https://thenewstack.io/5-key-trends-shaping-agentic-development-in-2026/) - Agent architecture patterns
- [The 2026 Architect's Dilemma](https://dev.to/ridwan_sassman_3d07/the-2026-architects-dilemma-orchestrating-ai-agents-not-writing-code-the-paradigm-shift-from-219c) - Orchestration over coding
- [AI in Accessibility Testing: Complete Guide 2026](https://thectoclub.com/software-development/artificial-intelligence-in-accessibility-testing/) - A11y automation

### Frontend Architecture
- [Agentic AI Frontend Patterns](https://blog.logrocket.com/agentic-ai-frontend-patterns/) - UI patterns for agents
- [AI-Ready Frontend Architecture Guide](https://blog.logrocket.com/ai-ready-frontend-architecture-guide) - Architecture best practices
- [From Prompt to Production: AI-Generated Design Systems](https://thenewstack.io/from-prompt-to-production-a-guide-to-ai-generated-design-systems/) - Design system automation

### Context Engineering
- [Context Engineering for AI Agents](https://www.philschmid.de/context-engineering-part-2) - Advanced context strategies
- [Claude Code Subagents Best Practices](https://claudekit.cc/blog/vc-04-subagents-from-basic-to-deep-dive-i-misunderstood) - Subagent patterns
- [Multi-Agent Systems with Context Engineering](https://www.vellum.ai/blog/multi-agent-systems-building-with-context-engineering) - Framework guide
- [Subagents in Claude Code](https://wmedia.es/en/writing/claude-code-subagents-guide-ai) - Divide and conquer patterns
- [Architecting Context-Aware Multi-Agent Framework](https://developers.googleblog.com/architecting-efficient-context-aware-multi-agent-framework-for-production/) - Google's production patterns

### Accessibility
- [BrowserStack AI Agent for Accessibility Testing](https://www.browserstack.com/accessibility-testing/ai-agents) - AI a11y agent
- [2026 Report: Digital Accessibility Compliance](https://accessible.org/digital-accessibility-compliance-changing/) - Compliance trends
- [AI and Accessibility: WCAG Compliance](https://www.adacompliancepros.com/blog/ai-and-accessibility-how-machine-learning-is-changing-wcag-compliance) - ML for WCAG

---

## Appendix A: Agent Definition Files

See proposed agent definition files in the companion document:
- `agents/ux-researcher.md`
- `agents/ui-designer.md`
- `agents/accessibility-specialist.md`
- `agents/frontend-architect.md`
- `agents/design-system-engineer.md`

---

*Report generated: 2026-01-22*
*Research Scientist Agent - SDLC Orchestration*
