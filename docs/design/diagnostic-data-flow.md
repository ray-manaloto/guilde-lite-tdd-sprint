# Diagnostic Data Flow Architecture

## Overview

This document describes the data flow for the self-diagnostic capabilities, including error event capture, pattern detection, AI-powered categorization, and feedback collection.

## Data Flow Diagram

```
                                    +------------------+
                                    |   User/Client    |
                                    +--------+---------+
                                             |
                         +-------------------+-------------------+
                         |                   |                   |
                         v                   v                   v
                  +------+------+     +------+------+     +------+------+
                  |  API Layer  |     |   Frontend  |     |  Feedback   |
                  |  (FastAPI)  |     |  (Next.js)  |     |    Form     |
                  +------+------+     +------+------+     +------+------+
                         |                   |                   |
                         |                   |                   |
    +--------------------+-------------------+-------------------+----------+
    |                                                                       |
    |                        Exception Handler / Middleware                 |
    |                                                                       |
    +---+---------------------------+---------------------------+-----------+
        |                           |                           |
        v                           v                           v
+-------+-------+          +--------+-------+          +--------+-------+
|  Error Event  |          |    Logfire     |          |  User Feedback |
|   Capture     |          |  Enrichment    |          |    Capture     |
+-------+-------+          +--------+-------+          +--------+-------+
        |                           |                           |
        |     +---------------------+                           |
        |     |                                                 |
        v     v                                                 v
+-------+-----+-------+                              +----------+---------+
|                     |                              |                    |
|    PostgreSQL       |                              |    PostgreSQL      |
|    (error_events)   |                              |   (user_feedback)  |
|                     |                              |                    |
+----------+----------+                              +----------+---------+
           |                                                    |
           |                                                    |
           v                                                    |
+----------+----------+                                         |
|                     |                                         |
|  Pattern Detection  |<----------------------------------------+
|     Service         |
|                     |
+----------+----------+
           |
           |
           v
+----------+----------+
|                     |
|    PostgreSQL       |
|  (error_patterns)   |
|                     |
+----------+----------+
           |
           |
           v
+----------+----------+
|                     |
|   AI Categorization |
|     (PydanticAI)    |
|                     |
+----------+----------+
           |
           |
           v
+----------+----------+              +--------------------+
|                     |              |                    |
|  Diagnostic Report  +------------->|   Logfire Cloud    |
|     Generation      |              |   (Observability)  |
|                     |              |                    |
+----------+----------+              +--------------------+
           |
           |
           v
+----------+----------+
|                     |
|    PostgreSQL       |
|(diagnostic_reports) |
|                     |
+---------------------+
```

## Component Descriptions

### 1. Error Event Capture

**Source:** Exception handlers, middleware, agent tools

**Process:**
1. Exception occurs in any layer (API, Service, Agent, Tool)
2. Exception handler intercepts the error
3. ErrorEvent schema is populated with:
   - Error type and message
   - Stack trace with code context
   - Request/agent context
   - Telemetry correlation IDs

**Output:** `ErrorEvent` record in PostgreSQL

```python
# Example capture flow
try:
    result = await service.process()
except Exception as exc:
    error_event = ErrorEventCreate(
        error_type=type(exc).__name__,
        message=str(exc),
        stack_trace=extract_stack_frames(exc),
        context=ErrorContext(
            request_id=request.state.request_id,
            agent_run_id=current_run_id,
        ),
        trace_id=get_current_trace_id(),
    )
    await diagnostic_service.capture_error(error_event)
    raise
```

### 2. Logfire Enrichment

**Purpose:** Enrich Logfire spans with diagnostic metadata for observability

**Process:**
1. Error is captured
2. LogfireErrorEnrichment schema is populated
3. Attributes are attached to the current span

```python
# Enrichment example
enrichment = LogfireErrorEnrichment(
    error_type=error_event.error_type,
    error_message=error_event.message,
    error_category=error_event.category,
    error_severity=error_event.severity,
    pattern_fingerprint=matched_pattern.fingerprint if matched_pattern else None,
)

with logfire.span("error_captured") as span:
    span.set_attributes(enrichment.to_logfire_attributes())
```

### 3. Pattern Detection

**Purpose:** Identify recurring errors for proactive debugging

**Algorithm:**
1. Compute error fingerprint (hash of type + normalized message + source)
2. Query for existing pattern with matching fingerprint
3. If exists: increment occurrence counter
4. If not exists and threshold met: create new pattern

**Fingerprint Computation:**
```python
def compute_fingerprint(error_type: str, message: str, source: str) -> str:
    # Normalize message
    normalized = re.sub(r'\b[0-9a-fA-F-]{36}\b', '<UUID>', message)
    normalized = re.sub(r'\b\d+\b', '<NUM>', normalized)

    # Create fingerprint
    data = f"{error_type}|{normalized[:200]}|{source}"
    return hashlib.sha256(data.encode()).hexdigest()
```

