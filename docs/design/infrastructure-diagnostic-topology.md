# Infrastructure Design: Self-Diagnostic Tooling Integration

**Version:** 1.0
**Date:** 2026-01-22
**Author:** DevOps Engineer Agent

---

## 1. Executive Summary

This document defines the infrastructure topology for integrating self-diagnostic tooling into the guilde-lite-tdd-sprint platform. The design encompasses:

- **dev3000** development debugging server (MCP-based)
- **Circuit breakers** for external API resilience
- **Enhanced observability** via Logfire/Sentry configuration
- **Health check enhancements** for diagnostic endpoints

---

## 2. Current Infrastructure Overview

### 2.1 Service Topology

```
Port Allocation (Current):
+------------------+--------+----------------------------+
| Service          | Port   | Description                |
+------------------+--------+----------------------------+
| FastAPI Backend  | 8000   | Main API server            |
| Agent-Web UI     | 8001   | AI agent web interface     |
| Next.js Frontend | 3000   | User-facing web app        |
| PostgreSQL       | 5432   | Primary database           |
| Redis            | 6379   | Cache/session/queue broker |
| Flower           | 5555   | Celery task monitoring     |
| Prometheus       | /metrics | Metrics endpoint (on 8000) |
+------------------+--------+----------------------------+
```

### 2.2 Existing Observability Stack

| Component | Purpose | Status |
|-----------|---------|--------|
| Logfire | Distributed tracing, AI agent observability | Configured |
| Sentry | Error tracking, crash reporting | Optional (DSN-based) |
| Prometheus | Metrics collection | Active via FastAPI instrumentator |

---

## 3. New Components Architecture

### 3.1 Infrastructure Diagram - Diagnostic Data Flow

```
                              +------------------+
                              |   Developers     |
                              |  (Local/Remote)  |
                              +--------+---------+
                                       |
           +---------------------------+---------------------------+
           |                           |                           |
           v                           v                           v
+----------+----------+    +-----------+-----------+    +----------+----------+
|   Next.js Frontend  |    |    dev3000 Server     |    |   Agent-Web UI      |
|      :3000          |    |       :3001           |    |      :8001          |
|                     |    |  (MCP Debug Server)   |    |                     |
+----------+----------+    +----------+------------+    +----------+----------+
           |                          |                            |
           |              +-----------+-----------+                |
           |              |                       |                |
           v              v                       v                v
+----------+---------------------------------------------+----------+
|                    FastAPI Backend (:8000)                        |
|                                                                   |
|  +------------------+  +------------------+  +------------------+ |
|  | Circuit Breaker  |  | Health Checks    |  | Diagnostic API   | |
|  | Manager          |  | (Enhanced)       |  | Endpoints        | |
|  +--------+---------+  +--------+---------+  +--------+---------+ |
|           |                     |                     |           |
|  +--------+---------+  +--------+---------+  +--------+---------+ |
|  | External APIs    |  | Dependency       |  | Trace Context    | |
|  | (OpenAI, etc.)   |  | Status Monitor   |  | Propagator       | |
|  +------------------+  +------------------+  +------------------+ |
+------------------------------------------------------------------+
           |                     |                     |
           v                     v                     v
+----------+----------+  +-------+--------+  +---------+----------+
|    PostgreSQL       |  |     Redis      |  |  External APIs     |
|      :5432          |  |     :6379      |  | (with CB protect)  |
+---------------------+  +----------------+  +--------------------+
           |                     |                     |
           +---------------------+---------------------+
                                 |
                    +------------+------------+
                    |                         |
                    v                         v
           +--------+--------+       +--------+--------+
           |    Logfire      |       |     Sentry      |
           | (Traces/Spans)  |       | (Errors/Alerts) |
           +-----------------+       +-----------------+
```

### 3.2 Port Allocation (Extended)

```
+----------------------+--------+-----------------------------------+
| Service              | Port   | Description                       |
+----------------------+--------+-----------------------------------+
| FastAPI Backend      | 8000   | Main API server                   |
| Agent-Web UI         | 8001   | AI agent web interface            |
| Next.js Frontend     | 3000   | User-facing web app               |
| dev3000 Debug Server | 3001   | MCP development debugging server  |
| PostgreSQL           | 5432   | Primary database                  |
| Redis                | 6379   | Cache/session/queue broker        |
| Flower               | 5555   | Celery task monitoring            |
| Diagnostic WS        | 8000   | WebSocket on /api/v1/diag/stream  |
+----------------------+--------+-----------------------------------+
```

