# Sprints

Sprint planning and execution tracking is handled by a dedicated API and a Sprint board in the
Next.js dashboard.

## Requirements

The sprint workflow must satisfy these requirements:

### Functional Requirements

1. **Sprint Interview**: User initiates a planning interview with a prompt
2. **Question Answering**: User answers generated clarifying questions
3. **Sprint Creation**: User provides sprint name, dates, and clicks "Create Sprint"
4. **Automated Execution**: Code is built and validated automatically (PhaseRunner)
5. **Completion**: When code is complete and executable, sprint status becomes COMPLETED

### AI Execution Requirements

At each AI interaction step:

1. **Dual-Provider Execution**: Same prompt sent to both OpenAI and Anthropic SDKs
2. **Response Storage**: Each provider's response stored with full metadata
3. **LLM-as-Judge**: A judge model selects the best response
4. **Model Tracking**: Store which model was used for each AI call

### Telemetry Requirements (Per AI Call)

| Data Point | Storage Location | Description |
|------------|------------------|-------------|
| Provider | `AgentCandidate.provider` | "openai" or "anthropic" |
| Model Name | `AgentCandidate.model_name` | Full model identifier |
| Tool Calls | `AgentCandidate.tool_calls` | Serialized tool invocations |
| Duration | `AgentCandidate.metrics.duration_ms` | Execution time |
| Trace ID | `AgentCandidate.trace_id` | Logfire trace link |
| Judge Decision | `AgentDecision.candidate_id` | Which response was selected |
| Judge Rationale | `AgentDecision.rationale` | Why it was selected |
| Judge Model | `AgentDecision.model_name` | Judge model used |

### SDK Requirements

All AI interactions use **pure API SDK calls** (no web components):

- **OpenAI**: `pydantic_ai.models.openai.OpenAIResponsesModel`
- **Anthropic**: `pydantic_ai.models.anthropic.AnthropicModel`

The `agent_browser` tool (if enabled) uses CLI subprocess, NOT browser automation.

---

## End-to-End Workflow (Idea → Sprint)

1. Enter a sprint prompt in the Sprint planning interview.
   - Expectation: prompt describes the outcome you want by the end of the sprint.
   - System action: starts the Ralph planning interview and generates clarifying questions.

2. Review the generated questions and provide answers.
   - Expectation: all questions must be answered before the sprint can be created.
   - System action: stores answers in the linked spec (`artifacts.planning.answers`).

3. Create the sprint after answers are saved.
   - Expectation: sprint name is required; goal is recommended.
   - System action: sprint is created with `spec_id` pointing to the planning spec.

4. Track the sprint in the board and add items.
   - Expectation: sprint focus shows status, dates, items, and planning telemetry.
   - System action: items are added to the sprint and move through status columns.

## Planning Interview Expectations

- The planning interview runs before sprint creation and must succeed.
- Answers are validated for non-empty input.
- If the interview fails to produce questions, sprint creation is blocked.

### Dynamic Question Generation

The AI generates questions **dynamically based on complexity**, not a hardcoded number:

| Requirement | Behavior |
|-------------|----------|
| Simple tasks | 1-3 questions (e.g., "print hello world") |
| Standard tasks | 3-5 questions (typical features) |
| Complex tasks | 5-10 questions (integrations, architecture) |
| Maximum limit | 10 questions (configurable via `max_questions`) |

**Key Principle**: The AI keeps asking questions until it has gathered enough information
to create a solution with **NO AMBIGUITY**. It stops early if requirements are already clear.

The system prompt instructs the AI to:
1. Focus on JTBD (Jobs to Be Done), scope boundaries, constraints, edge cases
2. Ask questions until the implementation path is unambiguous
3. Stop when confident - don't ask unnecessary questions for simple tasks

## Model-as-Judge (Dual-Subagent Planning)

By default, planning uses a dual-subagent workflow:

- **OpenAI agent** uses `OPENAI_MODEL`
- **Anthropic agent** uses `ANTHROPIC_MODEL`
- **Judge** uses `JUDGE_MODEL` (must be an OpenAI responses model)

The judge scores helpfulness + correctness and selects the best candidate. The
selected provider is stored in `artifacts.planning.metadata.selected_candidate`
and shown in the UI.

Configuration:

- `DUAL_SUBAGENT_ENABLED=true` (default)
- `OPENAI_MODEL=openai-responses:gpt-5.2-codex` (example)
- `ANTHROPIC_MODEL=anthropic:claude-opus-4-5-20251101` (example)
- `JUDGE_MODEL=openai-responses:gpt-5.2-codex` (required in dual-subagent mode)

## Telemetry and Logfire

