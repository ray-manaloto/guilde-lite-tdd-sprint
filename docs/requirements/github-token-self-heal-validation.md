# Requirements: GITHUB_TOKEN Self-Healing System Validation

## Overview

This document defines user stories and testable acceptance criteria for validating that the AI self-healing system is correctly configured with `GITHUB_TOKEN` and can successfully communicate with the GitHub API.

## Business Context

The self-healing system requires a valid `GITHUB_TOKEN` to:
- Trigger GitHub Actions workflows via `repository_dispatch` events
- Create GitHub issues for errors requiring human attention
- Authenticate API calls to `api.github.com`

Without proper token configuration, the self-healing system cannot perform automated remediation actions.

---

## User Story 1: Token is Loaded from .env into Settings

**As a** backend developer
**I want** the `GITHUB_TOKEN` to be loaded from the `.env` file into application settings
**So that** the self-healing service can authenticate with the GitHub API

### Acceptance Criteria

**Scenario 1.1: GITHUB_TOKEN setting exists in config**
**Given** the Settings class in `backend/app/core/config.py`
**When** I examine the class definition
**Then** there should be a `GITHUB_TOKEN: str | None = None` field defined

**Test Command:**
```bash
grep -n "GITHUB_TOKEN" backend/app/core/config.py
```
**Expected Output:** Line containing `GITHUB_TOKEN: str | None = None`

---

**Scenario 1.2: GITHUB_TOKEN is loaded from environment**
**Given** the `.env` file contains `GITHUB_TOKEN=ghp_xxxxxxxxxxxx`
**When** the Settings instance is created
**Then** `settings.GITHUB_TOKEN` should equal the value from `.env`

**Test Command:**
```python
# In Python REPL or test file
from app.core.config import settings
assert settings.GITHUB_TOKEN is not None
assert settings.GITHUB_TOKEN.startswith("ghp_") or settings.GITHUB_TOKEN.startswith("github_pat_")
print(f"Token loaded: {settings.GITHUB_TOKEN[:10]}...")
```

---

**Scenario 1.3: Settings validation does not reject missing token**
**Given** the `.env` file does NOT contain `GITHUB_TOKEN`
**When** the Settings instance is created
**Then** `settings.GITHUB_TOKEN` should be `None` (not raise ValidationError)

**Test Command:**
```python
# With GITHUB_TOKEN removed from .env
from app.core.config import Settings
s = Settings(_env_file=None, GITHUB_TOKEN=None, ...)  # explicit None
assert s.GITHUB_TOKEN is None
```

---

**Scenario 1.4: SelfHealService receives token from settings**
**Given** `settings.GITHUB_TOKEN` is set to a valid token
**When** `SelfHealService()` is instantiated without explicit parameters
**Then** `service.github_token` should equal `settings.GITHUB_TOKEN`

**Test Command:**
```python
from app.core.config import settings
from app.services.self_heal import SelfHealService

service = SelfHealService()
assert service.github_token == settings.GITHUB_TOKEN
```

### Notes
- The token is optional at the config level but required for GitHub operations
- Token format: Classic tokens start with `ghp_`, fine-grained tokens start with `github_pat_`
- Token should have `repo` scope for repository_dispatch and `issues:write` for creating issues

### Priority
**Must Have**

---

## User Story 2: GET /api/v1/self-heal/status Returns enabled=true

**As a** DevOps engineer
**I want** the status endpoint to report `enabled=true` when credentials are configured
**So that** I can verify the self-healing system is ready to operate

### Acceptance Criteria

**Scenario 2.1: Status returns enabled=true with valid credentials**
**Given** the backend is running
**And** `GITHUB_TOKEN` is set in environment
**And** `GITHUB_REPO` is set to a valid repository (e.g., `pagerguild/guilde-lite-tdd-sprint`)
**When** I GET `/api/v1/self-heal/status`
**Then** the response status code should be `200`
**And** the response body should contain `"enabled": true`

**Test Command:**
```bash
curl -s http://localhost:8000/api/v1/self-heal/status | jq '.enabled'
```
**Expected Output:** `true`

---

