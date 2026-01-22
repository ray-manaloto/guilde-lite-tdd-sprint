# Real-Time Communication Architecture

## Technical Design Document

**Version:** 1.0.0
**Date:** 2026-01-22
**Author:** Network Engineer Agent
**Status:** Draft

---

## 1. Executive Summary

This document defines the real-time communication architecture for the multi-agent workflow visualization feature. The design enables frontend clients to receive granular, real-time updates about candidate generation, judge decisions, and phase transitions during sprint execution.

---

## 2. Current State Analysis

### 2.1 Existing Infrastructure

| Component | Implementation | Location |
|-----------|---------------|----------|
| WebSocket Server | FastAPI native | `/backend/app/api/routes/v1/ws.py` |
| Connection Manager | In-memory room-based | `ConnectionManager` class |
| Event Broadcasting | JSON text messages | `broadcast_to_room()` method |
| Frontend Hook | React custom hook | `/frontend/src/hooks/use-websocket.ts` |
| State Management | TanStack Query | `@tanstack/react-query` v5.90 |
| Real-time State | Zustand | `zustand` v5.0 |

### 2.2 Current Event Structure

```json
{
  "type": "sprint_update",
  "sprint_id": "uuid",
  "status": "active|completed|failed",
  "phase": "discovery|coding|verification",
  "details": "Human-readable message"
}
```

### 2.3 Identified Gaps

1. **Event Granularity**: No events for candidate generation or judge decisions
2. **Message Reliability**: No acknowledgment or replay mechanism
3. **Connection Recovery**: Basic reconnection without state sync
4. **Event Ordering**: No sequence numbers for ordering guarantees
5. **Scalability**: Single-server in-memory rooms (no Redis pub/sub)

---

## 3. Protocol Design

### 3.1 Message Envelope Format

All WebSocket messages use a standardized envelope:

```
+------------------+
|  Message Envelope |
+------------------+
| version: "1.0"   |
| id: string       | <- Unique message ID (ULID)
| type: string     | <- Event type discriminator
| timestamp: ISO   | <- Server timestamp
| sequence: number | <- Monotonic sequence for ordering
| sprint_id: uuid  | <- Room/channel identifier
| payload: object  | <- Type-specific payload
| meta: object     | <- Optional metadata (trace_id, etc.)
+------------------+
```

**Example:**
```json
{
  "version": "1.0",
  "id": "01HXY2QK4R5MNCBZ3VWAP0TDEF",
  "type": "candidate.generated",
  "timestamp": "2026-01-22T10:30:45.123Z",
  "sequence": 42,
  "sprint_id": "550e8400-e29b-41d4-a716-446655440000",
  "payload": { ... },
  "meta": {
    "trace_id": "abc123",
    "trace_url": "https://logfire.../trace/abc123"
  }
}
```

### 3.2 Event Types Taxonomy

```
sprint.*              - Sprint lifecycle events
  sprint.started
  sprint.activated
  sprint.completed
  sprint.failed

phase.*               - Phase transition events
  phase.started
  phase.completed
  phase.failed

candidate.*           - Candidate generation events
  candidate.started
  candidate.generated
  candidate.failed

judge.*               - Judge decision events
  judge.started
  judge.decided
  judge.failed

connection.*          - Connection management events
  connection.sync      <- Server->Client: State sync on reconnect
  connection.ack       <- Client->Server: Acknowledge receipt
  connection.ping      <- Client->Server: Heartbeat
  connection.pong      <- Server->Client: Heartbeat response
```

### 3.3 Event Payloads

#### 3.3.1 Sprint Events

**sprint.started**
```json
{
  "type": "sprint.started",
  "payload": {
    "sprint_id": "uuid",
    "name": "Sprint Name",
    "goal": "Sprint goal description",
    "spec_id": "uuid|null",
    "workspace_ref": "2026-01-22T103045.123456"
  }
}
```

**sprint.completed**
```json
{
  "type": "sprint.completed",
  "payload": {
    "sprint_id": "uuid",
    "status": "completed|failed",
    "duration_ms": 125000,
    "phases_completed": ["discovery", "coding_1", "verification_1"],
    "final_output": "VERIFICATION_SUCCESS"
  }
}
```

