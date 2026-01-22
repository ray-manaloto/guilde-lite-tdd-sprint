# Requirements: Multi-Agent Workflow Visualization

## Overview
Update the webapp to reflect the parallel multi-agent workflow with OpenAI/Anthropic subagents and judge selection, providing users visibility into the dual-subagent execution, candidate comparison, and real-time sprint progress.

## Business Context
The backend has evolved to support a dual-subagent architecture where OpenAI and Anthropic agents compete in parallel, with a judge selecting the best output. Users currently lack visibility into:
- How many questions to request during planning interviews
- Which candidates competed and their individual performance
- Why the judge selected a particular winner
- Token consumption and model metadata for cost monitoring
- Artifact outputs and trace logs for debugging
- Real-time progress during sprint execution

## Functional Requirements

### FR-001: Dynamic Question Count Configuration
The frontend shall allow users to configure the number of planning interview questions (1-10).

### FR-002: Candidate Pairs Visualization
The frontend shall display all candidate subagent responses side-by-side for comparison.

### FR-003: Judge Decision Display
The frontend shall display the judge's score, rationale, and winner selection.

### FR-004: Token Usage and Model Metadata
The frontend shall display token consumption and model identifiers for each subagent run.

### FR-005: Artifact and Log Trace Visualization
The frontend shall provide access to workflow artifacts and Logfire trace links.

### FR-006: Real-Time Sprint Updates
The frontend shall display real-time progress updates during sprint execution via WebSocket.

## Non-Functional Requirements

### NFR-001: Performance
- WebSocket updates should render within 100ms of receipt
- Candidate comparison view should load within 2 seconds

### NFR-002: Usability
- Question count slider should provide immediate visual feedback
- Judge rationale should be clearly distinguishable from candidate outputs

### NFR-003: Accessibility
- All interactive elements must be keyboard navigable
- Trace links must have descriptive aria labels

## Constraints
- Backend API contracts must not change in breaking ways
- WebSocket events currently only support `sprint_update` type
- Frontend is built with Next.js 15 and React 18

## Assumptions
- DUAL_SUBAGENT_ENABLED is the default mode going forward
- Users have Logfire access for trace URL navigation
- WorkflowTracker artifacts are persisted to AUTOCODE_ARTIFACTS_DIR

## Dependencies
- Backend `planning.metadata.candidates[]` structure (exists)
- Backend `planning.metadata.judge{}` structure (exists)
- WorkflowTracker saves `timeline.json`, `phases/`, `candidates/` (exists)
- WebSocket `sprint_update` events (exists, needs expansion)

## Out of Scope
- Backend API changes to the planning interview flow
- Authentication/authorization for artifact access
- Mobile-responsive optimizations (follow-up sprint)
- Artifact file browser/download functionality

---

# User Stories

## User Story 1: Dynamic Question Count in Sprint Interview

**As a** product manager creating a sprint
**I want** to configure how many clarifying questions the planning interview asks
**So that** I can balance thoroughness vs. speed based on task complexity

### Acceptance Criteria

**Scenario 1: Default question count**
```
Given I am on the sprint planning interview form
When I view the question count control
Then I should see a default value of 5 questions
```

**Scenario 2: Adjust question count**
```
Given I am on the sprint planning interview form
When I adjust the question count slider to 3
And I click "Start planning interview"
Then the backend receives max_questions=3
And I receive at most 3 clarifying questions
```

**Scenario 3: Boundary validation**
```
Given I am on the sprint planning interview form
When I attempt to set questions below 1 or above 10
Then the control prevents invalid values
And shows appropriate validation feedback
```

### Technical Notes
- Backend `SpecPlanningCreate.max_questions` already supports 1-10 range
- Frontend currently hardcodes POST body without max_questions
- Add slider or number input to sprint planning interview card
- Store preference in component state (no persistence needed)

### Priority
**P0 - Must Have** (Low effort, high impact for user control)

---

## User Story 2: Visualization of Candidate Pairs

**As a** developer reviewing sprint planning results
**I want** to see both OpenAI and Anthropic candidate responses side-by-side
**So that** I can understand the quality difference and why one was selected

### Acceptance Criteria

**Scenario 1: Display candidate cards**
```
Given a sprint planning interview has completed with dual subagents
When I view the telemetry panel
Then I see two candidate cards (OpenAI and Anthropic)
And each card shows provider name and model identifier
```