Planning telemetry is recorded in `artifacts.planning.metadata` and displayed in
two places:

- Sprint planning interview panel (current interview)
- Sprint Focus panel (persisted sprint history, from the linked spec)

Metadata includes:

- `candidates` with `provider`, `model_name`, `trace_id`, and `trace_url`
- `judge` with `model_name`, `trace_id`, `trace_url`, and scoring rationale
- `selected_candidate` with the chosen provider/model

To enable clickable Logfire links in the UI:

- Set `LOGFIRE_TRACE_URL_TEMPLATE` in `backend/.env` with `{trace_id}` placeholder.
- The backend emits `trace_url` when the template is set.

Logfire setup details are in `backend/docs/observability.md`.

## Status Values

- Sprint status: `planned`, `active`, `completed`
- Sprint item status: `todo`, `in_progress`, `blocked`, `done`
- Priority: `1` (high), `2` (medium), `3` (low)
- Optional `spec_id` links a sprint to its planning interview/spec.

## Automated Execution (PhaseRunner)

When a sprint is created, the `PhaseRunner` background task executes automatically:

### Phase 1: Discovery
- **Input**: Sprint goal
- **Action**: Analyze requirements and create `implementation_plan.md`
- **AI Calls**: Dual-provider (OpenAI + Anthropic) → Judge selects best plan
- **Output**: `workspace_ref` directory with implementation plan

### Phase 2: Coding (Retries up to 3x)
- **Input**: Implementation plan
- **Action**: Write code files using `fs_write_file` tool
- **AI Calls**: Dual-provider → Judge selects best implementation
- **Output**: Code files in workspace (e.g., `hello.py`)

### Phase 3: Verification (Retries up to 3x)
- **Input**: Code files
- **Action**: Run tests using `run_tests` tool, verify execution
- **AI Calls**: Dual-provider → Judge selects best verification result
- **Evaluators**: Deterministic evaluators (Ruff, pytest, type check) validate output
- **Output**: `VERIFICATION_SUCCESS` or `VERIFICATION_FAILURE`

### Evaluator-Optimizer Integration

Each phase uses the **Evaluator-Optimizer pattern** for structured validation:

1. **Evaluators Run** after phase completion:
   - RuffLintEvaluator (global, all phases)
   - PytestEvaluator (verification, coding phases)
   - TypeCheckEvaluator (coding phase)

2. **FeedbackMemory** tracks retry history:
   - Attempt 1: Original task only
   - Attempt 2: Task + previous feedback
   - Attempt 3: Task + full history + detailed analysis

3. **Pass/Retry Decision**:
   - All evaluators pass → Proceed to next phase
   - Any evaluator fails → Retry with accumulated feedback
   - 3 failures → Escalate to human review

See `backend/app/runners/evaluators/` for implementation.

### Completion Criteria
- Sprint status → `COMPLETED` when `VERIFICATION_SUCCESS` is found
- Code must be in local filesystem and executable
- All phases must complete successfully

### Database Records Created

| Table | Per Phase | Data |
|-------|-----------|------|
| `agent_runs` | 1 | Run metadata, workspace_ref |
| `agent_candidates` | 2 | OpenAI + Anthropic responses |
| `agent_decisions` | 1 | Judge selection |
| `agent_checkpoints` | 3+ | start, candidate:*, decision |

### File Artifacts Created

```
AUTOCODE_ARTIFACTS_DIR/{workspace_ref}/
├── implementation_plan.md    (Phase 1: Discovery)
├── hello.py                  (Phase 2: Coding)
└── test_hello.py             (Phase 3: Verification, if needed)
```

## API Endpoints

Sprints:
- `GET /api/v1/sprints` (optional `status` query param)
- `POST /api/v1/sprints`
- `GET /api/v1/sprints/{sprint_id}`
- `PATCH /api/v1/sprints/{sprint_id}`
- `DELETE /api/v1/sprints/{sprint_id}`

Sprint items:
- `GET /api/v1/sprints/{sprint_id}/items`
- `POST /api/v1/sprints/{sprint_id}/items`
- `PATCH /api/v1/sprints/{sprint_id}/items/{item_id}`
- `DELETE /api/v1/sprints/{sprint_id}/items/{item_id}`

## Planning Interview

Sprint prompts should run through the Ralph planning interview before creating
the sprint. Use the spec planning endpoints to generate questions and capture
answers, then attach the resulting `spec_id` when creating the sprint.

## UI

- Sprint board: `frontend/src/app/[locale]/(dashboard)/sprints/page.tsx`
- Kanban placeholder (optional): `frontend/src/app/[locale]/(dashboard)/kanban/page.tsx`