#### 3.3.2 Phase Events

**phase.started**
```json
{
  "type": "phase.started",
  "payload": {
    "phase": "discovery|coding_N|verification_N",
    "attempt": 1,
    "model_config": {
      "openai_model": "gpt-4o",
      "anthropic_model": "claude-sonnet-4-20250514"
    },
    "input_summary": "Analyzing requirements..."
  }
}
```

**phase.completed**
```json
{
  "type": "phase.completed",
  "payload": {
    "phase": "discovery",
    "status": "completed|failed",
    "duration_ms": 15234,
    "output_summary": "Implementation plan created",
    "checkpoint_id": "cp_003_discovery_complete"
  }
}
```

#### 3.3.3 Candidate Events

**candidate.started**
```json
{
  "type": "candidate.started",
  "payload": {
    "phase": "discovery",
    "provider": "openai|anthropic",
    "model": "gpt-4o",
    "agent_name": "openai"
  }
}
```

**candidate.generated**
```json
{
  "type": "candidate.generated",
  "payload": {
    "candidate_id": "uuid",
    "phase": "discovery",
    "provider": "openai",
    "model": "gpt-4o",
    "agent_name": "openai",
    "status": "ok|error",
    "duration_ms": 8234,
    "tool_call_count": 3,
    "output_preview": "First 200 chars of output...",
    "metrics": {
      "trace_id": "abc123",
      "tokens_used": 1500
    }
  }
}
```

**candidate.failed**
```json
{
  "type": "candidate.failed",
  "payload": {
    "phase": "discovery",
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "agent_name": "anthropic",
    "error": "Rate limit exceeded",
    "error_code": "RATE_LIMIT"
  }
}
```

#### 3.3.4 Judge Events

**judge.started**
```json
{
  "type": "judge.started",
  "payload": {
    "phase": "discovery",
    "model": "gpt-4o",
    "candidate_count": 2,
    "candidate_ids": ["uuid1", "uuid2"]
  }
}
```

**judge.decided**
```json
{
  "type": "judge.decided",
  "payload": {
    "phase": "discovery",
    "decision_id": "uuid",
    "winner": {
      "candidate_id": "uuid",
      "agent_name": "openai",
      "provider": "openai",
      "model": "gpt-4o"
    },
    "score": 0.85,
    "scores": {
      "helpfulness": 0.9,
      "correctness": 0.8
    },
    "rationale": "Selected for superior code structure...",
    "checkpoint_id": "cp_004_discovery_judged"
  }
}
```

#### 3.3.5 Connection Events

**connection.sync** (Server to Client on reconnect)
```json
{
  "type": "connection.sync",
  "payload": {
    "last_sequence": 42,
    "sprint_state": {
      "status": "active",
      "current_phase": "coding_1",
      "phases_completed": ["discovery"]
    },
    "missed_events": [ /* Array of events since last_sequence */ ]
  }
}
```

---

## 4. Room/Channel Architecture

### 4.1 Room Hierarchy

```
rooms/
  sprint:{sprint_id}/          <- Main sprint room
    candidates/                <- Candidate updates sub-channel
    phases/                    <- Phase updates sub-channel
  user:{user_id}/              <- User notifications (future)
  global/                      <- System-wide broadcasts (future)
```

### 4.2 Room Subscription Model

Clients subscribe to sprint rooms using the WebSocket URL path:

```
ws://host/api/v1/ws/sprint/{sprint_id}
ws://host/api/v1/ws/sprint/{sprint_id}?token={jwt}
```

### 4.3 Multi-Room Support (Future)

For dashboard views showing multiple sprints:

```json
// Client -> Server
{
  "type": "subscribe",
  "rooms": ["sprint:uuid1", "sprint:uuid2"]
}

// Server -> Client
{
  "type": "subscribed",
  "rooms": ["sprint:uuid1", "sprint:uuid2"]
}
```

---

## 5. Message Reliability

### 5.1 Sequence-Based Ordering