**Scenario 2.2: Status returns enabled=false without token**
**Given** the backend is running
**And** `GITHUB_TOKEN` is NOT set or is empty
**When** I GET `/api/v1/self-heal/status`
**Then** the response status code should be `200`
**And** the response body should contain `"enabled": false`

**Test Command:**
```bash
# With GITHUB_TOKEN unset
GITHUB_TOKEN="" curl -s http://localhost:8000/api/v1/self-heal/status | jq '.enabled'
```
**Expected Output:** `false`

---

**Scenario 2.3: Status returns enabled=false without repo**
**Given** the backend is running
**And** `GITHUB_TOKEN` is set
**And** `GITHUB_REPO` is NOT set or is empty
**When** I GET `/api/v1/self-heal/status`
**Then** the response body should contain `"enabled": false`

**Test Command:**
```bash
# With GITHUB_REPO unset
curl -s http://localhost:8000/api/v1/self-heal/status | jq '.enabled'
```
**Expected Output:** `false`

---

**Scenario 2.4: Status response includes all required fields**
**Given** the backend is running
**When** I GET `/api/v1/self-heal/status`
**Then** the response should contain the following fields:
- `enabled` (boolean)
- `github_repo` (string or null)
- `active_circuits` (integer)
- `error_patterns_seen` (integer)

**Test Command:**
```bash
curl -s http://localhost:8000/api/v1/self-heal/status | jq 'keys'
```
**Expected Output:** `["active_circuits", "enabled", "error_patterns_seen", "github_repo"]`

---

**Scenario 2.5: Status endpoint requires no authentication**
**Given** the backend is running
**When** I GET `/api/v1/self-heal/status` without any auth headers
**Then** the response status code should be `200` (not `401` or `403`)

**Test Command:**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/self-heal/status
```
**Expected Output:** `200`

### Notes
- The `enabled` flag is computed as `bool(service.github_token and service.github_repo)`
- This endpoint is useful for health checks and monitoring dashboards
- Consider adding more diagnostic fields (e.g., `token_valid`, `last_action_timestamp`)

### Priority
**Must Have**

---

## User Story 3: GitHub API Calls Work (Can Reach api.github.com)

**As a** backend developer
**I want** to verify that the application can successfully communicate with the GitHub API
**So that** I can confirm network connectivity and token validity

### Acceptance Criteria

**Scenario 3.1: GitHub API is reachable from application**
**Given** the application has network access
**When** I make an HTTP request to `https://api.github.com`
**Then** the response status code should be `200`
**And** the response should contain GitHub API metadata

**Test Command:**
```bash
curl -s -o /dev/null -w "%{http_code}" https://api.github.com
```
**Expected Output:** `200`

---

**Scenario 3.2: Token authenticates successfully with GitHub API**
**Given** `GITHUB_TOKEN` is set to a valid token
**When** I make an authenticated request to `https://api.github.com/user`
**Then** the response status code should be `200`
**And** the response should contain the authenticated user's information

**Test Command:**
```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     https://api.github.com/user | jq '.login'
```
**Expected Output:** The GitHub username associated with the token

---

**Scenario 3.3: Token has required repository scope**
**Given** `GITHUB_TOKEN` is set
**When** I check the token's scopes via the API response headers
**Then** the `X-OAuth-Scopes` header should include `repo` or the token should be a fine-grained PAT with repository access

**Test Command:**
```bash
curl -sI -H "Authorization: Bearer $GITHUB_TOKEN" \
     https://api.github.com/user | grep -i "x-oauth-scopes"
```
**Expected Output:** Line containing `repo` (for classic tokens)

---

**Scenario 3.4: Token can access target repository**
**Given** `GITHUB_TOKEN` and `GITHUB_REPO` are set
**When** I make an authenticated request to `https://api.github.com/repos/{GITHUB_REPO}`
**Then** the response status code should be `200`
**And** the response should contain repository metadata

**Test Command:**
```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/$GITHUB_REPO" | jq '.full_name'
```
**Expected Output:** The repository full name (e.g., `"pagerguild/guilde-lite-tdd-sprint"`)