**Scenario 2: Show candidate outputs**
```
Given I am viewing candidate cards
When I expand a candidate card
Then I see the full list of questions that candidate generated
And I see any error message if the candidate failed
```

**Scenario 3: Highlight selected candidate**
```
Given the judge has selected a winner
When I view the candidate cards
Then the selected candidate has a "Selected" badge
And the card has visual emphasis (border/background)
```

**Scenario 4: Handle single candidate fallback**
```
Given only one candidate succeeded (other errored)
When I view the telemetry panel
Then I see one successful candidate card
And I see one error card showing the failure reason
```

### Technical Notes
- `planning.metadata.candidates[]` contains provider, model_name, trace_id, trace_url, error
- `planning.metadata.selected_candidate.provider` indicates the winner
- Current UI shows candidates in a list; refactor to side-by-side comparison
- Consider collapsible sections for question lists

### Priority
**P0 - Must Have** (Core visibility into dual-subagent architecture)

---

## User Story 3: Display of Judge Score, Rationale, and Winner Selection

**As a** team lead evaluating AI decision quality
**I want** to see the judge's reasoning for selecting a candidate
**So that** I can audit the selection process and understand model performance

### Acceptance Criteria

**Scenario 1: Display judge metadata**
```
Given a sprint planning interview used dual subagents
When I view the telemetry panel
Then I see a Judge Decision section
And it shows the judge provider and model name
```

**Scenario 2: Show judge score**
```
Given the judge returned a score
When I view the Judge Decision section
Then I see the overall score (0-1 scale)
And I see helpfulness and correctness sub-scores if available
```

**Scenario 3: Display rationale**
```
Given the judge returned a rationale
When I view the Judge Decision section
Then I see the full rationale text explaining the selection
And long rationales are expandable/collapsible
```

**Scenario 4: Link to judge trace**
```
Given the judge has a trace_url
When I view the Judge Decision section
Then I see a "View Trace" link that opens Logfire in a new tab
```

### Technical Notes
- `planning.metadata.judge` contains provider, model_name, trace_id, trace_url, score, rationale
- Rationale may contain parsed sub-scores like "helpfulness=0.9; correctness=0.7"
- Current UI shows judge info inline; enhance with dedicated card/section
- Score visualization could use a progress bar or gauge

### Priority
**P0 - Must Have** (Critical for auditability and trust)

---

## User Story 4: Token Usage and Model Metadata Display

**As a** engineering manager monitoring costs
**I want** to see token consumption for each subagent execution
**So that** I can track API costs and optimize model selection

### Acceptance Criteria

**Scenario 1: Display model identifiers**
```
Given a sprint execution has completed
When I view the workflow details
Then I see the exact model name for each candidate (e.g., "gpt-4o-mini", "claude-3-5-sonnet")
```

**Scenario 2: Show token counts (when available)**
```
Given token metrics are captured in candidate metadata
When I view candidate details
Then I see input tokens, output tokens, and total tokens
And I see estimated cost if cost-per-token is configured
```

**Scenario 3: Aggregate metrics**
```
Given a sprint has multiple phases
When I view the sprint summary
Then I see total token usage across all phases
And I see breakdown by provider
```

### Technical Notes
- Token data stored in `candidate.metrics.tokens` (when available from provider)
- WorkflowTracker records `duration_ms` per candidate
- May need backend enhancement to capture token counts from PydanticAI
- Consider deferred implementation if token capture requires API changes

### Priority
**P1 - Should Have** (Valuable for cost monitoring, may need backend work)

---

## User Story 5: Artifact and Log Trace Visualization

**As a** developer debugging a failed sprint
**I want** to access workflow artifacts and execution traces
**So that** I can diagnose issues and understand the execution flow

### Acceptance Criteria

**Scenario 1: Display trace links**
```
Given a phase has an associated trace_id
When I view the phase details
Then I see a "View in Logfire" link
And clicking it opens the trace in a new browser tab
```

**Scenario 2: Show timeline events**
```
Given a sprint has completed
When I view the sprint details
Then I see a timeline of events (started, phase_started, candidates_generated, judge_decision, completed)
And each event shows timestamp and duration
```

**Scenario 3: Access phase artifacts**
```
Given WorkflowTracker has saved phase records
When I view a completed phase
Then I see links to view input/output data
And I see checkpoint identifiers for branching reference
```