---

## 4. Docker Compose Additions

### 4.1 docker-compose.diagnostic.yml (New File)

```yaml
# Diagnostic tooling overlay for development
# Usage: docker-compose -f docker-compose.dev.yml -f docker-compose.diagnostic.yml up -d
#
# This overlay adds self-diagnostic tooling to the development environment.

version: "3.8"

services:
  # MCP-based development debugging server
  dev3000:
    build:
      context: ./tools/dev3000
      dockerfile: Dockerfile
    container_name: guilde_lite_tdd_sprint_dev3000
    ports:
      - "3001:3001"
    volumes:
      - ./backend:/workspace/backend:ro
      - ./frontend:/workspace/frontend:ro
      - ./logs:/workspace/logs
      - dev3000_data:/data
    environment:
      - DEV3000_PORT=3001
      - DEV3000_MODE=development
      - DEV3000_LOG_LEVEL=debug
      - DEV3000_BACKEND_URL=http://app:8000
      - DEV3000_AGENT_URL=http://agent-web:8001
      - DEV3000_LOGFIRE_TOKEN=${LOGFIRE_TOKEN:-}
      - DEV3000_SENTRY_DSN=${SENTRY_DSN:-}
      # MCP configuration
      - MCP_SERVER_NAME=guilde-diag
      - MCP_TRANSPORT=stdio
      - MCP_TOOLS_ENABLED=true
    networks:
      - backend
      - diagnostic
    depends_on:
      - app
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    labels:
      - "diagnostic.role=debug-server"
      - "diagnostic.mcp=true"

  # Agent-web service (if not in main compose)
  agent-web:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: guilde_lite_tdd_sprint_agent_web
    ports:
      - "8001:8001"
    volumes:
      - ./backend/app:/app/app:ro
    env_file:
      - ./.env
    environment:
      - DEBUG=true
      - ENVIRONMENT=local
      - POSTGRES_HOST=db
      - REDIS_HOST=redis
      - DIAGNOSTIC_MODE=true
    command: guilde_lite_tdd_sprint agent web --port 8001
    networks:
      - backend
      - diagnostic
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # Circuit breaker state store (optional - can use Redis)
  # Keeping separate for isolation and debugging
  circuit-state:
    image: redis:7-alpine
    container_name: guilde_lite_tdd_sprint_circuit_state
    ports:
      - "6380:6379"
    volumes:
      - circuit_state_data:/data
    networks:
      - diagnostic
    command: redis-server --appendonly yes --maxmemory 64mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    labels:
      - "diagnostic.role=circuit-breaker-state"

networks:
  diagnostic:
    driver: bridge
    name: guilde_diagnostic

volumes:
  dev3000_data:
  circuit_state_data:
```

### 4.2 Backend Service Enhancement (docker-compose.dev.yml updates)

Add to the `app` service environment:

```yaml
environment:
  # ... existing vars ...
  # Diagnostic mode
  - DIAGNOSTIC_MODE=${DIAGNOSTIC_MODE:-false}
  - DIAGNOSTIC_VERBOSE=${DIAGNOSTIC_VERBOSE:-false}
  # Circuit breaker configuration
  - CIRCUIT_BREAKER_ENABLED=${CIRCUIT_BREAKER_ENABLED:-true}
  - CIRCUIT_BREAKER_REDIS_URL=redis://circuit-state:6379/0
  - CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
  - CIRCUIT_BREAKER_RECOVERY_TIMEOUT=30
  - CIRCUIT_BREAKER_HALF_OPEN_REQUESTS=3
  # Enhanced observability
  - LOGFIRE_DIAGNOSTIC_SPANS=${LOGFIRE_DIAGNOSTIC_SPANS:-true}
  - SENTRY_TRACES_SAMPLE_RATE=${SENTRY_TRACES_SAMPLE_RATE:-1.0}
  - SENTRY_PROFILES_SAMPLE_RATE=${SENTRY_PROFILES_SAMPLE_RATE:-0.1}
```