---

**Scenario 3.5: Invalid token returns 401 Unauthorized**
**Given** an invalid or expired token is used
**When** I make an authenticated request to `https://api.github.com/user`
**Then** the response status code should be `401`

**Test Command:**
```bash
curl -s -o /dev/null -w "%{http_code}" \
     -H "Authorization: Bearer ghp_invalid_token_12345" \
     https://api.github.com/user
```
**Expected Output:** `401`

---

**Scenario 3.6: Rate limit headers are present**
**Given** `GITHUB_TOKEN` is set
**When** I make an authenticated request to the GitHub API
**Then** the response should include rate limit headers:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

**Test Command:**
```bash
curl -sI -H "Authorization: Bearer $GITHUB_TOKEN" \
     https://api.github.com/user | grep -i "x-ratelimit"
```
**Expected Output:** Three lines with rate limit information

### Notes
- GitHub API rate limits: 5000 requests/hour for authenticated users
- Fine-grained PATs require explicit repository permissions
- Network issues may require proxy configuration

### Priority
**Must Have**

---

## User Story 4: Manual Trigger Creates Action in GitHub

**As a** QA engineer
**I want** to verify that the manual trigger endpoint successfully dispatches a GitHub Action
**So that** I can confirm the end-to-end self-healing flow works

### Acceptance Criteria

**Scenario 4.1: Manual trigger sends repository dispatch event**
**Given** the backend is running with valid `GITHUB_TOKEN` and `GITHUB_REPO`
**When** I POST to `/api/v1/self-heal/trigger` with:
```json
{
  "error_message": "TypeError: Cannot read property 'test' of undefined",
  "file": "src/test/validation.ts",
  "line": 42
}
```
**Then** the response `success` field should be `true`
**And** the response `action_taken` should be `"create_pr"`
**And** the response `details` should contain `"Auto-fix workflow triggered"`

**Test Command:**
```bash
curl -s -X POST http://localhost:8000/api/v1/self-heal/trigger \
     -H "Content-Type: application/json" \
     -d '{
       "error_message": "TypeError: Cannot read property test of undefined",
       "file": "src/test/validation.ts",
       "line": 42
     }' | jq '{success, action_taken, details}'
```
**Expected Output:**
```json
{
  "success": true,
  "action_taken": "create_pr",
  "details": "Auto-fix workflow triggered"
}
```

---

**Scenario 4.2: GitHub Actions workflow is triggered**
**Given** a successful trigger response was received
**When** I check the GitHub Actions tab for the repository
**Then** a new workflow run for "AI Self-Heal" should appear within 30 seconds
**And** the workflow should show `repository_dispatch` as the trigger event

**Verification Steps:**
1. Navigate to `https://github.com/{GITHUB_REPO}/actions`
2. Find the "AI Self-Heal" workflow
3. Verify a new run was triggered with event type `repository_dispatch`

**Test Command (via API):**
```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/$GITHUB_REPO/actions/runs?event=repository_dispatch&per_page=1" \
     | jq '.workflow_runs[0] | {name, event, created_at, status}'
```

---

**Scenario 4.3: Workflow receives correct payload**
**Given** a repository dispatch was triggered with error context
**When** the workflow runs
**Then** the `client_payload` should contain:
- `error_message`: The original error message
- `file`: The file path
- `line`: The line number
- `timestamp`: ISO timestamp of the trigger

**Verification:** Check workflow run logs for the "Extract error context" step

---

**Scenario 4.4: Low confidence errors create issues instead**
**Given** the backend is running
**When** I POST a permission error (low confidence for auto-fix):
```json
{
  "error_message": "403 Forbidden: Access denied",
  "file": "app/api/admin.py",
  "line": 10
}
```
**Then** the response `action_taken` should be `"create_issue"`
**And** a new issue should be created in the GitHub repository

**Test Command:**
```bash
curl -s -X POST http://localhost:8000/api/v1/self-heal/trigger \
     -H "Content-Type: application/json" \
     -d '{
       "error_message": "403 Forbidden: Access denied",
       "file": "app/api/admin.py",
       "line": 10
     }' | jq '{action_taken, details}'
```
**Expected Output:**
```json
{
  "action_taken": "create_issue",
  "details": "Issue created: https://github.com/..."
}
```