Each room maintains a monotonically increasing sequence number:

```
Room: sprint:550e8400-e29b-41d4-a716-446655440000
  Sequence: 1  -> sprint.started
  Sequence: 2  -> phase.started (discovery)
  Sequence: 3  -> candidate.started (openai)
  Sequence: 4  -> candidate.started (anthropic)
  Sequence: 5  -> candidate.generated (openai)
  Sequence: 6  -> candidate.generated (anthropic)
  Sequence: 7  -> judge.started
  Sequence: 8  -> judge.decided
  Sequence: 9  -> phase.completed (discovery)
  ...
```

### 5.2 Event Buffer (Redis)

Store recent events in Redis for replay on reconnection:

```
Key: ws:events:sprint:{sprint_id}
Type: Sorted Set (ZSET)
Score: Sequence number
Value: JSON-encoded event
TTL: 1 hour

Operations:
  ZADD ws:events:sprint:{id} {seq} {event_json}
  ZRANGEBYSCORE ws:events:sprint:{id} {last_seq} +inf
  ZREMRANGEBYSCORE ws:events:sprint:{id} -inf {cutoff}
```

### 5.3 Reconnection Flow

```
Client                          Server
   |                               |
   |-- Connect (last_seq=5) ------>|
   |                               |
   |<-- connection.sync ---------- |
   |    (missed_events: 6,7,8,9)   |
   |                               |
   |<-- Live events continue ------|
```

### 5.4 Client-Side Gap Detection

```typescript
// Client detects gap in sequence
if (event.sequence !== lastSequence + 1) {
  // Request missing events
  socket.send({
    type: "sync_request",
    last_sequence: lastSequence
  });
}
```

---

## 6. Frontend Integration Pattern

### 6.1 TanStack Query + WebSocket Sync

The pattern uses TanStack Query for initial data fetch and REST API operations, with WebSocket events updating the query cache:

```
                                    +-----------------+
                                    |  TanStack Query |
                                    |      Cache      |
                                    +-----------------+
                                           ^  |
                              invalidate/  |  | read
                              setQueryData |  v
+-------------+    REST      +-----------------+
|   Backend   |<------------>|   API Hooks     |
|    API      |              |  useSprintQuery |
+-------------+              +-----------------+
      ^
      |
      | WebSocket
      v
+-------------+              +-----------------+
|  WebSocket  |  events  --> | useSprintSocket |
|   Server    | -----------> |    (Zustand)    |
+-------------+              +-----------------+
                                    |
                                    | update cache
                                    v
                            +-----------------+
                            |  queryClient.   |
                            | setQueryData()  |
                            +-----------------+
```

### 6.2 Query Key Structure

```typescript
// Query keys for sprint data
const sprintKeys = {
  all: ['sprints'] as const,
  lists: () => [...sprintKeys.all, 'list'] as const,
  detail: (id: string) => [...sprintKeys.all, 'detail', id] as const,
  candidates: (sprintId: string, phase: string) =>
    [...sprintKeys.detail(sprintId), 'candidates', phase] as const,
  timeline: (id: string) => [...sprintKeys.detail(id), 'timeline'] as const,
};
```

### 6.3 WebSocket Event Handlers

```typescript
// Event handler map
const eventHandlers: Record<string, (payload: any) => void> = {
  'sprint.started': (payload) => {
    queryClient.setQueryData(
      sprintKeys.detail(payload.sprint_id),
      (old) => ({ ...old, status: 'active' })
    );
  },

  'candidate.generated': (payload) => {
    queryClient.setQueryData(
      sprintKeys.candidates(payload.sprint_id, payload.phase),
      (old) => [...(old || []), payload]
    );
  },

  'judge.decided': (payload) => {
    queryClient.setQueryData(
      sprintKeys.detail(payload.sprint_id),
      (old) => ({
        ...old,
        lastDecision: payload
      })
    );
  },

  'phase.completed': (payload) => {
    // Invalidate to refetch full state
    queryClient.invalidateQueries({
      queryKey: sprintKeys.detail(payload.sprint_id)
    });
  },
};
```