---

## 5. Environment Variables

### 5.1 Complete Environment Variable Reference

```bash
# =============================================================================
# DIAGNOSTIC TOOLING CONFIGURATION
# Add these to your .env file for self-diagnostic features
# =============================================================================

# === dev3000 Debug Server ===
DEV3000_ENABLED=true
DEV3000_PORT=3001
DEV3000_MODE=development          # development|staging|production
DEV3000_LOG_LEVEL=debug           # debug|info|warning|error
DEV3000_BACKEND_URL=http://localhost:8000
DEV3000_AGENT_URL=http://localhost:8001
DEV3000_FRONTEND_URL=http://localhost:3000

# MCP Configuration
MCP_SERVER_NAME=guilde-diag
MCP_TRANSPORT=stdio               # stdio|sse|websocket
MCP_TOOLS_ENABLED=true
MCP_RESOURCES_ENABLED=true
MCP_PROMPTS_ENABLED=false

# === Circuit Breaker Configuration ===
CIRCUIT_BREAKER_ENABLED=true
CIRCUIT_BREAKER_REDIS_URL=redis://localhost:6380/0
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5      # failures before opening
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=30      # seconds before half-open
CIRCUIT_BREAKER_HALF_OPEN_REQUESTS=3     # test requests in half-open
CIRCUIT_BREAKER_SUCCESS_THRESHOLD=2      # successes to close

# Per-service circuit breaker overrides
CB_OPENAI_FAILURE_THRESHOLD=3
CB_OPENAI_RECOVERY_TIMEOUT=60
CB_ANTHROPIC_FAILURE_THRESHOLD=3
CB_ANTHROPIC_RECOVERY_TIMEOUT=60
CB_EXTERNAL_API_FAILURE_THRESHOLD=5
CB_EXTERNAL_API_RECOVERY_TIMEOUT=30

# === Enhanced Observability (Logfire) ===
LOGFIRE_DIAGNOSTIC_SPANS=true
LOGFIRE_SPAN_PROCESSOR_BATCH_SIZE=512
LOGFIRE_SPAN_PROCESSOR_TIMEOUT=5000
LOGFIRE_RESOURCE_ATTRIBUTES=service.namespace=guilde,deployment.environment=development

# Additional Logfire Configuration
LOGFIRE_CONSOLE_ENABLED=true           # Local console output
LOGFIRE_CONSOLE_COLORS=true
LOGFIRE_CONSOLE_INCLUDE_TIMESTAMPS=true
LOGFIRE_CONSOLE_VERBOSE=false

# === Enhanced Observability (Sentry) ===
SENTRY_TRACES_SAMPLE_RATE=1.0          # 0.0-1.0 (1.0 = 100% for dev)
SENTRY_PROFILES_SAMPLE_RATE=0.1        # 0.0-1.0 (profiling sample rate)
SENTRY_ENVIRONMENT=development
SENTRY_RELEASE=${GIT_SHA:-local}
SENTRY_DEBUG=false
SENTRY_ATTACH_STACKTRACE=true
SENTRY_SEND_DEFAULT_PII=false          # GDPR compliance

# === Diagnostic API Configuration ===
DIAGNOSTIC_MODE=true
DIAGNOSTIC_VERBOSE=false
DIAGNOSTIC_AUTH_REQUIRED=false         # Require API key for diag endpoints
DIAGNOSTIC_RATE_LIMIT=100              # Requests per minute
DIAGNOSTIC_WEBSOCKET_ENABLED=true
DIAGNOSTIC_STREAM_BUFFER_SIZE=1000

# === Health Check Configuration ===
HEALTH_CHECK_TIMEOUT=5                 # seconds
HEALTH_CHECK_INCLUDE_DETAILS=true
HEALTH_CHECK_EXTERNAL_SERVICES=true    # Check external API connectivity
HEALTH_DEEP_CHECK_ENABLED=true
HEALTH_DEEP_CHECK_INTERVAL=60          # seconds between deep checks

# === Performance Thresholds (for health warnings) ===
HEALTH_WARN_DB_LATENCY_MS=100
HEALTH_WARN_REDIS_LATENCY_MS=50
HEALTH_WARN_API_LATENCY_MS=500
HEALTH_WARN_MEMORY_PERCENT=80
HEALTH_WARN_CPU_PERCENT=70
```