---

**Scenario 4.5: Missing credentials returns failure**
**Given** `GITHUB_TOKEN` is not set
**When** I POST to `/api/v1/self-heal/trigger` with an auto-fixable error
**Then** the response `success` field should be `false`
**And** the response `details` should indicate the failure reason

**Test Command:**
```bash
# With GITHUB_TOKEN unset in the running server
curl -s -X POST http://localhost:8000/api/v1/self-heal/trigger \
     -H "Content-Type: application/json" \
     -d '{"error_message": "TypeError: test"}' | jq '{success, details}'
```
**Expected Output:**
```json
{
  "success": false,
  "details": "Failed to trigger workflow"
}
```

---

**Scenario 4.6: Repository dispatch returns 204 No Content**
**Given** valid credentials are configured
**When** the service calls `POST /repos/{owner}/{repo}/dispatches`
**Then** GitHub should return HTTP status `204 No Content`

**Direct API Test:**
```bash
curl -s -o /dev/null -w "%{http_code}" -X POST \
     -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     -H "X-GitHub-Api-Version: 2022-11-28" \
     "https://api.github.com/repos/$GITHUB_REPO/dispatches" \
     -d '{"event_type":"test-event","client_payload":{"test":true}}'
```
**Expected Output:** `204`

### Notes
- Repository dispatch is fire-and-forget; 204 means accepted, not completed
- Workflow execution is asynchronous; verify via Actions API or UI
- The `ai-self-heal.yml` workflow must be committed to the default branch

### Priority
**Must Have**

---

## Functional Requirements Summary

| ID | Requirement | User Story |
|----|-------------|------------|
| FR-001 | `GITHUB_TOKEN` must be loadable from `.env` into Settings | US-1 |
| FR-002 | `GITHUB_TOKEN` must be passed to SelfHealService | US-1 |
| FR-003 | Status endpoint must return `enabled=true` when credentials valid | US-2 |
| FR-004 | Status endpoint must return `enabled=false` when credentials missing | US-2 |
| FR-005 | Application must be able to reach `api.github.com` | US-3 |
| FR-006 | Token must authenticate successfully with GitHub API | US-3 |
| FR-007 | Token must have access to target repository | US-3 |
| FR-008 | Manual trigger must dispatch `repository_dispatch` event | US-4 |
| FR-009 | GitHub Actions workflow must be triggered by dispatch | US-4 |
| FR-010 | Workflow must receive error context in payload | US-4 |

## Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-001 | Security | `GITHUB_TOKEN` must never be logged or returned in API responses |
| NFR-002 | Security | Token should use minimum required scopes (`repo` for dispatch, `issues:write` for issues) |
| NFR-003 | Performance | GitHub API calls should timeout after 30 seconds |
| NFR-004 | Reliability | Failed GitHub calls should not crash the application |
| NFR-005 | Observability | All GitHub API calls should be logged with trace IDs |

## Constraints

- GitHub API rate limit: 5000 requests/hour per authenticated user
- Repository dispatch requires the workflow file on the default branch
- Fine-grained PATs require explicit repository selection

## Assumptions

- GitHub Actions is enabled for the target repository
- The `ai-self-heal.yml` workflow file exists in `.github/workflows/`
- Network allows outbound HTTPS connections to `api.github.com`

## Dependencies

- GitHub API availability
- Valid GitHub Personal Access Token (classic or fine-grained)
- Target repository with Actions enabled

## Out of Scope

- Token rotation/refresh mechanisms
- GitHub App authentication (vs PAT)
- Webhook secret validation
- GitHub Enterprise Server support

---

## Validation Script

Save as `tools/github-validation/validate-self-heal-config.sh`:

