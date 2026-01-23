# AI Self-Healing System Acceptance Criteria

## Overview

This document defines testable acceptance criteria for validating the AI self-healing system integration. Each criterion includes specific pass/fail conditions and test commands.

**Last Updated:** 2026-01-22
**Feature Location:** `/Users/ray.manaloto.guilde/dev/github/pagerguild/guilde-lite-tdd-sprint`

---

## 1. Status Endpoint Validation

### AC-1.1: GET /api/v1/self-heal/status Returns System Status

**As a** system administrator
**I want** to query the self-healing status endpoint
**So that** I can verify the system is properly configured

#### Acceptance Criteria

| ID | Criterion | Pass Condition | Fail Condition |
|----|-----------|----------------|----------------|
| AC-1.1.1 | Endpoint returns 200 OK | HTTP status code is 200 | Any other status code |
| AC-1.1.2 | Response contains `enabled` field | `enabled` is boolean (true/false) | Field missing or non-boolean |
| AC-1.1.3 | Response contains `github_repo` field | Field present (string or null) | Field missing |
| AC-1.1.4 | Response contains `active_circuits` field | Field is integer >= 0 | Field missing or negative |
| AC-1.1.5 | Response contains `error_patterns_seen` field | Field is integer >= 0 | Field missing or negative |

#### Test Commands

```bash
# Test 1: Basic status check
curl -s http://localhost:8000/api/v1/self-heal/status | jq '.'

# Expected response structure:
# {
#   "enabled": true|false,
#   "github_repo": "owner/repo" | null,
#   "active_circuits": 0,
#   "error_patterns_seen": 0
# }

# Test 2: Verify enabled=true when properly configured
curl -s http://localhost:8000/api/v1/self-heal/status | jq -e '.enabled == true'
# Exit code 0 = PASS, non-zero = FAIL
```

#### Pass/Fail Checklist

- [ ] **PASS:** `enabled` is `true` when both `GITHUB_TOKEN` and `GITHUB_REPO` are configured
- [ ] **PASS:** `enabled` is `false` when either token or repo is missing
- [ ] **PASS:** Response returns within 500ms
- [ ] **FAIL:** Endpoint returns 4xx or 5xx error
- [ ] **FAIL:** Response missing required fields

---

## 2. GitHub Token Authentication Validation

### AC-2.1: GITHUB_TOKEN Authenticates with GitHub API

**As a** DevOps engineer
**I want** to verify the GitHub token has proper permissions
**So that** the self-healing system can create issues and trigger workflows

#### Acceptance Criteria

| ID | Criterion | Pass Condition | Fail Condition |
|----|-----------|----------------|----------------|
| AC-2.1.1 | Token authenticates successfully | GitHub API returns 200 for `/user` | 401 Unauthorized |
| AC-2.1.2 | Token has repo scope | Can read repository metadata | 403 Forbidden on repo read |
| AC-2.1.3 | Token can list workflows | GET `/repos/{owner}/{repo}/actions/workflows` returns 200 | 403 or 404 |
| AC-2.1.4 | Token can trigger dispatches | POST to `/repos/{owner}/{repo}/dispatches` returns 204 | 403 or 401 |
| AC-2.1.5 | Token can create issues | POST to `/repos/{owner}/{repo}/issues` returns 201 | 403 or 422 |

#### Test Commands

```bash
# Get token from environment
export GITHUB_TOKEN="${GITHUB_TOKEN:-$(grep GITHUB_TOKEN .env | cut -d= -f2)}"
export GITHUB_REPO="${GITHUB_REPO:-$(grep GITHUB_REPO .env | cut -d= -f2)}"

# Test 1: Verify token authentication
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     https://api.github.com/user | jq '{login: .login, id: .id}'
# Expected: Returns user object with login and id

# Test 2: Check repository access
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/$GITHUB_REPO" | jq '{name: .name, permissions: .permissions}'
# Expected: permissions.push should be true

# Test 3: Check workflow access
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/$GITHUB_REPO/actions/workflows" | jq '.total_count'
# Expected: Integer >= 0

# Test 4: Verify dispatch permission (dry-run check)
curl -s -o /dev/null -w "%{http_code}" \
     -X POST \
     -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     -H "X-GitHub-Api-Version: 2022-11-28" \
     "https://api.github.com/repos/$GITHUB_REPO/dispatches" \
     -d '{"event_type":"health-check","client_payload":{"test":true}}'
# Expected: 204 (success) or 422 (validation error, but auth succeeded)
```