### 5.2 Environment-Specific Configurations

#### Development (.env.development)

```bash
DIAGNOSTIC_MODE=true
DIAGNOSTIC_VERBOSE=true
DEV3000_ENABLED=true
DEV3000_LOG_LEVEL=debug
CIRCUIT_BREAKER_ENABLED=true
LOGFIRE_DIAGNOSTIC_SPANS=true
SENTRY_TRACES_SAMPLE_RATE=1.0
HEALTH_CHECK_INCLUDE_DETAILS=true
```

#### Staging (.env.staging)

```bash
DIAGNOSTIC_MODE=true
DIAGNOSTIC_VERBOSE=false
DEV3000_ENABLED=false
CIRCUIT_BREAKER_ENABLED=true
LOGFIRE_DIAGNOSTIC_SPANS=true
SENTRY_TRACES_SAMPLE_RATE=0.5
HEALTH_CHECK_INCLUDE_DETAILS=true
```

#### Production (.env.production)

```bash
DIAGNOSTIC_MODE=false
DIAGNOSTIC_VERBOSE=false
DEV3000_ENABLED=false
CIRCUIT_BREAKER_ENABLED=true
LOGFIRE_DIAGNOSTIC_SPANS=false
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.01
HEALTH_CHECK_INCLUDE_DETAILS=false
DIAGNOSTIC_AUTH_REQUIRED=true
```

---

## 6. Health Check Enhancements

### 6.1 Enhanced Health Check Endpoints

| Endpoint | Purpose | Response Time | Auth |
|----------|---------|---------------|------|
| `GET /api/v1/health` | Basic liveness | < 10ms | None |
| `GET /api/v1/health/live` | K8s liveness probe | < 50ms | None |
| `GET /api/v1/health/ready` | K8s readiness probe | < 500ms | None |
| `GET /api/v1/health/deep` | Deep diagnostics | < 5s | Optional |
| `GET /api/v1/diag/status` | Full system status | < 10s | Required |
| `GET /api/v1/diag/circuits` | Circuit breaker states | < 100ms | Required |
| `WS /api/v1/diag/stream` | Real-time diagnostics | Streaming | Required |

### 6.2 Deep Health Check Response Schema

```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2026-01-22T10:30:00Z",
  "service": "guilde_lite_tdd_sprint",
  "version": "0.1.0",
  "environment": "development",
  "uptime_seconds": 3600,
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 5.2,
      "type": "postgresql",
      "pool": {
        "size": 5,
        "available": 4,
        "in_use": 1
      }
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 1.1,
      "memory_used_mb": 12.5,
      "connected_clients": 3
    },
    "external_apis": {
      "openai": {
        "status": "healthy",
        "circuit_state": "closed",
        "last_success": "2026-01-22T10:29:55Z",
        "failure_count": 0
      },
      "anthropic": {
        "status": "degraded",
        "circuit_state": "half-open",
        "last_failure": "2026-01-22T10:25:00Z",
        "failure_count": 3
      }
    },
    "observability": {
      "logfire": {
        "status": "healthy",
        "spans_exported": 15420,
        "export_errors": 0
      },
      "sentry": {
        "status": "healthy",
        "events_sent": 45,
        "rate_limited": false
      }
    }
  },
  "metrics": {
    "requests_total": 50000,
    "requests_per_second": 125.5,
    "error_rate_percent": 0.02,
    "p50_latency_ms": 45,
    "p99_latency_ms": 250
  },
  "diagnostics": {
    "memory_mb": 512,
    "cpu_percent": 25.5,
    "open_connections": 45,
    "active_tasks": 12
  }
}
```

---

## 7. Circuit Breaker Architecture

### 7.1 Circuit Breaker State Machine

```
                    +----------+
                    |  CLOSED  |<--------+
                    +----+-----+         |
                         |               |
             Failure threshold           | Success threshold
                  reached                |    reached
                         |               |
                         v               |
                    +----------+    +----+-----+
                    |   OPEN   |--->| HALF-OPEN|
                    +----------+    +----------+
                         ^               |
                         |               |
                    Recovery         Failure
                    timeout          detected
                    expires              |
                         |               v
                         +---------------+
```