### 6.4 Optimistic Updates

For user-initiated actions (e.g., triggering a sprint):

```typescript
const triggerSprintMutation = useMutation({
  mutationFn: (sprintId: string) => api.post(`/sprints/${sprintId}/trigger`),

  onMutate: async (sprintId) => {
    // Cancel outgoing refetches
    await queryClient.cancelQueries({ queryKey: sprintKeys.detail(sprintId) });

    // Snapshot previous value
    const previous = queryClient.getQueryData(sprintKeys.detail(sprintId));

    // Optimistically update
    queryClient.setQueryData(sprintKeys.detail(sprintId), (old) => ({
      ...old,
      status: 'active',
      triggeredAt: new Date().toISOString()
    }));

    return { previous };
  },

  onError: (err, sprintId, context) => {
    // Rollback on error
    queryClient.setQueryData(
      sprintKeys.detail(sprintId),
      context?.previous
    );
  },

  onSettled: (data, err, sprintId) => {
    // Always refetch after mutation
    queryClient.invalidateQueries({ queryKey: sprintKeys.detail(sprintId) });
  },
});
```

### 6.5 Zustand Store for Real-Time State

```typescript
interface SprintRealtimeState {
  // Connection state
  isConnected: boolean;
  lastSequence: number;

  // Real-time data (not persisted)
  currentPhase: string | null;
  activeCandidates: Map<string, CandidateProgress>;
  lastDecision: JudgeDecision | null;

  // Timeline for visualization
  events: TimelineEvent[];

  // Actions
  handleEvent: (event: WebSocketEvent) => void;
  reset: () => void;
}

const useSprintRealtimeStore = create<SprintRealtimeState>((set, get) => ({
  isConnected: false,
  lastSequence: 0,
  currentPhase: null,
  activeCandidates: new Map(),
  lastDecision: null,
  events: [],

  handleEvent: (event) => {
    set((state) => {
      // Update sequence tracking
      if (event.sequence > state.lastSequence) {
        state.lastSequence = event.sequence;
      }

      // Add to timeline
      state.events.push(event);

      // Type-specific handling
      switch (event.type) {
        case 'candidate.started':
          state.activeCandidates.set(event.payload.agent_name, {
            status: 'running',
            startedAt: event.timestamp
          });
          break;

        case 'candidate.generated':
          state.activeCandidates.set(event.payload.agent_name, {
            status: 'completed',
            ...event.payload
          });
          break;

        case 'judge.decided':
          state.lastDecision = event.payload;
          break;

        case 'phase.started':
          state.currentPhase = event.payload.phase;
          state.activeCandidates.clear();
          state.lastDecision = null;
          break;
      }

      return state;
    });
  },

  reset: () => set({
    currentPhase: null,
    activeCandidates: new Map(),
    lastDecision: null,
    events: []
  })
}));
```

---

## 7. Connection State Management

### 7.1 Connection States

```
     +------------+
     |            |
     |  INITIAL   |
     |            |
     +-----+------+
           |
           | connect()
           v
     +------------+       error        +------------+
     |            | -----------------> |            |
     | CONNECTING |                    |   ERROR    |
     |            | <----------------- |            |
     +-----+------+       retry        +------------+
           |
           | onopen
           v
     +------------+       close        +------------+
     |            | -----------------> |            |
     | CONNECTED  |                    | DISCONNECTED|
     |            | <----------------- |  (retry)   |
     +-----+------+     reconnect      +------------+
           |
           | sync_complete
           v
     +------------+
     |            |
     |   SYNCED   |
     |            |
     +------------+
```

### 7.2 Reconnection Strategy

| Attempt | Delay | Jitter |
|---------|-------|--------|
| 1 | 1s | 0-500ms |
| 2 | 2s | 0-1000ms |
| 3 | 4s | 0-2000ms |
| 4 | 8s | 0-4000ms |
| 5 | 16s | 0-8000ms |
| 6+ | 30s | 0-15000ms |

**Max Attempts:** 10 (then require manual reconnect)

### 7.3 Heartbeat Protocol