#### Required Token Scopes

The `GITHUB_TOKEN` must have these scopes:
- `repo` - Full control of private repositories (or `public_repo` for public only)
- `workflow` - Update GitHub Action workflows

#### Pass/Fail Checklist

- [ ] **PASS:** Token authenticates (GET /user returns 200)
- [ ] **PASS:** Repository is accessible (GET /repos/{repo} returns 200)
- [ ] **PASS:** Workflows are listable (GET /actions/workflows returns 200)
- [ ] **PASS:** Dispatches can be triggered (POST /dispatches returns 204)
- [ ] **FAIL:** Token is expired or revoked (401 response)
- [ ] **FAIL:** Token lacks required scopes (403 response)
- [ ] **FAIL:** Repository does not exist or is inaccessible (404 response)

---

## 3. Manual Trigger Endpoint Validation

### AC-3.1: POST /api/v1/self-heal/trigger Processes Errors

**As a** developer
**I want** to manually trigger self-healing for a specific error
**So that** I can test the system or force processing of known issues

#### Acceptance Criteria

| ID | Criterion | Pass Condition | Fail Condition |
|----|-----------|----------------|----------------|
| AC-3.1.1 | Endpoint accepts valid payload | HTTP 200 OK | 4xx/5xx error |
| AC-3.1.2 | Response contains classification | `classification` object present | Field missing |
| AC-3.1.3 | Response contains action_taken | `action_taken` field present | Field missing |
| AC-3.1.4 | Response contains success status | `success` is boolean | Field missing |
| AC-3.1.5 | Classification includes error_hash | Unique hash string present | Missing or empty |
| AC-3.1.6 | Classification includes category | Valid ErrorCategory enum | Invalid or missing |
| AC-3.1.7 | Classification includes severity | Valid ErrorSeverity enum | Invalid or missing |

#### Test Commands

```bash
# Test 1: Basic trigger with minimal payload
curl -X POST http://localhost:8000/api/v1/self-heal/trigger \
     -H "Content-Type: application/json" \
     -d '{"error_message": "Test error for validation"}' | jq '.'

# Expected response structure:
# {
#   "classification": {
#     "error_hash": "abc123...",
#     "category": "unknown",
#     "severity": "error",
#     "recommended_action": "alert_only",
#     "confidence": 0.5,
#     "auto_fixable": false,
#     "root_cause_hint": null
#   },
#   "action_taken": "alert_only",
#   "success": true,
#   "details": "Alert sent, no auto-action taken"
# }

# Test 2: Trigger with full payload
curl -X POST http://localhost:8000/api/v1/self-heal/trigger \
     -H "Content-Type: application/json" \
     -d '{
       "error_message": "TypeError: Cannot read property foo of undefined",
       "file": "src/components/Dashboard.tsx",
       "line": 42,
       "trace_id": "test-trace-001",
       "stack_trace": "at Dashboard (Dashboard.tsx:42)\n  at renderWithHooks...",
       "metadata": {"source": "manual-test", "user": "qa-tester"}
     }' | jq '.'

# Test 3: Verify timeout errors get RETRY action
curl -X POST http://localhost:8000/api/v1/self-heal/trigger \
     -H "Content-Type: application/json" \
     -d '{"error_message": "Request timed out after 30000ms"}' \
     | jq -e '.classification.recommended_action == "retry"'
# Exit code 0 = PASS

# Test 4: Verify rate limit errors get CIRCUIT_BREAK action
curl -X POST http://localhost:8000/api/v1/self-heal/trigger \
     -H "Content-Type: application/json" \
     -d '{"error_message": "Error 429: Rate limit exceeded"}' \
     | jq -e '.classification.recommended_action == "circuit_break"'
# Exit code 0 = PASS
```

#### Pass/Fail Checklist

- [ ] **PASS:** Endpoint returns 200 for valid payloads
- [ ] **PASS:** Response contains all required fields
- [ ] **PASS:** Classification logic correctly identifies error patterns
- [ ] **PASS:** Action taken matches recommended action
- [ ] **FAIL:** Endpoint returns 422 for invalid payload
- [ ] **FAIL:** Response missing required classification fields
- [ ] **FAIL:** Action contradicts classification recommendation

---

## 4. Webhook Endpoint Validation

### AC-4.1: Sentry Webhook Accepts Payloads

**As a** Sentry integration
**I want** to send error webhooks to the self-heal endpoint
**So that** errors are automatically processed

#### Acceptance Criteria