### 7.2 Protected External Services

| Service | Failure Threshold | Recovery Timeout | Priority |
|---------|-------------------|------------------|----------|
| OpenAI API | 3 | 60s | Critical |
| Anthropic API | 3 | 60s | Critical |
| OpenRouter API | 5 | 30s | Normal |
| External Webhooks | 10 | 15s | Low |
| Logfire Export | 5 | 30s | Normal |

### 7.3 Circuit Breaker Implementation Location

```
backend/app/core/
  circuit_breaker.py         # Core circuit breaker implementation
  circuit_breaker_config.py  # Configuration and defaults

backend/app/clients/
  openai_client.py           # OpenAI with circuit breaker
  anthropic_client.py        # Anthropic with circuit breaker

backend/app/api/routes/v1/
  diagnostics.py             # Circuit breaker status endpoints
```

---

## 8. CI/CD Integration

### 8.1 GitHub Actions Updates

Add to `.github/workflows/ci.yml`:

```yaml
  diagnostic-check:
    name: Diagnostic Tools Check
    runs-on: ubuntu-latest
    needs: [test]
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync --directory backend --dev

      - name: Run diagnostic self-tests
        run: |
          uv run --directory backend pytest tests/diagnostic/ -v
        env:
          DIAGNOSTIC_MODE: true
          CIRCUIT_BREAKER_ENABLED: true

      - name: Verify health endpoints
        run: |
          # Start server in background
          uv run --directory backend uvicorn app.main:app --host 0.0.0.0 --port 8000 &
          sleep 5

          # Test health endpoints
          curl -f http://localhost:8000/api/v1/health || exit 1
          curl -f http://localhost:8000/api/v1/health/live || exit 1

          # Cleanup
          pkill -f uvicorn || true
        env:
          POSTGRES_HOST: localhost
          REDIS_HOST: localhost

      - name: Build dev3000 container
        run: |
          docker build -t guilde-dev3000:test ./tools/dev3000
        if: hashFiles('tools/dev3000/Dockerfile') != ''
```

### 8.2 Staging Deployment Checks

Add to `.github/workflows/deploy-staging.yml`:

```yaml
  post-deploy-diagnostics:
    name: Post-Deploy Diagnostic Validation
    runs-on: ubuntu-latest
    needs: [deploy]
    steps:
      - name: Wait for deployment
        run: sleep 30

      - name: Validate health endpoints
        run: |
          STAGING_URL="${{ secrets.STAGING_URL }}"

          # Basic health
          response=$(curl -s -o /dev/null -w "%{http_code}" "${STAGING_URL}/api/v1/health")
          if [ "$response" != "200" ]; then
            echo "Health check failed: $response"
            exit 1
          fi

          # Readiness
          response=$(curl -s -o /dev/null -w "%{http_code}" "${STAGING_URL}/api/v1/health/ready")
          if [ "$response" != "200" ]; then
            echo "Readiness check failed: $response"
            exit 1
          fi

      - name: Verify circuit breaker endpoints
        run: |
          STAGING_URL="${{ secrets.STAGING_URL }}"
          API_KEY="${{ secrets.STAGING_API_KEY }}"

          curl -f -H "X-API-Key: ${API_KEY}" \
            "${STAGING_URL}/api/v1/diag/circuits" || exit 1

      - name: Check Logfire connectivity
        run: |
          # Verify traces are being exported
          curl -f -H "Authorization: Bearer ${{ secrets.LOGFIRE_READ_TOKEN }}" \
            "https://api.logfire.pydantic.dev/v1/projects/${{ secrets.LOGFIRE_PROJECT }}/traces?limit=1" || exit 1
```

---

## 9. Deployment Checklist

### 9.1 Pre-Deployment

- [ ] **Environment Variables**
  - [ ] All diagnostic env vars added to `.env` template
  - [ ] Secrets added to GitHub Secrets (SENTRY_DSN, LOGFIRE_TOKEN)
  - [ ] Circuit breaker Redis URL configured

