# ADR-002: Self-Diagnostic Architecture

## Status
**Proposed** (2026-01-22)

## Context

The application needs enhanced observability and self-healing capabilities including:
- Development debugging with dev3000
- Enhanced Logfire/Sentry spans for production monitoring
- Circuit breakers for external API resilience
- Error boundaries in the frontend

The current state has:
- Basic Logfire instrumentation (`/backend/app/core/logfire_setup.py`)
- Sentry DSN configuration (`/backend/app/core/config.py:157`)
- Prometheus metrics (`/backend/app/main.py:185-205`)
- No circuit breakers for external APIs (AI providers, etc.)
- No structured error boundaries in frontend

## Decision

Implement a **Layered Self-Diagnostic Pipeline** with the following components:

### System Architecture (ASCII)

```
+-----------------------------------------------------------------------------------+
|                                 FRONTEND (Next.js)                                |
+-----------------------------------------------------------------------------------+
|  +-------------+   +----------------+   +------------------+   +---------------+  |
|  | Error       |   | React Query    |   | Toast/Snackbar   |   | DevTools     |  |
|  | Boundaries  |-->| Error States   |-->| User Feedback    |   | (dev only)   |  |
|  +-------------+   +----------------+   +------------------+   +---------------+  |
|         |                  |                     |                     |          |
|         v                  v                     v                     v          |
|  +--------------------------------------------------------------------------+    |
|  |                    Error Reporting Service (Sentry Browser SDK)          |    |
|  +--------------------------------------------------------------------------+    |
+-----------------------------------------------------------------------------------+
                                        |
                                        | HTTP/WebSocket
                                        v
+-----------------------------------------------------------------------------------+
|                              BACKEND (FastAPI)                                     |
+-----------------------------------------------------------------------------------+
|                                                                                    |
|  +--------------------+   +----------------------+   +------------------------+   |
|  | Request Middleware |   | Exception Handlers   |   | Background Task        |   |
|  | - Request ID       |-->| - Domain Exceptions  |   | Error Handling         |   |
|  | - Timing           |   | - Validation Errors  |   | - Retry Logic          |   |
|  +--------------------+   +----------------------+   +------------------------+   |
|         |                         |                           |                   |
|         v                         v                           v                   |
|  +--------------------------------------------------------------------------+    |
|  |                         OBSERVABILITY LAYER                               |    |
|  |  +---------------+  +--------------+  +-------------+  +---------------+  |   |
|  |  | Logfire       |  | Sentry       |  | Prometheus  |  | dev3000       |  |   |
|  |  | (Traces/Logs) |  | (Errors)     |  | (Metrics)   |  | (Dev Debug)   |  |   |
|  |  +---------------+  +--------------+  +-------------+  +---------------+  |   |
|  +--------------------------------------------------------------------------+    |
|         |                         |                           |                   |
|         v                         v                           v                   |
|  +--------------------------------------------------------------------------+    |
|  |                         SERVICE LAYER                                     |    |
|  |  +------------------+  +------------------+  +-------------------------+  |   |
|  |  | SprintService    |  | AgentService     |  | ExternalAPIService      |  |   |
|  |  | - Business Logic |  | - AI Orchestrat. |  | - Circuit Breaker       |  |   |
|  |  +------------------+  +------------------+  +-------------------------+  |   |
|  +--------------------------------------------------------------------------+    |
|         |                         |                           |                   |
|         v                         v                           v                   |
|  +--------------------------------------------------------------------------+    |
|  |                    EXTERNAL API RESILIENCE LAYER                          |    |
|  |  +------------------------------------------------------------------+    |   |
|  |  |              Circuit Breaker Manager (circuitbreaker)             |    |   |
|  |  |  +------------+  +------------+  +------------+  +------------+  |    |   |
|  |  |  | OpenAI     |  | Anthropic  |  | OpenRouter |  | Browser    |  |    |   |
|  |  |  | Breaker    |  | Breaker    |  | Breaker    |  | Breaker    |  |    |   |
|  |  |  +------------+  +------------+  +------------+  +------------+  |    |   |
|  |  +------------------------------------------------------------------+    |   |
|  +--------------------------------------------------------------------------+    |
|                                                                                    |
+-----------------------------------------------------------------------------------+
                |                           |                           |
                v                           v                           v
        +-------------+           +------------------+         +-----------------+
        | PostgreSQL  |           | Redis            |         | External APIs   |
        | (Primary)   |           | (Cache/Queue)    |         | (AI Providers)  |
        +-------------+           +------------------+         +-----------------+
```

### Component Details

#### 1. Circuit Breaker Layer

```
+------------------------------------------------------------------+
|                    Circuit Breaker State Machine                  |
+------------------------------------------------------------------+
|                                                                   |
|     CLOSED                  OPEN                   HALF-OPEN      |
|   +---------+            +--------+              +----------+     |
|   | Normal  |  failures  |  Fail  |   timeout   |   Test   |     |
|   | Traffic |----------->|  Fast  |------------>|  Traffic |     |
|   |         |            |        |             |          |     |
|   |         |  success   |        |    fail     |          |     |
|   |         |<-----------|        |<------------|          |     |
|   +---------+            +--------+              +----------+     |
|                                                                   |
|   Configuration:                                                  |
|   - failure_threshold: 5 failures                                 |
|   - recovery_timeout: 30 seconds                                  |
|   - expected_exceptions: [APIConnectionError, Timeout]            |
+------------------------------------------------------------------+
```