| ID | Criterion | Pass Condition | Fail Condition |
|----|-----------|----------------|----------------|
| AC-4.1.1 | POST /self-heal/webhook/sentry returns 202 | HTTP 202 Accepted | Other status |
| AC-4.1.2 | Response includes status field | `status` is "accepted" or "ignored" | Field missing |
| AC-4.1.3 | Valid events are accepted | `status: "accepted"` for valid events | Rejected valid event |
| AC-4.1.4 | Invalid events are ignored | `status: "ignored"` with reason | Accepted invalid event |

#### Test Commands

```bash
# Test 1: Sentry error event
curl -X POST http://localhost:8000/api/v1/self-heal/webhook/sentry \
     -H "Content-Type: application/json" \
     -d '{
       "action": "created",
       "event": {
         "event_id": "abc123",
         "title": "TypeError in auth module",
         "exception": {
           "values": [{
             "type": "TypeError",
             "value": "Cannot read property of null",
             "stacktrace": {
               "frames": [{
                 "filename": "backend/app/services/auth.py",
                 "lineno": 55
               }]
             }
           }]
         }
       },
       "project": {"slug": "guilde-lite"}
     }' | jq '.'
# Expected: {"status": "accepted", "trigger_id": "abc123"}

# Test 2: Ignored event type
curl -X POST http://localhost:8000/api/v1/self-heal/webhook/sentry \
     -H "Content-Type: application/json" \
     -d '{"action": "assigned", "event": {}}' | jq '.'
# Expected: {"status": "ignored", "reason": "Event type 'assigned' not handled"}
```

### AC-4.2: Logfire Webhook Accepts Payloads

| ID | Criterion | Pass Condition | Fail Condition |
|----|-----------|----------------|----------------|
| AC-4.2.1 | POST /self-heal/webhook/logfire returns 202 | HTTP 202 Accepted | Other status |
| AC-4.2.2 | Error alerts are processed | `status: "accepted"` | Rejected valid alert |
| AC-4.2.3 | Non-error alerts are ignored | `status: "ignored"` | Processed non-error |

#### Test Commands

```bash
# Test 1: Logfire error alert
curl -X POST http://localhost:8000/api/v1/self-heal/webhook/logfire \
     -H "Content-Type: application/json" \
     -d '{
       "alert_type": "error",
       "message": "Database connection failed",
       "span": {
         "trace_id": "logfire-trace-001",
         "span_id": "span-abc",
         "attributes": {
           "code.filepath": "backend/app/db/session.py",
           "code.lineno": 28,
           "exception.message": "Connection refused",
           "exception.stacktrace": "...",
           "service.name": "guilde-backend"
         }
       }
     }' | jq '.'
# Expected: {"status": "accepted", "trace_id": "logfire-trace-001"}

# Test 2: Ignored alert type
curl -X POST http://localhost:8000/api/v1/self-heal/webhook/logfire \
     -H "Content-Type: application/json" \
     -d '{"alert_type": "info", "message": "Info message"}' | jq '.'
# Expected: {"status": "ignored", "reason": "Alert type 'info' not handled"}
```

### AC-4.3: Frontend Webhook Accepts Payloads

| ID | Criterion | Pass Condition | Fail Condition |
|----|-----------|----------------|----------------|
| AC-4.3.1 | POST /self-heal/webhook/frontend returns 202 | HTTP 202 Accepted | Other status |
| AC-4.3.2 | Frontend errors are accepted | `status: "accepted"` | Rejected |

#### Test Commands

```bash
# Test: Frontend error boundary payload
curl -X POST http://localhost:8000/api/v1/self-heal/webhook/frontend \
     -H "Content-Type: application/json" \
     -d '{
       "message": "ChunkLoadError: Loading chunk 5 failed",
       "digest": "frontend-001",
       "stack": "ChunkLoadError: Loading chunk 5 failed\n  at ...",
       "componentStack": "at Dashboard\n  at Layout",
       "url": "https://app.example.com/dashboard",
       "userAgent": "Mozilla/5.0 ..."
     }' | jq '.'
# Expected: {"status": "accepted", "digest": "frontend-001"}
```

#### Pass/Fail Checklist for All Webhooks

- [ ] **PASS:** All webhook endpoints return 202 Accepted for valid payloads
- [ ] **PASS:** Handled event types are accepted with trigger/trace ID
- [ ] **PASS:** Unhandled event types are ignored with reason
- [ ] **PASS:** Payloads are processed asynchronously (fast response)
- [ ] **FAIL:** Endpoint returns 4xx/5xx for valid payloads
- [ ] **FAIL:** Handled event types are incorrectly ignored
- [ ] **FAIL:** Response time exceeds 1 second (blocking issue)