**Pattern Thresholds:**
| Condition | Action |
|-----------|--------|
| 3+ occurrences in 24h | Create pattern |
| 10+ occurrences in 1h | Escalate severity |
| 100+ occurrences | Alert + auto-report |

### 4. AI Categorization

**Purpose:** Automatically classify errors and suggest fixes

**Process:**
1. New pattern detected
2. AI agent analyzes:
   - Error type and message
   - Stack trace
   - Similar historical patterns
   - Related documentation
3. AI generates:
   - Category classification
   - Root cause analysis
   - Fix suggestions
   - Confidence score

**AI Prompt Structure:**
```
Analyze this error pattern:

Error Type: {error_type}
Message: {message}
Stack Trace: {stack_trace}
Occurrence Count: {count}
Affected Components: {affected_sources}

Similar Past Patterns:
{similar_patterns}

Provide:
1. Most likely category (from: database, network, llm_api, etc.)
2. Probable root cause
3. Suggested fixes (prioritized list)
4. Confidence score (0-1)
```

### 5. Diagnostic Report Generation

**Triggers:**
- Manual request by developer
- Automatic on critical pattern detection
- Scheduled (daily/weekly health reports)

**Report Contents:**
```markdown
# Diagnostic Report: {title}

## Executive Summary
{ai_generated_summary}

## System Health
- API Error Rate: {rate}%
- Agent Success Rate: {rate}%
- Active Patterns: {count}

## Top Issues
1. {pattern_name} - {occurrences} occurrences
   - Root Cause: {ai_root_cause}
   - Suggested Fix: {ai_fix}

## Recommendations
1. {recommendation}
2. {recommendation}

## Immediate Actions Required
- {action}
```

### 6. User Feedback Collection

**Integration Points:**
- Error dialogs ("Report this issue")
- Feedback button in UI
- Post-task satisfaction surveys

**Correlation:**
- Auto-attach current error_id if error dialog
- Auto-attach agent_run_id if in agent context
- Auto-attach sprint_id if in sprint context

**Processing Pipeline:**
1. Feedback submitted
2. Auto-tag based on content analysis
3. Link to existing patterns if similar
4. Create GitHub issue if severity warrants

## Data Retention Policy

| Data Type | Hot Storage | Cold Storage | Archive |
|-----------|-------------|--------------|---------|
| Error Events | 30 days | 1 year | 7 years |
| Error Patterns | Indefinite | N/A | N/A |
| Diagnostic Reports | 90 days | 2 years | 7 years |
| User Feedback | 1 year | 3 years | 7 years |

## Query Patterns

### Common Queries

**Errors by category in last 24h:**
```sql
SELECT category, COUNT(*) as count
FROM error_events
WHERE occurred_at > NOW() - INTERVAL '24 hours'
GROUP BY category
ORDER BY count DESC;
```

**Active patterns with high occurrence:**
```sql
SELECT id, name, total_occurrences, last_seen, ai_summary
FROM error_patterns
WHERE status = 'active'
  AND total_occurrences > 10
ORDER BY last_seen DESC;
```

**Correlated errors for agent run:**
```sql
SELECT e.*, p.name as pattern_name, p.ai_root_cause
FROM error_events e
LEFT JOIN error_patterns p ON e.pattern_id = p.id
WHERE e.agent_run_id = :agent_run_id
ORDER BY e.occurred_at;
```

## Integration with Existing Systems

### Agent Run Correlation

```
AgentRun
    |
    +-- agent_run_id --> ErrorEvent (captures errors during run)
    |
    +-- AgentCheckpoint (last good state before error)
```

### Sprint Correlation

```
Sprint
    |
    +-- sprint_id --> ErrorEvent (errors during sprint execution)
    |
    +-- sprint_id --> UserFeedback (feedback about sprint features)
```

### Telemetry Correlation

```
Logfire Trace
    |
    +-- trace_id --> ErrorEvent (links to full trace)
    |
    +-- diagnostic.* attributes (enriched error data)
```

## Metrics and KPIs

### Error Health Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Error Rate | Errors / Total Requests | < 1% |
| Pattern Detection Rate | Patterns / Total Errors | > 80% |
| MTTR | Mean Time to Resolution | < 24h |
| AI Categorization Accuracy | Correct / Total | > 90% |

### Feedback Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Feedback Response Time | Time to first response | < 4h |
| Resolution Rate | Resolved / Total | > 85% |
| User Satisfaction | Avg rating | > 4.0/5 |

## Security Considerations

1. **PII Handling:**
   - User IDs stored, not user details
   - Local variables logged as types, not values
   - Contact emails encrypted at rest

2. **Access Control:**
   - Error events: read by support + developers
   - Patterns: manage by developers
   - Feedback: create by users, manage by support

3. **Data Sanitization:**
   - API keys/secrets redacted from stack traces
   - Request bodies sanitized before logging
   - Environment variables masked