#### 2. Logfire Span Hierarchy

```
+------------------------------------------------------------------+
|                    Trace: Sprint Phase Execution                  |
+------------------------------------------------------------------+
|                                                                   |
| [HTTP Request] POST /api/v1/sprints                               |
|     |                                                             |
|     +-- [Span] SprintService.create                               |
|         |   - sprint_id: uuid                                     |
|         |   - spec_id: uuid                                       |
|         |                                                         |
|         +-- [Span] SprintRepo.create                              |
|         |       - db_operation: INSERT                            |
|         |                                                         |
|         +-- [Span] PhaseRunner.start (background)                 |
|                 |                                                 |
|                 +-- [Span] phase=requirements                     |
|                 |       - status: in_progress -> completed        |
|                 |                                                 |
|                 +-- [Span] phase=design                           |
|                 |       +-- [Span] AI.call (circuit_breaker)      |
|                 |               - provider: openai                |
|                 |               - model: gpt-4o                   |
|                 |               - tokens: 1234                    |
|                 |                                                 |
|                 +-- [Span] phase=implementation                   |
|                         +-- [Span] AgentBrowser.execute           |
|                                 - url: http://localhost:3000      |
|                                 - action: screenshot              |
|                                                                   |
+------------------------------------------------------------------+
```

#### 3. Error Boundary Hierarchy (Frontend)

```
+------------------------------------------------------------------+
|                    Frontend Error Boundary Tree                   |
+------------------------------------------------------------------+
|                                                                   |
| <RootErrorBoundary>  [Catches: All unhandled errors]              |
|     |                [Shows: Full-page error with reload]         |
|     |                                                             |
|     +-- <Layout>                                                  |
|         |                                                         |
|         +-- <RouteErrorBoundary>  [Catches: Route-level errors]   |
|             |                     [Shows: Page-level fallback]    |
|             |                                                     |
|             +-- <SprintDashboard>                                 |
|                 |                                                 |
|                 +-- <WidgetErrorBoundary>  [Catches: Widget errs] |
|                     |                      [Shows: Widget retry]  |
|                     |                                             |
|                     +-- <SprintList />                            |
|                     +-- <PhaseStatus />                           |
|                     +-- <AgentOutput />                           |
|                                                                   |
+------------------------------------------------------------------+
```

### Configuration Schema

```yaml
# .env additions for self-diagnostic features

# === Dev3000 (Development Only) ===
DEV3000_ENABLED=true
DEV3000_PORT=3001
DEV3000_AUTO_OPEN_BROWSER=true

# === Circuit Breaker Configuration ===
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=30
CIRCUIT_BREAKER_EXPECTED_EXCEPTIONS="APIConnectionError,TimeoutError,RateLimitError"

# === Enhanced Logfire Spans ===
LOGFIRE_TRACE_AI_CALLS=true
LOGFIRE_TRACE_DB_QUERIES=true
LOGFIRE_TRACE_EXTERNAL_HTTP=true
LOGFIRE_SAMPLE_RATE=1.0  # 1.0 = trace everything

# === Sentry Enhanced ===
SENTRY_TRACES_SAMPLE_RATE=0.2  # 20% of transactions
SENTRY_PROFILES_SAMPLE_RATE=0.1  # 10% of profiled transactions
SENTRY_SEND_DEFAULT_PII=false
```

## Consequences

### Positive

1. **Faster Debugging**: dev3000 provides real-time inspection during development
2. **Production Visibility**: Enhanced Logfire spans show full request lifecycle
3. **Resilience**: Circuit breakers prevent cascade failures from external APIs
4. **User Experience**: Error boundaries show graceful degradation, not blank screens
5. **Correlation**: Request IDs tie frontend errors to backend traces

### Negative

1. **Complexity**: Multiple observability tools require maintenance
2. **Performance Overhead**: Tracing adds latency (mitigated by sampling)
3. **Cost**: More logs/traces = higher observability costs
4. **Learning Curve**: Team needs to understand circuit breaker patterns

### Neutral

1. **No API Contract Changes**: All changes are internal implementation
2. **Backwards Compatible**: Existing code continues to work
3. **Incremental Adoption**: Components can be enabled independently

## Implementation Roadmap

### Phase 1: Circuit Breakers (Priority: High)
1. Add `circuitbreaker` package to requirements
2. Create `/backend/app/core/circuit_breaker.py`
3. Wrap AI provider calls in circuit breakers
4. Add health endpoint reporting circuit states

### Phase 2: Enhanced Logfire Spans (Priority: High)
1. Add custom spans to PhaseRunner
2. Add AI call instrumentation with token tracking
3. Add database query span annotations
4. Configure structured attributes for filtering

### Phase 3: Frontend Error Boundaries (Priority: Medium)
1. Create `ErrorBoundary` component hierarchy
2. Integrate with Sentry browser SDK
3. Add toast notifications for recoverable errors
4. Add retry logic to React Query mutations

### Phase 4: dev3000 Integration (Priority: Low)
1. Add dev3000 as dev dependency
2. Create startup hook in development mode
3. Configure dashboard panels
4. Document usage for team

## Related Skills

The following installed skills provide implementation guidance:

- `skills/openlit-observability/` - For LLM observability patterns
- `skills/code-auditor/` - For reviewing observability implementation
- `skills/pytest-testing/` - For testing circuit breakers

Read with: `cat skills/<skill-name>/SKILL.md`
