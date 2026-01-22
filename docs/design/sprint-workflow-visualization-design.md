# Sprint Workflow Visualization - System Design

**Version:** 1.0.0
**Status:** Proposed
**Author:** Software Architect Agent
**Date:** 2026-01-22

---

## Table of Contents

1. [Overview](#overview)
2. [Current State Analysis](#current-state-analysis)
3. [Requirements Traceability](#requirements-traceability)
4. [API Design](#api-design)
5. [WebSocket Event Design](#websocket-event-design)
6. [Data Flow Architecture](#data-flow-architecture)
7. [Component Architecture](#component-architecture)
8. [Data Models](#data-models)
9. [Performance Considerations](#performance-considerations)
10. [ADRs](#architecture-decision-records)

---

## Overview

### Purpose

This document defines the system architecture for visualizing multi-agent workflow execution in the sprint board. The design enables real-time display of:

- Dynamic interview question counts (1-10 questions, not hardcoded)
- Judge selection visualization with OpenAI/Anthropic candidate comparisons
- Judge scores, subagent models, and token usage metrics
- Specs, artifacts, and Logfire trace links
- Real-time WebSocket updates during sprint execution

### Scope

| In Scope | Out of Scope |
|----------|--------------|
| REST API endpoints for workflow data | Agent execution logic changes |
| Enhanced WebSocket event types | LLM model selection algorithms |
| Frontend React components | Authentication/authorization |
| Data flow from WorkflowTracker to UI | Database schema migrations |

---

## Current State Analysis

### Existing Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `WorkflowTracker` | `/backend/app/services/workflow_tracker.py` | Saves timeline.json with candidates, judges, phases |
| `PhaseRunner` | `/backend/app/runners/phase_runner.py` | Orchestrates sprint phases, broadcasts basic events |
| `ConnectionManager` | `/backend/app/api/routes/v1/ws.py` | WebSocket room-based broadcasting |
| `AgentTddService` | `/backend/app/services/agent_tdd.py` | Executes multi-provider subagents with judge |
| Sprint Page | `/frontend/src/app/[locale]/(dashboard)/sprints/page.tsx` | Displays sprint board with telemetry panel |

### Gaps Identified

1. **No REST endpoints** for retrieving workflow/timeline data
2. **WebSocket events are generic** - only `sprint_update` type with limited detail
3. **No candidate comparison data** exposed to frontend
4. **Token usage metrics** captured but not surfaced
5. **Timeline events** stored on disk but not queryable via API

### Data Currently Available

From `WorkflowTracker`:
```
- timeline.json: Events with sequence, type, timestamp, trace_id, metadata
- phases/{phase}.json: Phase records with candidates, judge_result, model_config
- candidates/{phase}/{provider}/: Response and metadata per provider
- checkpoints/{checkpoint_id}.json: State snapshots for branching
- manifest.json: Sprint overview with paths and status
```

From `planning.metadata`:
```
- mode: "dual_subagent" | "single_agent"
- candidates[]: Array of {provider, model_name, trace_id, trace_url, questions}
- judge: {provider, model_name, trace_id, trace_url, score, rationale}
- selected_candidate: {provider, model_name}
```

---

## Requirements Traceability

| User Story | API Endpoint | WebSocket Event | Component |
|------------|--------------|-----------------|-----------|
| US-1: Dynamic questions (1-10) | GET /sprints/{id}/workflow | phase_update | InterviewProgress |
| US-2: Candidate comparison | GET /sprints/{id}/candidates | candidate_generated | CandidateComparison |
| US-3: Judge visualization | GET /sprints/{id}/workflow | judge_decision | JudgeVisualization |
| US-4: Token/cost tracking | GET /sprints/{id}/candidates | candidate_generated | TokenUsageChart |
| US-5: Artifact browser | GET /sprints/{id}/artifacts | artifact_created | ArtifactBrowser |
| US-6: Real-time updates | - | All events | WorkflowTimeline |

---

## API Design

### Endpoint Summary

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/sprints/{id}/workflow` | Full workflow state including phases, timeline, status |
| GET | `/sprints/{id}/candidates` | All candidates across phases with metrics |
| GET | `/sprints/{id}/timeline` | Chronological event stream |
| GET | `/sprints/{id}/artifacts` | List of generated artifacts with paths |
| GET | `/sprints/{id}/artifacts/{path}` | Download specific artifact content |

### GET /sprints/{sprint_id}/workflow

Returns the complete workflow state for visualization.

**Response Schema:**

```yaml
openapi: 3.0.0
paths:
  /sprints/{sprint_id}/workflow:
    get:
      summary: Get sprint workflow state
      parameters:
        - name: sprint_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Workflow state
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WorkflowState'
        '404':
          description: Sprint not found

components:
  schemas:
    WorkflowState:
      type: object
      properties:
        sprint_id:
          type: string
          format: uuid
        spec_id:
          type: string
          format: uuid
          nullable: true
        status:
          type: string
          enum: [planned, active, completed, failed]
        current_phase:
          type: string
          nullable: true
        total_duration_ms:
          type: integer
          nullable: true
        phases:
          type: array
          items:
            $ref: '#/components/schemas/PhaseState'
        planning:
          $ref: '#/components/schemas/PlanningState'
        logfire_project_url:
          type: string
          nullable: true

    PhaseState:
      type: object
      properties:
        phase:
          type: string
        sequence:
          type: integer
        status:
          type: string
          enum: [pending, in_progress, completed, failed, skipped]
        start_time:
          type: string
          format: date-time
          nullable: true
        end_time:
          type: string
          format: date-time
          nullable: true
        duration_ms:
          type: integer
          nullable: true
        model_config:
          type: object
          properties:
            openai_model:
              type: string
            anthropic_model:
              type: string
        candidates:
          type: array
          items:
            $ref: '#/components/schemas/CandidateSummary'
        judge_result:
          $ref: '#/components/schemas/JudgeResult'
        checkpoint_before:
          type: string
          nullable: true
        checkpoint_after:
          type: string
          nullable: true
        trace_id:
          type: string
          nullable: true
        trace_url:
          type: string
          nullable: true

    CandidateSummary:
      type: object
      properties:
        provider:
          type: string
          enum: [openai, anthropic, openrouter]
        model_name:
          type: string
        status:
          type: string
          enum: [pending, running, completed, failed]
        duration_ms:
          type: integer
          nullable: true
        token_usage:
          $ref: '#/components/schemas/TokenUsage'
        trace_id:
          type: string
          nullable: true
        trace_url:
          type: string
          nullable: true
        error:
          type: string
          nullable: true

    TokenUsage:
      type: object
      properties:
        prompt_tokens:
          type: integer
        completion_tokens:
          type: integer
        total_tokens:
          type: integer
        estimated_cost_usd:
          type: number
          format: float

    JudgeResult:
      type: object
      properties:
        model_name:
          type: string
        provider:
          type: string
        winner:
          type: string
          description: Provider name of winning candidate
        score:
          type: number
          format: float
          minimum: 0
          maximum: 1
        helpfulness_score:
          type: number
          format: float
          nullable: true
        correctness_score:
          type: number
          format: float
          nullable: true
        rationale:
          type: string
        trace_id:
          type: string
          nullable: true
        trace_url:
          type: string
          nullable: true

    PlanningState:
      type: object
      properties:
        status:
          type: string
          enum: [idle, needs_answers, answered]
        question_count:
          type: integer
          minimum: 1
          maximum: 10
        questions:
          type: array
          items:
            type: object
            properties:
              question:
                type: string
              rationale:
                type: string
                nullable: true
        answers:
          type: array
          items:
            type: object
            properties:
              question:
                type: string
              answer:
                type: string
        metadata:
          $ref: '#/components/schemas/PlanningMetadata'

    PlanningMetadata:
      type: object
      properties:
        mode:
          type: string
          enum: [single_agent, dual_subagent]
        candidates:
          type: array
          items:
            $ref: '#/components/schemas/CandidateSummary'
        judge:
          $ref: '#/components/schemas/JudgeResult'
        selected_candidate:
          type: object
          properties:
            provider:
              type: string
            model_name:
              type: string
```

### GET /sprints/{sprint_id}/candidates

Returns detailed candidate data for comparison views.

**Response Schema:**

```yaml
paths:
  /sprints/{sprint_id}/candidates:
    get:
      summary: Get all candidates for a sprint
      parameters:
        - name: sprint_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: phase
          in: query
          required: false
          schema:
            type: string
          description: Filter by phase name
      responses:
        '200':
          content:
            application/json:
              schema:
                type: object
                properties:
                  sprint_id:
                    type: string
                    format: uuid
                  candidates:
                    type: array
                    items:
                      $ref: '#/components/schemas/CandidateDetail'

  schemas:
    CandidateDetail:
      type: object
      properties:
        id:
          type: string
          format: uuid
        phase:
          type: string
        provider:
          type: string
        model_name:
          type: string
        output:
          type: string
          description: Truncated output (first 2000 chars)
        output_full_path:
          type: string
          description: Path to full output artifact
        tool_calls:
          type: array
          items:
            type: object
            properties:
              tool_name:
                type: string
              args:
                type: object
        metrics:
          type: object
          properties:
            duration_ms:
              type: integer
            tool_call_count:
              type: integer
            status:
              type: string
            token_usage:
              $ref: '#/components/schemas/TokenUsage'
        started_at:
          type: string
          format: date-time
        completed_at:
          type: string
          format: date-time
          nullable: true
        trace_id:
          type: string
          nullable: true
        trace_url:
          type: string
          nullable: true
        is_selected:
          type: boolean
          description: Whether this candidate was selected by judge
```

### GET /sprints/{sprint_id}/timeline

Returns event stream for timeline visualization.

**Response Schema:**

```yaml
paths:
  /sprints/{sprint_id}/timeline:
    get:
      summary: Get workflow timeline events
      parameters:
        - name: sprint_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: since_sequence
          in: query
          required: false
          schema:
            type: integer
          description: Only return events after this sequence number
      responses:
        '200':
          content:
            application/json:
              schema:
                type: object
                properties:
                  sprint_id:
                    type: string
                    format: uuid
                  total_duration_ms:
                    type: integer
                    nullable: true
                  events:
                    type: array
                    items:
                      $ref: '#/components/schemas/TimelineEvent'

  schemas:
    TimelineEvent:
      type: object
      properties:
        sequence:
          type: integer
        event_type:
          type: string
          enum:
            - sprint_started
            - sprint_activated
            - spec_exported
            - phase_started
            - candidates_generated
            - judge_decision
            - phase_completed
            - artifact_created
            - checkpoint_created
            - sprint_completed
        timestamp:
          type: string
          format: date-time
        state:
          type: string
          nullable: true
        phase:
          type: string
          nullable: true
        checkpoint_id:
          type: string
          nullable: true
        trace_id:
          type: string
          nullable: true
        trace_url:
          type: string
          nullable: true
        duration_ms:
          type: integer
          nullable: true
        metadata:
          type: object
          description: Event-specific metadata
```

### GET /sprints/{sprint_id}/artifacts

Returns list of generated artifacts.

**Response Schema:**

```yaml
paths:
  /sprints/{sprint_id}/artifacts:
    get:
      summary: List sprint artifacts
      responses:
        '200':
          content:
            application/json:
              schema:
                type: object
                properties:
                  sprint_id:
                    type: string
                    format: uuid
                  base_path:
                    type: string
                  artifacts:
                    type: array
                    items:
                      $ref: '#/components/schemas/Artifact'

  schemas:
    Artifact:
      type: object
      properties:
        path:
          type: string
          description: Relative path from sprint base directory
        type:
          type: string
          enum: [spec, code, plan, timeline, checkpoint, candidate_response, manifest]
        name:
          type: string
        size_bytes:
          type: integer
        created_at:
          type: string
          format: date-time
        mime_type:
          type: string
```

---

## WebSocket Event Design

### Event Type Hierarchy

```
sprint_event (base)
  |-- sprint_started
  |-- sprint_activated
  |-- sprint_completed
  |-- phase_update
  |     |-- phase_started
  |     |-- phase_completed
  |-- candidate_event
  |     |-- candidate_started
  |     |-- candidate_generated
  |     |-- candidate_failed
  |-- judge_decision
  |-- artifact_created
  |-- checkpoint_created
  |-- error
```

### Event Schemas

#### Base Event Structure

All events share this structure:

```typescript
interface SprintWebSocketEvent {
  type: string;
  sprint_id: string;
  timestamp: string;  // ISO 8601
  sequence: number;
}
```

#### phase_update

Emitted when phase status changes.

```typescript
interface PhaseUpdateEvent extends SprintWebSocketEvent {
  type: "phase_update";
  phase: string;
  status: "started" | "completed" | "failed";
  phase_data: {
    sequence: number;
    duration_ms?: number;
    model_config?: {
      openai_model: string;
      anthropic_model: string;
    };
    checkpoint_id?: string;
    trace_id?: string;
    trace_url?: string;
  };
}
```

#### candidate_generated

Emitted when a subagent completes (success or failure).

```typescript
interface CandidateGeneratedEvent extends SprintWebSocketEvent {
  type: "candidate_generated";
  phase: string;
  candidate: {
    provider: "openai" | "anthropic";
    model_name: string;
    status: "completed" | "failed";
    duration_ms: number;
    token_usage?: {
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
      estimated_cost_usd: number;
    };
    output_preview?: string;  // First 500 chars
    tool_call_count: number;
    trace_id?: string;
    trace_url?: string;
    error?: string;
  };
  candidates_complete: number;  // Count of completed candidates
  candidates_total: number;     // Total expected candidates
}
```

#### judge_decision

Emitted when judge selects a winner.

```typescript
interface JudgeDecisionEvent extends SprintWebSocketEvent {
  type: "judge_decision";
  phase: string;
  decision: {
    judge_model: string;
    judge_provider: string;
    winner: string;  // Provider name
    score: number;   // 0-1
    helpfulness_score?: number;
    correctness_score?: number;
    rationale: string;
    trace_id?: string;
    trace_url?: string;
  };
  candidates_evaluated: Array<{
    provider: string;
    model_name: string;
    was_selected: boolean;
  }>;
}
```

#### artifact_created

Emitted when a new artifact is generated.

```typescript
interface ArtifactCreatedEvent extends SprintWebSocketEvent {
  type: "artifact_created";
  artifact: {
    path: string;
    type: string;
    name: string;
    size_bytes: number;
  };
}
```

### WebSocket Room Strategy

```
Room naming: sprint:{sprint_id}
Example: sprint:550e8400-e29b-41d4-a716-446655440000
```

Clients subscribe to their sprint's room to receive relevant events only.

---

## Data Flow Architecture

### Sequence Diagram: Agent Execution to UI Update

```

    PhaseRunner         AgentTddService       WorkflowTracker      ConnectionManager      Frontend
         |                    |                     |                     |                   |
         |--execute phase---->|                     |                     |                   |
         |                    |--run subagents----->|                     |                   |
         |                    |   (parallel)        |                     |                   |
         |                    |                     |                     |                   |
         |                    |<--candidate result--|                     |                   |
         |                    |                     |                     |                   |
         |                    |--record_candidates->|                     |                   |
         |                    |                     |--save to disk       |                   |
         |                    |                     |                     |                   |
         |----emit WS event---------------------------------->|                              |
         |                    |                     |         |--broadcast to room---------->|
         |                    |                     |         |                   candidate_generated
         |                    |                     |                     |                   |
         |                    |--run judge--------->|                     |                   |
         |                    |                     |                     |                   |
         |                    |<--judge decision----|                     |                   |
         |                    |                     |                     |                   |
         |                    |--record_judge------>|                     |                   |
         |                    |                     |--save to disk       |                   |
         |                    |                     |                     |                   |
         |----emit WS event---------------------------------->|                              |
         |                    |                     |         |--broadcast to room---------->|
         |                    |                     |         |                   judge_decision
         |                    |                     |                     |                   |
         |                    |                     |                     |                   |
```

### Data Flow: REST API Read Path

```
Frontend                API Layer              Service Layer           File System
    |                       |                       |                       |
    |--GET /workflow------->|                       |                       |
    |                       |--get_workflow-------->|                       |
    |                       |                       |--read manifest.json-->|
    |                       |                       |<--manifest data-------|
    |                       |                       |--read timeline.json-->|
    |                       |                       |<--timeline data-------|
    |                       |                       |--read phases/*.json-->|
    |                       |                       |<--phase data----------|
    |                       |<--WorkflowState-------|                       |
    |<--JSON response-------|                       |                       |
```

### Data Flow: Real-Time WebSocket Path

```
1. PhaseRunner executes phase
2. AgentTddService runs subagents in parallel
3. On each candidate completion:
   a. WorkflowTracker.record_candidates() saves to disk
   b. PhaseRunner calls ConnectionManager.broadcast_to_room()
   c. Frontend receives candidate_generated event
   d. React component updates immediately
4. On judge completion:
   a. WorkflowTracker.record_judge_decision() saves to disk
   b. PhaseRunner calls ConnectionManager.broadcast_to_room()
   c. Frontend receives judge_decision event
   d. JudgeVisualization component shows winner
```

---

## Component Architecture

### Component Hierarchy

```
SprintsPage
  |-- SprintList (existing)
  |-- SprintDetail
  |     |-- SprintHeader
  |     |-- WorkflowPanel (new)
  |     |     |-- WorkflowProgress
  |     |     |-- PhaseList
  |     |     |     |-- PhaseCard
  |     |     |     |     |-- CandidateComparison
  |     |     |     |     |-- JudgeVisualization
  |     |     |     |     |-- TokenUsageChart
  |     |     |-- TimelineView
  |     |-- ArtifactBrowser (new)
  |     |     |-- ArtifactTree
  |     |     |-- ArtifactViewer
  |     |-- PlanningInterview (existing, enhanced)
  |           |-- InterviewProgress
  |           |-- QuestionList
  |           |-- TelemetryPanel
  |-- SprintBoard (existing)
```

### Component Specifications

#### WorkflowPanel

**Purpose:** Container for workflow visualization, manages WebSocket subscription.

**Props:**
```typescript
interface WorkflowPanelProps {
  sprintId: string;
  initialWorkflow?: WorkflowState;
}
```

**State:**
- `workflow: WorkflowState`
- `isConnected: boolean`
- `lastEventSequence: number`

**Behavior:**
1. On mount, subscribe to WebSocket room `sprint:{sprintId}`
2. Fetch initial workflow state via REST API
3. Process incoming WebSocket events to update state
4. Unsubscribe on unmount

---

#### CandidateComparison

**Purpose:** Side-by-side comparison of OpenAI vs Anthropic candidates.

**Props:**
```typescript
interface CandidateComparisonProps {
  phase: string;
  candidates: CandidateSummary[];
  judgeResult?: JudgeResult;
  showOutput?: boolean;
}
```

**Visual Design:**
```
+------------------------------------------+
|            Candidate Comparison          |
+-------------------+----------------------+
|      OpenAI       |      Anthropic       |
+-------------------+----------------------+
| gpt-4o            | claude-3-5-sonnet    |
| Status: Complete  | Status: Complete     |
| Duration: 2.3s    | Duration: 1.8s       |
| Tokens: 1,234     | Tokens: 1,456        |
| Cost: $0.02       | Cost: $0.03          |
+-------------------+----------------------+
|        [Logfire]  |        [Logfire]     |
+-------------------+----------------------+
|              SELECTED (by judge)         |
+------------------------------------------+
```

---

#### JudgeVisualization

**Purpose:** Display judge decision with score breakdown.

**Props:**
```typescript
interface JudgeVisualizationProps {
  judgeResult: JudgeResult;
  candidates: CandidateSummary[];
}
```

**Visual Design:**
```
+------------------------------------------+
|           Judge Decision                 |
+------------------------------------------+
| Model: gpt-4o (OpenAI)                   |
+------------------------------------------+
|                                          |
|   OpenAI  [=========>     ] 0.85        |
|   Anthrop [======>        ] 0.72        |
|                                          |
+------------------------------------------+
| Winner: OpenAI                           |
| Score: 0.85                              |
+------------------------------------------+
| Rationale:                               |
| "The OpenAI response was more complete   |
|  and included better error handling..."  |
+------------------------------------------+
|                            [Logfire]     |
+------------------------------------------+
```

---

#### TokenUsageChart

**Purpose:** Visualize token usage and estimated costs.

**Props:**
```typescript
interface TokenUsageChartProps {
  candidates: CandidateSummary[];
  aggregated?: boolean;  // Show totals across phases
}
```

**Visual Design:**
```
+------------------------------------------+
|           Token Usage                    |
+------------------------------------------+
|                                          |
|  Prompt    [==========] 12,345 tokens    |
|  Complete  [====]       4,567 tokens     |
|  Total     [==============] 16,912       |
|                                          |
+------------------------------------------+
| Estimated Cost: $0.45                    |
| By Provider:                             |
|   OpenAI:   $0.28 (62%)                  |
|   Anthropic: $0.17 (38%)                 |
+------------------------------------------+
```

---

#### TimelineView

**Purpose:** Chronological event stream with trace links.

**Props:**
```typescript
interface TimelineViewProps {
  events: TimelineEvent[];
  onEventClick?: (event: TimelineEvent) => void;
}
```

**Visual Design:**
```
+------------------------------------------+
|              Timeline                    |
+------------------------------------------+
| 10:23:45  sprint_started                 |
|     |     Sprint initialized              |
|     |                                     |
| 10:23:46  phase_started [discovery]      |
|     |     Models: gpt-4o, claude-3-5     |
|     |                                     |
| 10:23:52  candidate_generated            |
|     |     OpenAI completed (6.2s)        |
|     |     [Logfire]                       |
|     |                                     |
| 10:23:54  candidate_generated            |
|     |     Anthropic completed (8.1s)     |
|     |     [Logfire]                       |
|     |                                     |
| 10:23:55  judge_decision                 |
|     |     Winner: OpenAI (0.85)          |
|     |     [Logfire]                       |
|     |                                     |
| 10:23:56  phase_completed                |
|           Duration: 10.2s                 |
+------------------------------------------+
```

---

#### ArtifactBrowser

**Purpose:** Browse and view generated artifacts.

**Props:**
```typescript
interface ArtifactBrowserProps {
  sprintId: string;
  artifacts: Artifact[];
}
```

**Visual Design:**
```
+------------------------------------------+
|           Artifacts                      |
+------------------------------------------+
| > spec/                                  |
|   |-- spec.json                          |
|   |-- spec.md                            |
|   > questionnaire/                       |
|      |-- questionnaire.json              |
|      > candidates/                       |
|         > openai/                        |
|            |-- questions.json            |
|         > anthropic/                     |
|            |-- questions.json            |
| > phases/                                |
|   |-- 01_discovery.json                  |
|   |-- 02_coding_1.json                   |
| > candidates/                            |
|   > discovery/                           |
|      > openai/                           |
|         |-- response.json                |
|         |-- metadata.json                |
| > timeline.json                          |
| > manifest.json                          |
+------------------------------------------+
```

---

#### InterviewProgress (Enhancement to existing)

**Purpose:** Show dynamic question count progress.

**Props:**
```typescript
interface InterviewProgressProps {
  questionCount: number;  // 1-10
  answeredCount: number;
  maxQuestions: number;
}
```

**Visual Design:**
```
+------------------------------------------+
|        Interview Progress                |
+------------------------------------------+
| Questions: 7 of 10                       |
| [=======                   ] 70%         |
|                                          |
| Answered: 5 of 7                         |
| [==========                ] 71%         |
+------------------------------------------+
```

---

## Data Models

### Frontend TypeScript Types

```typescript
// New types to add to frontend/src/types/workflow.ts

export interface WorkflowState {
  sprint_id: string;
  spec_id: string | null;
  status: "planned" | "active" | "completed" | "failed";
  current_phase: string | null;
  total_duration_ms: number | null;
  phases: PhaseState[];
  planning: PlanningState;
  logfire_project_url: string | null;
}

export interface PhaseState {
  phase: string;
  sequence: number;
  status: "pending" | "in_progress" | "completed" | "failed" | "skipped";
  start_time: string | null;
  end_time: string | null;
  duration_ms: number | null;
  model_config: {
    openai_model: string;
    anthropic_model: string;
  };
  candidates: CandidateSummary[];
  judge_result: JudgeResult | null;
  checkpoint_before: string | null;
  checkpoint_after: string | null;
  trace_id: string | null;
  trace_url: string | null;
}

export interface CandidateSummary {
  provider: "openai" | "anthropic" | "openrouter";
  model_name: string;
  status: "pending" | "running" | "completed" | "failed";
  duration_ms: number | null;
  token_usage: TokenUsage | null;
  trace_id: string | null;
  trace_url: string | null;
  error: string | null;
}

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
}

export interface JudgeResult {
  model_name: string;
  provider: string;
  winner: string;
  score: number;
  helpfulness_score: number | null;
  correctness_score: number | null;
  rationale: string;
  trace_id: string | null;
  trace_url: string | null;
}

export interface TimelineEvent {
  sequence: number;
  event_type: string;
  timestamp: string;
  state: string | null;
  phase: string | null;
  checkpoint_id: string | null;
  trace_id: string | null;
  trace_url: string | null;
  duration_ms: number | null;
  metadata: Record<string, unknown>;
}

export interface Artifact {
  path: string;
  type: "spec" | "code" | "plan" | "timeline" | "checkpoint" | "candidate_response" | "manifest";
  name: string;
  size_bytes: number;
  created_at: string;
  mime_type: string;
}
```

### Backend Pydantic Schemas

```python
# New schemas to add to backend/app/schemas/workflow.py

from pydantic import BaseModel, Field
from typing import Literal
from uuid import UUID
from datetime import datetime

class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float

class CandidateSummary(BaseModel):
    provider: Literal["openai", "anthropic", "openrouter"]
    model_name: str
    status: Literal["pending", "running", "completed", "failed"]
    duration_ms: int | None = None
    token_usage: TokenUsage | None = None
    trace_id: str | None = None
    trace_url: str | None = None
    error: str | None = None

class JudgeResult(BaseModel):
    model_name: str
    provider: str
    winner: str
    score: float = Field(ge=0, le=1)
    helpfulness_score: float | None = None
    correctness_score: float | None = None
    rationale: str
    trace_id: str | None = None
    trace_url: str | None = None

class PhaseState(BaseModel):
    phase: str
    sequence: int
    status: Literal["pending", "in_progress", "completed", "failed", "skipped"]
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_ms: int | None = None
    model_config: dict = Field(default_factory=dict)
    candidates: list[CandidateSummary] = Field(default_factory=list)
    judge_result: JudgeResult | None = None
    checkpoint_before: str | None = None
    checkpoint_after: str | None = None
    trace_id: str | None = None
    trace_url: str | None = None

class PlanningState(BaseModel):
    status: Literal["idle", "needs_answers", "answered"]
    question_count: int = Field(ge=1, le=10)
    questions: list[dict] = Field(default_factory=list)
    answers: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

class WorkflowState(BaseModel):
    sprint_id: UUID
    spec_id: UUID | None = None
    status: Literal["planned", "active", "completed", "failed"]
    current_phase: str | None = None
    total_duration_ms: int | None = None
    phases: list[PhaseState] = Field(default_factory=list)
    planning: PlanningState | None = None
    logfire_project_url: str | None = None

class TimelineEvent(BaseModel):
    sequence: int
    event_type: str
    timestamp: datetime
    state: str | None = None
    phase: str | None = None
    checkpoint_id: str | None = None
    trace_id: str | None = None
    trace_url: str | None = None
    duration_ms: int | None = None
    metadata: dict = Field(default_factory=dict)

class Artifact(BaseModel):
    path: str
    type: Literal["spec", "code", "plan", "timeline", "checkpoint", "candidate_response", "manifest"]
    name: str
    size_bytes: int
    created_at: datetime
    mime_type: str
```

---

## Performance Considerations

### REST API

| Concern | Mitigation |
|---------|------------|
| Large timeline files | Pagination via `since_sequence` parameter |
| Artifact file reads | Stream large files, cache manifests |
| Multiple file reads | Aggregate data in memory, single response |

### WebSocket

| Concern | Mitigation |
|---------|------------|
| Event flooding | Throttle events (max 10/second per room) |
| Connection limits | Room-based isolation, cleanup stale connections |
| Large payloads | Truncate output previews (500 chars) |

### Frontend

| Concern | Mitigation |
|---------|------------|
| Re-renders | Use React.memo, useMemo for computed data |
| Large state | Split workflow state by section |
| Stale data | Sequence-based reconciliation |

---

## Architecture Decision Records

### ADR-001: REST API for Workflow Data

**Status:** Proposed

**Context:**
The frontend needs to display comprehensive workflow data including phases, candidates, and timeline. Options considered:
1. REST endpoints for each data type
2. GraphQL for flexible queries
3. Server-Sent Events for streaming

**Decision:**
Use REST endpoints with structured responses. The workflow data structure is well-defined and predictable.

**Consequences:**
- Multiple endpoints provide separation of concerns
- Caching is straightforward with HTTP semantics
- No GraphQL learning curve for team
- May require multiple requests for complete view

**Alternatives Considered:**
- GraphQL: More flexible but adds complexity
- SSE: Good for streaming but REST + WebSocket covers needs

---

### ADR-002: WebSocket Room-Based Broadcasting

**Status:** Proposed

**Context:**
Real-time updates need to reach relevant clients only. Options:
1. Global broadcast to all clients
2. Room-based broadcasting by sprint ID
3. Individual socket targeting

**Decision:**
Use room-based broadcasting with room name `sprint:{sprint_id}`.

**Consequences:**
- Clients only receive events for sprints they're viewing
- Reduced bandwidth and processing
- Simple room management with existing ConnectionManager
- Frontend must manage room subscription lifecycle

---

### ADR-003: File-Based Workflow Storage

**Status:** Accepted (existing design)

**Context:**
Workflow data is currently stored on filesystem by WorkflowTracker. Options for API:
1. Read directly from files
2. Mirror data to database
3. Hybrid approach

**Decision:**
Continue using filesystem as source of truth, read directly in API layer.

**Consequences:**
- No database migrations required
- Artifacts remain accessible for debugging
- File I/O may be slower than DB queries
- Consider caching manifest/timeline in memory

---

### ADR-004: Truncated Output in WebSocket Events

**Status:** Proposed

**Context:**
Candidate outputs can be large (10KB+). Sending full output over WebSocket:
- Increases bandwidth
- Slows down updates
- May not be needed for real-time display

**Decision:**
WebSocket events include `output_preview` (first 500 characters). Full output available via REST API.

**Consequences:**
- Faster real-time updates
- Frontend can fetch full output on demand
- Users see preview immediately, details on request

---

### ADR-005: Component State Management

**Status:** Proposed

**Context:**
WorkflowPanel needs to manage complex state from REST + WebSocket. Options:
1. Local useState/useReducer
2. Context API
3. External state management (Zustand/Redux)

**Decision:**
Use local state with useReducer for workflow state, WebSocket events trigger dispatch.

**Consequences:**
- No additional dependencies
- State isolated to workflow components
- Reducer pattern handles event reconciliation cleanly
- May revisit if state sharing needs grow

---

## Related Skills

The following installed skills provide implementation guidance:

- `skills/websocket-realtime` - For WebSocket patterns and real-time updates
- `skills/nextjs-shadcn` - For UI component implementation
- `skills/pytest-testing` - For backend API testing patterns

Read with: `cat skills/<skill-name>/SKILL.md`

---

## Next Steps

1. **Backend Implementation**
   - Create `/backend/app/api/routes/v1/workflow.py` with new endpoints
   - Create `/backend/app/schemas/workflow.py` with Pydantic models
   - Create `/backend/app/services/workflow.py` for data aggregation
   - Enhance `PhaseRunner` to emit detailed WebSocket events

2. **Frontend Implementation**
   - Create `/frontend/src/types/workflow.ts`
   - Create `/frontend/src/hooks/use-sprint-workflow.ts`
   - Create components in `/frontend/src/components/workflow/`
   - Integrate WorkflowPanel into SprintsPage

3. **Testing**
   - Integration tests for new API endpoints
   - WebSocket event tests
   - Component tests with mock data

---

## Appendix: File Locations

### Backend Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/api/routes/v1/workflow.py` | Create | New REST endpoints |
| `backend/app/schemas/workflow.py` | Create | Pydantic models |
| `backend/app/services/workflow.py` | Create | Data aggregation service |
| `backend/app/runners/phase_runner.py` | Modify | Enhanced WebSocket events |
| `backend/app/api/routes/v1/__init__.py` | Modify | Register workflow router |

### Frontend Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/types/workflow.ts` | Create | TypeScript types |
| `frontend/src/hooks/use-sprint-workflow.ts` | Create | WebSocket + REST hook |
| `frontend/src/components/workflow/WorkflowPanel.tsx` | Create | Container component |
| `frontend/src/components/workflow/CandidateComparison.tsx` | Create | Side-by-side view |
| `frontend/src/components/workflow/JudgeVisualization.tsx` | Create | Judge decision display |
| `frontend/src/components/workflow/TokenUsageChart.tsx` | Create | Token metrics |
| `frontend/src/components/workflow/TimelineView.tsx` | Create | Event timeline |
| `frontend/src/components/workflow/ArtifactBrowser.tsx` | Create | File browser |
| `frontend/src/components/workflow/index.ts` | Create | Barrel export |
| `frontend/src/app/[locale]/(dashboard)/sprints/page.tsx` | Modify | Integrate WorkflowPanel |