**Scenario 4: Handle missing traces**
```
Given LOGFIRE_TRACE_URL_TEMPLATE is not configured
When I view trace information
Then I see the raw trace_id with a hint about configuration
And I do not see broken links
```

### Technical Notes
- WorkflowTracker saves to `AUTOCODE_ARTIFACTS_DIR/{sprint_id}/`
- Timeline at `timeline.json`, phases at `phases/`, candidates at `candidates/`
- Current UI shows trace links when `trace_url` exists
- Need new API endpoint to serve artifact content (out of scope) or display metadata only

### Priority
**P1 - Should Have** (Important for debugging, partial implementation possible)

---

## User Story 6: Real-Time Updates During Sprint Execution

**As a** user who has triggered a sprint
**I want** to see live progress updates
**So that** I know what phase is executing and can monitor completion

### Acceptance Criteria

**Scenario 1: Connect to sprint room**
```
Given I have created a sprint
When the sprint page loads
Then the frontend connects to WebSocket room `/ws/{sprint_id}`
And displays "Connected" status indicator
```

**Scenario 2: Display phase transitions**
```
Given I am connected to the sprint WebSocket
When the backend broadcasts a sprint_update event
Then I see the current phase name (discovery, coding, verification)
And I see the phase status (active, complete, failed)
```

**Scenario 3: Show progress details**
```
Given I am viewing a sprint in progress
When I receive sprint_update events
Then I see the details message (e.g., "Analyzing requirements...")
And I see attempt number for retry phases
```

**Scenario 4: Handle disconnection**
```
Given I am connected to the sprint WebSocket
When the connection is lost
Then I see a "Disconnected" status indicator
And the UI attempts automatic reconnection
And shows a manual "Reconnect" button
```

**Scenario 5: Support multiple event types**
```
Given the backend sends events for candidates and judge decisions
When I receive these events
Then the candidate cards update in real-time
And the judge decision appears when available
```

### Technical Notes
- Current WebSocket at `/api/v1/ws/{room}` supports `broadcast_to_room`
- PhaseRunner broadcasts `sprint_update` type events
- Need to extend event types: `candidate_result`, `judge_decision`, `phase_complete`
- Frontend needs WebSocket hook with reconnection logic
- Consider using React Query for WebSocket state management

### Priority
**P0 - Must Have** (Core UX for sprint execution visibility)

---

## Implementation Checklist

### Phase 1: Foundation (P0 Stories)
- [ ] US-1: Add question count control to planning interview form
- [ ] US-2: Create side-by-side candidate comparison component
- [ ] US-3: Add judge decision card with score and rationale
- [ ] US-6: Implement WebSocket connection and event handling

### Phase 2: Enhanced Visibility (P1 Stories)
- [ ] US-4: Add token usage display (frontend only, pending backend data)
- [ ] US-5: Add timeline visualization component
- [ ] US-5: Add trace link handling with fallback for missing config

### Phase 3: Polish
- [ ] Responsive design for candidate comparison
- [ ] Keyboard navigation for all new components
- [ ] Loading states and error boundaries
- [ ] Unit tests for new components

---

## Appendix: Data Structures

### SpecPlanningMetadata (from frontend/src/types/specs.ts)
```typescript
interface SpecPlanningMetadata {
  mode?: string;
  provider?: string | null;
  model_name?: string | null;
  max_questions?: number;
  question_count?: number;
  trace_id?: string | null;
  trace_url?: string | null;
  candidates?: SpecPlanningTelemetryLink[];
  judge?: {
    provider?: string | null;
    model_name?: string | null;
    trace_id?: string | null;
    trace_url?: string | null;
    score?: number | null;
    rationale?: string | null;
  };
  selected_candidate?: {
    provider?: string | null;
    model_name?: string | null;
  };
}
```

### WebSocket sprint_update Event (current)
```json
{
  "type": "sprint_update",
  "sprint_id": "uuid",
  "status": "active|completed|failed",
  "phase": "discovery|coding|verification",
  "details": "Human readable message"
}
```

### Proposed Extended Events
```json
{
  "type": "candidate_result",
  "sprint_id": "uuid",
  "phase": "discovery",
  "candidate": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "success": true,
    "duration_ms": 1234
  }
}

{
  "type": "judge_decision",
  "sprint_id": "uuid",
  "phase": "discovery",
  "judge": {
    "winner": "openai",
    "score": 0.85,
    "rationale": "Better question coverage"
  }
}
```