```
Client                          Server
   |                               |
   |-- ping (every 30s) ---------> |
   |                               |
   |<-- pong --------------------- |
   |                               |

Timeout: 10s (no pong = connection dead)
```

---

## 8. Backend Implementation Patterns

### 8.1 Event Emission Points

Events are emitted from `PhaseRunner` and `AgentTddService`:

```
PhaseRunner.start()
  |
  +-> emit("sprint.started")
  |
  +-> start_phase("discovery")
  |     +-> emit("phase.started")
  |
  +-> AgentTddService.execute()
  |     |
  |     +-> _run_subagents()
  |     |     +-> emit("candidate.started") x N
  |     |     +-> emit("candidate.generated") x N
  |     |
  |     +-> _run_judge()
  |           +-> emit("judge.started")
  |           +-> emit("judge.decided")
  |
  +-> end_phase("discovery")
  |     +-> emit("phase.completed")
  |
  +-> [loop coding/verification]
  |
  +-> emit("sprint.completed")
```

### 8.2 Event Emitter Interface

```python
from abc import ABC, abstractmethod
from typing import Any

class SprintEventEmitter(ABC):
    """Interface for emitting sprint events."""

    @abstractmethod
    async def emit(
        self,
        event_type: str,
        sprint_id: str,
        payload: dict[str, Any],
        meta: dict[str, Any] | None = None
    ) -> None:
        """Emit an event to connected clients."""
        pass

class WebSocketEventEmitter(SprintEventEmitter):
    """WebSocket-based event emitter."""

    def __init__(self, manager: ConnectionManager, redis: RedisClient):
        self.manager = manager
        self.redis = redis
        self._sequences: dict[str, int] = {}

    async def emit(
        self,
        event_type: str,
        sprint_id: str,
        payload: dict[str, Any],
        meta: dict[str, Any] | None = None
    ) -> None:
        # Get next sequence
        seq_key = f"ws:seq:{sprint_id}"
        sequence = await self.redis.raw.incr(seq_key)

        # Build envelope
        event = {
            "version": "1.0",
            "id": ulid.new().str,
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sequence": sequence,
            "sprint_id": sprint_id,
            "payload": payload,
            "meta": meta or {}
        }

        # Store in Redis for replay
        await self.redis.raw.zadd(
            f"ws:events:{sprint_id}",
            {json.dumps(event): sequence}
        )
        await self.redis.raw.expire(f"ws:events:{sprint_id}", 3600)

        # Broadcast to room
        await self.manager.broadcast_to_room(
            sprint_id,
            json.dumps(event)
        )
```

### 8.3 Redis Pub/Sub for Horizontal Scaling

For multi-instance deployments:

```
+----------+     +----------+     +----------+
| Backend  |     | Backend  |     | Backend  |
| Instance |     | Instance |     | Instance |
|    1     |     |    2     |     |    3     |
+----+-----+     +----+-----+     +----+-----+
     |               |               |
     +-------+-------+-------+-------+
             |               |
        +----v----+     +----v----+
        |  Redis  |<--->|  Redis  |
        |  Pub    |     |  Sub    |
        +---------+     +---------+
```

**Channel naming:**
```
ws:sprint:{sprint_id}  <- Sprint-specific events
ws:broadcast           <- Global broadcasts
```

---

## 9. Security Considerations

### 9.1 Authentication

- WebSocket connections require JWT token (query param or cookie)
- Token verified on connection establishment
- Connection closed on token expiration

### 9.2 Authorization

- Clients can only subscribe to sprints they have access to
- Sprint ownership verified against user_id in token

### 9.3 Rate Limiting

- Max 5 connections per user
- Max 100 messages per minute per connection
- Excessive connections result in 4029 close code

### 9.4 Input Validation

- All client messages validated against schema
- Invalid messages logged and discarded
- Malformed JSON results in warning, not disconnect

---

## 10. Monitoring and Observability

### 10.1 Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `ws_connections_total` | Counter | room, status |
| `ws_connections_active` | Gauge | room |
| `ws_messages_sent_total` | Counter | room, event_type |
| `ws_messages_received_total` | Counter | room, message_type |
| `ws_message_latency_ms` | Histogram | event_type |
| `ws_reconnections_total` | Counter | room, reason |