---

## 5. Error Classification Validation

### AC-5.1: Error Classification Works Correctly

**As a** self-healing system
**I want** to correctly classify errors by category and severity
**So that** appropriate automated actions are taken

#### Acceptance Criteria

| ID | Criterion | Pass Condition | Fail Condition |
|----|-----------|----------------|----------------|
| AC-5.1.1 | Timeout errors classified correctly | `category: "timeout"`, `action: "retry"` | Wrong classification |
| AC-5.1.2 | Connection errors classified correctly | `category: "network"`, `action: "circuit_break"` | Wrong classification |
| AC-5.1.3 | Auth errors classified correctly | `category: "authentication"`, `action: "alert_only"` | Wrong classification |
| AC-5.1.4 | Type errors classified correctly | `category: "validation"`, `action: "create_pr"` | Wrong classification |
| AC-5.1.5 | Import errors classified correctly | `category: "dependency"`, `action: "create_issue"` | Wrong classification |
| AC-5.1.6 | Rate limit errors classified correctly | `category: "llm_api"`, `action: "circuit_break"` | Wrong classification |
| AC-5.1.7 | Unknown errors get default classification | `category: "unknown"`, `action: "alert_only"` | Wrong classification |

#### Test Matrix

```bash
# Run classification test suite
echo "Testing error classification matrix..."

# Test case 1: Timeout
RESULT=$(curl -s -X POST http://localhost:8000/api/v1/self-heal/trigger \
  -H "Content-Type: application/json" \
  -d '{"error_message": "Connection timed out after 30s"}')
echo "Timeout: $(echo $RESULT | jq '{category: .classification.category, action: .classification.recommended_action}')"
# Expected: {"category":"timeout","action":"retry"}

# Test case 2: Connection Refused
RESULT=$(curl -s -X POST http://localhost:8000/api/v1/self-heal/trigger \
  -H "Content-Type: application/json" \
  -d '{"error_message": "ConnectionError: Connection refused to localhost:5432"}')
echo "Connection: $(echo $RESULT | jq '{category: .classification.category, action: .classification.recommended_action}')"
# Expected: {"category":"network","action":"circuit_break"}

# Test case 3: Unauthorized
RESULT=$(curl -s -X POST http://localhost:8000/api/v1/self-heal/trigger \
  -H "Content-Type: application/json" \
  -d '{"error_message": "401 Unauthorized: Invalid token"}')
echo "Auth: $(echo $RESULT | jq '{category: .classification.category, action: .classification.recommended_action}')"
# Expected: {"category":"authentication","action":"alert_only"}

# Test case 4: TypeError
RESULT=$(curl -s -X POST http://localhost:8000/api/v1/self-heal/trigger \
  -H "Content-Type: application/json" \
  -d '{"error_message": "TypeError: Cannot read property length of undefined"}')
echo "TypeError: $(echo $RESULT | jq '{category: .classification.category, action: .classification.recommended_action}')"
# Expected: {"category":"validation","action":"create_pr"}

# Test case 5: ImportError
RESULT=$(curl -s -X POST http://localhost:8000/api/v1/self-heal/trigger \
  -H "Content-Type: application/json" \
  -d '{"error_message": "ImportError: No module named pydantic_ai"}')
echo "Import: $(echo $RESULT | jq '{category: .classification.category, action: .classification.recommended_action}')"
# Expected: {"category":"dependency","action":"create_issue"}

# Test case 6: Rate Limit
RESULT=$(curl -s -X POST http://localhost:8000/api/v1/self-heal/trigger \
  -H "Content-Type: application/json" \
  -d '{"error_message": "Error 429: Rate limit exceeded for API calls"}')
echo "Rate Limit: $(echo $RESULT | jq '{category: .classification.category, action: .classification.recommended_action}')"
# Expected: {"category":"llm_api","action":"circuit_break"}

# Test case 7: Permission Denied
RESULT=$(curl -s -X POST http://localhost:8000/api/v1/self-heal/trigger \
  -H "Content-Type: application/json" \
  -d '{"error_message": "403 Forbidden: Permission denied to access resource"}')
echo "Permission: $(echo $RESULT | jq '{category: .classification.category, action: .classification.recommended_action}')"
# Expected: {"category":"authorization","action":"create_issue"}

# Test case 8: Unknown Error
RESULT=$(curl -s -X POST http://localhost:8000/api/v1/self-heal/trigger \
  -H "Content-Type: application/json" \
  -d '{"error_message": "Something unexpected happened"}')
echo "Unknown: $(echo $RESULT | jq '{category: .classification.category, action: .classification.recommended_action}')"
# Expected: {"category":"unknown","action":"alert_only"}
```