- [ ] **Infrastructure**
  - [ ] dev3000 Dockerfile created and tested
  - [ ] docker-compose.diagnostic.yml validated
  - [ ] Network configuration verified (diagnostic network)
  - [ ] Volume mounts tested

- [ ] **Code Changes**
  - [ ] Circuit breaker module implemented
  - [ ] Enhanced health endpoints added
  - [ ] Diagnostic API routes created
  - [ ] Tests written and passing

### 9.2 Deployment Steps

1. **Update Configuration**
   ```bash
   # Copy new env template
   cp .env.example .env
   # Edit with environment-specific values
   vim .env
   ```

2. **Deploy Infrastructure**
   ```bash
   # Start base services
   docker-compose -f docker-compose.dev.yml up -d db redis

   # Start diagnostic services
   docker-compose -f docker-compose.dev.yml \
                  -f docker-compose.diagnostic.yml up -d
   ```

3. **Verify Deployment**
   ```bash
   # Check all services
   docker-compose -f docker-compose.dev.yml \
                  -f docker-compose.diagnostic.yml ps

   # Test health endpoints
   curl http://localhost:8000/api/v1/health
   curl http://localhost:8000/api/v1/health/ready
   curl http://localhost:3001/health  # dev3000
   ```

4. **Validate Observability**
   ```bash
   # Check Logfire traces
   ./scripts/devctl.sh preflight --verbose

   # Verify circuit breaker state
   curl -H "X-API-Key: $API_KEY" \
        http://localhost:8000/api/v1/diag/circuits
   ```

### 9.3 Post-Deployment Validation

- [ ] Health endpoints returning 200
- [ ] Logfire traces appearing in dashboard
- [ ] Sentry events being captured
- [ ] Circuit breakers in CLOSED state
- [ ] dev3000 MCP server responding
- [ ] WebSocket diagnostic stream functional
- [ ] Prometheus metrics being scraped

### 9.4 Rollback Procedure

```bash
# If issues detected, rollback diagnostic overlay
docker-compose -f docker-compose.dev.yml \
               -f docker-compose.diagnostic.yml down

# Start without diagnostics
docker-compose -f docker-compose.dev.yml up -d

# Disable diagnostic mode
export DIAGNOSTIC_MODE=false
```

---

## 10. Monitoring & Alerting

### 10.1 Key Metrics to Monitor

| Metric | Threshold | Alert Level |
|--------|-----------|-------------|
| `circuit_breaker_state` | != closed | Warning |
| `health_check_latency_ms` | > 500 | Warning |
| `error_rate_percent` | > 5% | Critical |
| `db_connection_pool_exhausted` | == true | Critical |
| `logfire_export_errors` | > 10/min | Warning |
| `sentry_rate_limited` | == true | Warning |

### 10.2 Dashboard Recommendations

1. **System Health Dashboard**
   - Service status grid
   - Circuit breaker states
   - Response latency histograms
   - Error rate trends

2. **Diagnostic Dashboard**
   - Trace throughput
   - Span durations
   - Error categorization
   - AI agent performance

---

## 11. Appendix

### 11.1 File Locations

```
/Users/ray.manaloto.guilde/dev/github/pagerguild/guilde-lite-tdd-sprint/
├── docker-compose.dev.yml           # Base development config
├── docker-compose.diagnostic.yml    # Diagnostic overlay (NEW)
├── .env.example                     # Environment template
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py           # Settings (update)
│   │   │   ├── circuit_breaker.py  # Circuit breaker (NEW)
│   │   │   └── logfire_setup.py    # Logfire config (update)
│   │   └── api/routes/v1/
│   │       ├── health.py           # Health endpoints (update)
│   │       └── diagnostics.py      # Diagnostic API (NEW)
│   └── tests/
│       └── diagnostic/             # Diagnostic tests (NEW)
├── tools/
│   └── dev3000/                    # Debug server (NEW)
│       ├── Dockerfile
│       └── src/
└── .github/workflows/
    └── ci.yml                      # CI pipeline (update)
```

### 11.2 References

- [Logfire Documentation](https://logfire.pydantic.dev/docs/)
- [Sentry FastAPI Integration](https://docs.sentry.io/platforms/python/integrations/fastapi/)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