```bash
#!/bin/bash
# Validate GITHUB_TOKEN and self-heal configuration

set -e

echo "=== Self-Heal Configuration Validation ==="
echo ""

# Check 1: Token is set
echo "1. Checking GITHUB_TOKEN environment variable..."
if [ -z "$GITHUB_TOKEN" ]; then
    echo "   FAIL: GITHUB_TOKEN is not set"
    exit 1
else
    echo "   PASS: GITHUB_TOKEN is set (${GITHUB_TOKEN:0:10}...)"
fi

# Check 2: Token authenticates
echo ""
echo "2. Validating token with GitHub API..."
USER_RESPONSE=$(curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    https://api.github.com/user)

if echo "$USER_RESPONSE" | jq -e '.login' > /dev/null 2>&1; then
    LOGIN=$(echo "$USER_RESPONSE" | jq -r '.login')
    echo "   PASS: Authenticated as $LOGIN"
else
    echo "   FAIL: Authentication failed"
    echo "   Response: $USER_RESPONSE"
    exit 1
fi

# Check 3: Repository access
echo ""
echo "3. Checking repository access..."
if [ -z "$GITHUB_REPO" ]; then
    echo "   SKIP: GITHUB_REPO not set"
else
    REPO_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/$GITHUB_REPO")

    if [ "$REPO_RESPONSE" = "200" ]; then
        echo "   PASS: Can access $GITHUB_REPO"
    else
        echo "   FAIL: Cannot access $GITHUB_REPO (HTTP $REPO_RESPONSE)"
        exit 1
    fi
fi

# Check 4: Status endpoint
echo ""
echo "4. Checking self-heal status endpoint..."
if [ -z "$BACKEND_URL" ]; then
    BACKEND_URL="http://localhost:8000"
fi

STATUS_RESPONSE=$(curl -s "$BACKEND_URL/api/v1/self-heal/status" 2>/dev/null || echo '{"error": "unreachable"}')

if echo "$STATUS_RESPONSE" | jq -e '.enabled' > /dev/null 2>&1; then
    ENABLED=$(echo "$STATUS_RESPONSE" | jq -r '.enabled')
    echo "   Status: enabled=$ENABLED"
    if [ "$ENABLED" = "true" ]; then
        echo "   PASS: Self-heal is enabled"
    else
        echo "   WARN: Self-heal is disabled (check GITHUB_REPO)"
    fi
else
    echo "   SKIP: Backend not reachable at $BACKEND_URL"
fi

# Check 5: Repository dispatch permission
echo ""
echo "5. Testing repository dispatch (dry-run)..."
if [ -n "$GITHUB_REPO" ]; then
    # Note: This actually triggers a workflow if valid
    # Use with caution or implement a no-op event type
    echo "   INFO: Skipping actual dispatch test (would trigger workflow)"
    echo "   Manual test: POST to /api/v1/self-heal/trigger"
fi

echo ""
echo "=== Validation Complete ==="
```

---

## Test Execution Checklist

- [ ] **US-1.1**: `GITHUB_TOKEN` field exists in `config.py`
- [ ] **US-1.2**: Token loads from `.env` into settings
- [ ] **US-1.3**: Missing token does not crash application
- [ ] **US-1.4**: SelfHealService receives token from settings
- [ ] **US-2.1**: Status returns `enabled=true` with credentials
- [ ] **US-2.2**: Status returns `enabled=false` without token
- [ ] **US-2.3**: Status returns `enabled=false` without repo
- [ ] **US-2.4**: Status response includes all required fields
- [ ] **US-2.5**: Status endpoint requires no authentication
- [ ] **US-3.1**: GitHub API is reachable
- [ ] **US-3.2**: Token authenticates successfully
- [ ] **US-3.3**: Token has repository scope
- [ ] **US-3.4**: Token can access target repository
- [ ] **US-3.5**: Invalid token returns 401
- [ ] **US-3.6**: Rate limit headers are present
- [ ] **US-4.1**: Manual trigger sends dispatch event
- [ ] **US-4.2**: GitHub Actions workflow is triggered
- [ ] **US-4.3**: Workflow receives correct payload
- [ ] **US-4.4**: Low confidence errors create issues
- [ ] **US-4.5**: Missing credentials returns failure
- [ ] **US-4.6**: Repository dispatch returns 204