### 10.2 Logging

```json
{
  "level": "info",
  "event": "ws_event_sent",
  "sprint_id": "uuid",
  "event_type": "candidate.generated",
  "sequence": 42,
  "room_size": 3,
  "trace_id": "abc123"
}
```

### 10.3 Tracing

- Each event includes `trace_id` linking to Logfire trace
- WebSocket operations instrumented with OpenTelemetry
- Span: `ws.broadcast` with event_type attribute

---

## 11. Migration Path

### Phase 1: Event Protocol (Week 1)
- Define event schemas (Pydantic models)
- Implement event envelope format
- Add sequence number tracking

### Phase 2: Backend Emission (Week 2)
- Add `SprintEventEmitter` interface
- Inject emitter into `PhaseRunner`
- Emit events from `AgentTddService`

### Phase 3: Redis Integration (Week 3)
- Implement event buffering in Redis
- Add replay on reconnection
- Test horizontal scaling

### Phase 4: Frontend Integration (Week 4)
- Update `useWebSocket` hook
- Implement TanStack Query sync
- Add Zustand real-time store

### Phase 5: Testing and Polish (Week 5)
- End-to-end integration tests
- Load testing
- Documentation

---

## 12. Appendices

### A. Event Schema Definitions (Pydantic)

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Any, Literal

class EventMeta(BaseModel):
    trace_id: str | None = None
    trace_url: str | None = None
    request_id: str | None = None

class EventEnvelope(BaseModel):
    version: Literal["1.0"] = "1.0"
    id: str
    type: str
    timestamp: datetime
    sequence: int
    sprint_id: str
    payload: dict[str, Any]
    meta: EventMeta = EventMeta()

class CandidateGeneratedPayload(BaseModel):
    candidate_id: str
    phase: str
    provider: str
    model: str
    agent_name: str
    status: Literal["ok", "error"]
    duration_ms: int
    tool_call_count: int
    output_preview: str | None = None
    metrics: dict[str, Any] = {}

class JudgeDecidedPayload(BaseModel):
    phase: str
    decision_id: str
    winner: dict[str, str]  # candidate_id, agent_name, provider, model
    score: float | None
    scores: dict[str, float] = {}
    rationale: str
    checkpoint_id: str | None = None
```

### B. Frontend Type Definitions

```typescript
interface EventMeta {
  trace_id?: string;
  trace_url?: string;
  request_id?: string;
}

interface EventEnvelope<T = unknown> {
  version: "1.0";
  id: string;
  type: string;
  timestamp: string;
  sequence: number;
  sprint_id: string;
  payload: T;
  meta: EventMeta;
}

interface CandidateGeneratedPayload {
  candidate_id: string;
  phase: string;
  provider: "openai" | "anthropic";
  model: string;
  agent_name: string;
  status: "ok" | "error";
  duration_ms: number;
  tool_call_count: number;
  output_preview?: string;
  metrics: Record<string, unknown>;
}

interface JudgeDecidedPayload {
  phase: string;
  decision_id: string;
  winner: {
    candidate_id: string;
    agent_name: string;
    provider: string;
    model: string;
  };
  score: number | null;
  scores: Record<string, number>;
  rationale: string;
  checkpoint_id?: string;
}
```

### C. Redis Key Reference

| Key Pattern | Type | TTL | Description |
|-------------|------|-----|-------------|
| `ws:seq:{sprint_id}` | String | None | Sequence counter |
| `ws:events:{sprint_id}` | ZSET | 1hr | Event buffer |
| `ws:rooms:{sprint_id}` | SET | None | Connected socket IDs |
| `ws:user:{user_id}:connections` | SET | None | User's connections |

---

## 13. References

- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [TanStack Query Real-time Updates](https://tanstack.com/query/latest/docs/framework/react/guides/updates-from-mutation-responses)
- [Redis Pub/Sub](https://redis.io/docs/manual/pubsub/)
- [WebSocket Close Codes](https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent/code)