#### Classification Action Matrix

| Error Pattern | Expected Category | Expected Action | Confidence |
|---------------|-------------------|-----------------|------------|
| `timeout`, `timed out` | `timeout` | `retry` | 0.9 |
| `connection refused`, `connectionerror` | `network` | `circuit_break` | 0.85 |
| `401`, `unauthorized` | `authentication` | `alert_only` | 0.9 |
| `typeerror`, `attributeerror` | `validation` | `create_pr` | 0.7 |
| `importerror`, `modulenotfounderror` | `dependency` | `create_issue` | 0.8 |
| `rate limit`, `429` | `llm_api` | `circuit_break` | 0.95 |
| `websocket` | `network` | `create_pr` | 0.6 |
| `permission`, `403` | `authorization` | `create_issue` | 0.85 |
| Other | `unknown` | `alert_only` | 0.5 |

#### Pass/Fail Checklist

- [ ] **PASS:** All error patterns in matrix are classified correctly
- [ ] **PASS:** Confidence scores match expected thresholds
- [ ] **PASS:** Auto-fixable flag set correctly for TypeErrors
- [ ] **PASS:** Root cause hints provided for known patterns
- [ ] **FAIL:** Error pattern misclassified
- [ ] **FAIL:** Wrong action recommended for error type
- [ ] **FAIL:** Confidence outside expected range

---

## 6. End-to-End Integration Validation

### AC-6.1: Full Workflow Integration Test

**As a** system operator
**I want** to verify the complete self-healing workflow
**So that** I know the system works end-to-end in production

#### Test Script

```bash
#!/bin/bash
# Full integration test script
# Save as: test-self-heal-integration.sh

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
GITHUB_REPO="${GITHUB_REPO:-$(grep GITHUB_REPO .env 2>/dev/null | cut -d= -f2)}"

echo "=============================================="
echo "AI Self-Healing Integration Test"
echo "Base URL: $BASE_URL"
echo "GitHub Repo: $GITHUB_REPO"
echo "=============================================="
echo ""

PASS_COUNT=0
FAIL_COUNT=0

check_result() {
  local test_name="$1"
  local condition="$2"
  if [ "$condition" = "true" ]; then
    echo "[PASS] $test_name"
    ((PASS_COUNT++))
  else
    echo "[FAIL] $test_name"
    ((FAIL_COUNT++))
  fi
}

# Test 1: Status endpoint
echo "--- Test 1: Status Endpoint ---"
STATUS=$(curl -s "$BASE_URL/api/v1/self-heal/status")
check_result "Status endpoint returns 200" "$(echo $STATUS | jq -e '.enabled != null' >/dev/null 2>&1 && echo true || echo false)"
check_result "Enabled field is boolean" "$(echo $STATUS | jq -e '.enabled | type == "boolean"' >/dev/null 2>&1 && echo true || echo false)"
check_result "GitHub repo configured" "$(echo $STATUS | jq -e '.github_repo != null' >/dev/null 2>&1 && echo true || echo false)"
echo ""

# Test 2: Manual trigger
echo "--- Test 2: Manual Trigger ---"
TRIGGER=$(curl -s -X POST "$BASE_URL/api/v1/self-heal/trigger" \
  -H "Content-Type: application/json" \
  -d '{"error_message": "Integration test error"}')
check_result "Trigger returns classification" "$(echo $TRIGGER | jq -e '.classification' >/dev/null 2>&1 && echo true || echo false)"
check_result "Trigger returns action_taken" "$(echo $TRIGGER | jq -e '.action_taken' >/dev/null 2>&1 && echo true || echo false)"
check_result "Trigger returns success status" "$(echo $TRIGGER | jq -e '.success' >/dev/null 2>&1 && echo true || echo false)"
echo ""

# Test 3: Sentry webhook
echo "--- Test 3: Sentry Webhook ---"
SENTRY=$(curl -s -X POST "$BASE_URL/api/v1/self-heal/webhook/sentry" \
  -H "Content-Type: application/json" \
  -d '{"action": "created", "event": {"event_id": "test", "title": "Test"}}')
check_result "Sentry webhook accepts payload" "$(echo $SENTRY | jq -e '.status == "accepted"' >/dev/null 2>&1 && echo true || echo false)"
echo ""

# Test 4: Logfire webhook
echo "--- Test 4: Logfire Webhook ---"
LOGFIRE=$(curl -s -X POST "$BASE_URL/api/v1/self-heal/webhook/logfire" \
  -H "Content-Type: application/json" \
  -d '{"alert_type": "error", "span": {"trace_id": "test"}}')
check_result "Logfire webhook accepts payload" "$(echo $LOGFIRE | jq -e '.status == "accepted"' >/dev/null 2>&1 && echo true || echo false)"
echo ""

# Test 5: Frontend webhook
echo "--- Test 5: Frontend Webhook ---"
FRONTEND=$(curl -s -X POST "$BASE_URL/api/v1/self-heal/webhook/frontend" \
  -H "Content-Type: application/json" \
  -d '{"message": "Test error", "digest": "test-001"}')
check_result "Frontend webhook accepts payload" "$(echo $FRONTEND | jq -e '.status == "accepted"' >/dev/null 2>&1 && echo true || echo false)"
echo ""

# Test 6: Error classification
echo "--- Test 6: Error Classification ---"
TIMEOUT=$(curl -s -X POST "$BASE_URL/api/v1/self-heal/trigger" \
  -H "Content-Type: application/json" \
  -d '{"error_message": "Request timed out"}')
check_result "Timeout classified as timeout" "$(echo $TIMEOUT | jq -e '.classification.category == "timeout"' >/dev/null 2>&1 && echo true || echo false)"
check_result "Timeout action is retry" "$(echo $TIMEOUT | jq -e '.classification.recommended_action == "retry"' >/dev/null 2>&1 && echo true || echo false)"

RATE=$(curl -s -X POST "$BASE_URL/api/v1/self-heal/trigger" \
  -H "Content-Type: application/json" \
  -d '{"error_message": "429 Rate limit exceeded"}')
check_result "Rate limit classified correctly" "$(echo $RATE | jq -e '.classification.category == "llm_api"' >/dev/null 2>&1 && echo true || echo false)"
check_result "Rate limit action is circuit_break" "$(echo $RATE | jq -e '.classification.recommended_action == "circuit_break"' >/dev/null 2>&1 && echo true || echo false)"
echo ""

# Summary
echo "=============================================="
echo "TEST SUMMARY"
echo "=============================================="
echo "Passed: $PASS_COUNT"
echo "Failed: $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
  echo "ALL TESTS PASSED"
  exit 0
else
  echo "SOME TESTS FAILED"
  exit 1
fi
```

#### Pass/Fail Checklist

- [ ] **PASS:** All integration tests pass (exit code 0)
- [ ] **PASS:** All endpoints respond within 2 seconds
- [ ] **PASS:** No 5xx errors during test run
- [ ] **PASS:** Classification results are deterministic
- [ ] **FAIL:** Any integration test fails
- [ ] **FAIL:** Endpoints timeout or return errors
- [ ] **FAIL:** Inconsistent classification results

---

## Summary Checklist

### Prerequisites

- [ ] Backend server running on port 8000
- [ ] `GITHUB_TOKEN` environment variable set
- [ ] `GITHUB_REPO` environment variable set (format: `owner/repo`)
- [ ] `SELF_HEAL_ENABLED=true` in configuration

### Validation Checklist

| # | Validation | Status | Notes |
|---|------------|--------|-------|
| 1 | GET /api/v1/self-heal/status returns enabled=true | [ ] | |
| 2 | GITHUB_TOKEN authenticates with GitHub API | [ ] | |
| 3 | POST /api/v1/self-heal/trigger works | [ ] | |
| 4 | Sentry webhook endpoint accepts payloads | [ ] | |
| 5 | Logfire webhook endpoint accepts payloads | [ ] | |
| 6 | Frontend webhook endpoint accepts payloads | [ ] | |
| 7 | Timeout errors get RETRY action | [ ] | |
| 8 | Connection errors get CIRCUIT_BREAK action | [ ] | |
| 9 | Auth errors get ALERT_ONLY action | [ ] | |
| 10 | Type errors get CREATE_PR action | [ ] | |
| 11 | Import errors get CREATE_ISSUE action | [ ] | |
| 12 | Rate limit errors get CIRCUIT_BREAK action | [ ] | |
| 13 | End-to-end integration test passes | [ ] | |

### Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| QA Engineer | | | |
| DevOps Lead | | | |
| Tech Lead | | | |
