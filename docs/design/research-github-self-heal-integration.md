# Research Report: GitHub Integration for Self-Healing System

## Executive Summary

This report evaluates the technical feasibility of validating GitHub integration for the AI self-healing system at `ray-manaloto/guilde-lite-tdd-sprint`. The existing `ai-self-heal.yml` workflow is well-structured but requires specific GitHub secrets and permissions to function. Testing can be performed safely via `workflow_dispatch` with mock error data.

**Key Findings:**
- **CRITICAL:** The `ai-self-heal.yml` workflow exists locally but has NOT been pushed to `ray-manaloto/guilde-lite-tdd-sprint` remote yet
- The workflow requires `ANTHROPIC_API_KEY` secret to be configured
- Workflow permissions are correctly set (`contents: write`, `pull-requests: write`, `issues: write`)
- `repository_dispatch` requires a PAT with `Contents: write` permission for external triggers
- The `claude-code-action@v1` has minimal configuration requirements
- The `claude_args` format in the current workflow needs correction (should use CLI flags, not JSON)

## Research Questions

1. What GitHub token permissions are needed for `repository_dispatch` and issue creation?
2. How to verify GitHub secrets are properly configured?
3. How to test the `ai-self-heal.yml` workflow without triggering a real error?
4. What's the minimum configuration needed for `claude-code-action` to work?

---

## Findings

### 1. GitHub Token Permissions for `repository_dispatch`

#### For External Systems (Sentry/Logfire Webhooks)

| Token Type | Required Permissions | Notes |
|------------|---------------------|-------|
| **Fine-Grained PAT** | `Contents: write` | Primary permission for `repository_dispatch` |
| **Classic PAT** | `repo` scope | Full repository access (broader) |
| **GitHub App** | `contents: read/write`, `actions: read/write`, `metadata: read` | For integrations |

**Critical Insight:** The `repository_dispatch` endpoint requires `Contents: write` permission specifically. The `actions: write` permission is for `workflow_dispatch`, not `repository_dispatch`.

#### For Issue Creation (within workflow)

The workflow already has correct permissions:
```yaml
permissions:
  contents: write      # For creating branches, commits
  pull-requests: write # For creating PRs
  issues: write        # For creating/updating issues
```

These are granted to `GITHUB_TOKEN` automatically since they're declared in the workflow.

#### API Endpoint Details

```bash
# repository_dispatch (for external webhooks)
POST /repos/{owner}/{repo}/dispatches
Authorization: Bearer <PAT_with_contents_write>
Content-Type: application/json

{
  "event_type": "error-detected",
  "client_payload": {
    "error_message": "...",
    "file": "...",
    "line": "...",
    "trace_id": "..."
  }
}
```

**Sources:**
- [GitHub Docs: repository_dispatch](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
- [Fine-grained PAT for dispatch](https://www.eliostruyf.com/dispatch-github-action-fine-grained-personal-access-token/)
- [GitHub Community Discussion #58868](https://github.com/orgs/community/discussions/58868)

---

### 2. Verifying GitHub Secrets Configuration

#### Method A: Workflow-Based Validation (Recommended)

Add a validation step that checks if secrets exist without exposing them:

```yaml
- name: Validate required secrets
  run: |
    if [ -z "$ANTHROPIC_API_KEY" ]; then
      echo "::error::ANTHROPIC_API_KEY secret is not configured"
      exit 1
    fi
    echo "ANTHROPIC_API_KEY is configured (length: ${#ANTHROPIC_API_KEY} chars)"
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

#### Method B: GitHub API Check

```bash
# List repository secrets (requires admin PAT)
gh api repos/ray-manaloto/guilde-lite-tdd-sprint/actions/secrets

# Expected response includes:
# { "total_count": N, "secrets": [{"name": "ANTHROPIC_API_KEY", ...}] }
```

#### Method C: Conditional Step Execution

```yaml
- name: Check secret exists
  id: check-secret
  run: echo "has_key=${{ secrets.ANTHROPIC_API_KEY != '' }}" >> $GITHUB_OUTPUT

- name: Fail if secret missing
  if: steps.check-secret.outputs.has_key != 'true'
  run: |
    echo "::error::Required secret ANTHROPIC_API_KEY is not configured"
    exit 1
```

**Important Limitations:**
- Secrets cannot be used in job-level `if:` conditions directly
- Must convert to environment variable first
- Secrets from forks are not available (security feature)

**Sources:**
- [GitHub Docs: Using secrets](https://docs.github.com/actions/security-guides/using-secrets-in-github-actions)
- [GitHub Community: Testing secrets in actions](https://github.com/orgs/community/discussions/26726)

---

### 3. Testing the Workflow Without Real Errors

#### Option A: Manual Trigger via GitHub UI (Safest)

1. Navigate to: `https://github.com/ray-manaloto/guilde-lite-tdd-sprint/actions/workflows/ai-self-heal.yml`
2. Click "Run workflow"
3. Enter mock test data:
   - **error_message:** `Test: Division by zero in calculate_total()`
   - **error_file:** `backend/app/services/calculator.py`
   - **error_line:** `42`

This uses `workflow_dispatch` which is already configured in the workflow.

#### Option B: GitHub CLI Trigger

```bash
gh workflow run ai-self-heal.yml \
  -R ray-manaloto/guilde-lite-tdd-sprint \
  -f error_message="Test: Mock validation error for integration testing" \
  -f error_file="backend/app/test_file.py" \
  -f error_line="1"
```

#### Option C: Create Test Issue with `ai-fix` Label

```bash
# Create a test issue
gh issue create \
  -R ray-manaloto/guilde-lite-tdd-sprint \
  --title "[Test] AI Self-Heal Validation" \
  --body "This is a test issue to validate the AI self-healing workflow.

**Expected behavior:** Claude should analyze this issue and provide recommendations.

**Test Context:**
- File: backend/app/services/test_service.py
- Error: Mock ImportError for testing
- This is NOT a real bug." \
  --label "ai-fix"
```

#### Option D: Simulate `repository_dispatch` (Requires PAT)

```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_PAT" \
  https://api.github.com/repos/ray-manaloto/guilde-lite-tdd-sprint/dispatches \
  -d '{
    "event_type": "error-detected",
    "client_payload": {
      "error_message": "TEST: Mock error for validation",
      "file": "backend/app/test.py",
      "line": "1",
      "trace_id": "test-trace-12345"
    }
  }'
```

**Important Note:** The workflow must be on the default branch (main) for `workflow_dispatch` to appear in the Actions UI.

**Sources:**
- [GitHub Actions workflow_dispatch](https://graphite.com/guides/github-actions-workflow-dispatch)
- [GitHub Docs: Events that trigger workflows](https://docs.github.com/en/actions/reference/events-that-trigger-workflows)

---

### 4. Minimum Configuration for `claude-code-action`

#### Required Elements

| Element | Requirement | Notes |
|---------|-------------|-------|
| **Secret** | `ANTHROPIC_API_KEY` | Must be configured in repository secrets |
| **Permissions** | `contents: write`, `pull-requests: write`, `issues: write` | For full functionality |
| **GitHub App** | Install [Claude GitHub App](https://github.com/apps/claude) | Or use custom app with PAT |
| **Checkout** | `actions/checkout@v4` before claude-code-action | Required for codebase access |

#### Minimal Working Workflow

```yaml
name: Minimal Claude Code Action
on:
  workflow_dispatch:
    inputs:
      task:
        description: 'Task for Claude'
        required: true

permissions:
  contents: write
  pull-requests: write
  issues: write

jobs:
  claude:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: ${{ inputs.task }}
```

#### Authentication Options

1. **Direct API Key (Simplest)**
   ```yaml
   anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
   ```

2. **OAuth Token (Pro/Max users)**
   ```yaml
   claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
   ```

3. **Custom GitHub App**
   ```yaml
   - uses: actions/create-github-app-token@v1
     id: app-token
     with:
       app-id: ${{ secrets.APP_ID }}
       private-key: ${{ secrets.APP_PRIVATE_KEY }}

   - uses: anthropics/claude-code-action@v1
     with:
       anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
       github_token: ${{ steps.app-token.outputs.token }}
   ```

#### Issue with Current Workflow

The current `ai-self-heal.yml` has a potential issue with `claude_args`:

```yaml
# Current (may not work correctly)
claude_args: |
  {
    "thinking": "enabled",
    "max_tokens": 16000
  }

# Should be CLI flags format:
claude_args: |
  --max-turns 20
```

The `claude_args` input expects CLI arguments, not JSON. The `thinking` parameter is not a valid CLI flag.

**Sources:**
- [claude-code-action Setup Guide](https://github.com/anthropics/claude-code-action/blob/main/docs/setup.md)
- [claude-code-action Usage Guide](https://github.com/anthropics/claude-code-action/blob/main/docs/usage.md)
- [Claude Code Docs: GitHub Actions](https://code.claude.com/docs/en/github-actions)

---

## Recommendation

### Approach: Phased Validation

**Phase 1: Secret Verification (No cost)**
```bash
# Check if workflow file exists on main branch
gh api repos/ray-manaloto/guilde-lite-tdd-sprint/contents/.github/workflows/ai-self-heal.yml

# List secrets (requires admin access)
gh api repos/ray-manaloto/guilde-lite-tdd-sprint/actions/secrets
```

**Phase 2: Dry-Run Validation (Minimal cost)**
1. Add a validation job that runs before the main job
2. Test with `workflow_dispatch` using mock data
3. Monitor the GitHub Actions log for any permission errors

**Phase 3: Full Integration Test**
1. Create a test issue with `ai-fix` label
2. Verify Claude responds and creates a branch
3. Validate PR creation

### Corrected Workflow

The workflow should be updated to fix the `claude_args` format:

```yaml
- name: AI Diagnosis and Fix
  uses: anthropics/claude-code-action@v1
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    prompt: |
      ## Self-Healing Task
      [... existing prompt ...]
    claude_args: |
      --max-turns 20
```

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| API key not configured | High | Add validation step that fails fast |
| Incorrect `claude_args` format | Medium | Update to CLI flag format |
| `repository_dispatch` needs PAT | Medium | Document PAT creation for webhooks |
| Rate limiting on Anthropic API | Low | Add retry logic, monitor usage |
| PR conflicts from concurrent fixes | Low | Use unique branch naming with timestamps |

---

## Next Steps

1. **Push workflow to remote** - The `ai-self-heal.yml` exists locally but needs to be pushed to `main` branch
   ```bash
   git add .github/workflows/ai-self-heal.yml
   git commit -m "feat: Add AI self-healing workflow"
   git push origin main
   ```
2. **Configure ANTHROPIC_API_KEY secret** - Go to https://github.com/ray-manaloto/guilde-lite-tdd-sprint/settings/secrets/actions
3. **Install Claude GitHub App** - Visit https://github.com/apps/claude and install on repository
4. **Fix `claude_args` format** - Update workflow to use CLI flags instead of JSON
5. **Test with `workflow_dispatch`** - Run manual test with mock error data
6. **Create PAT for webhooks** - If using Sentry/Logfire integration, create fine-grained PAT with `Contents: write`

---

## Validation Scripts

### Script 1: Check Repository Setup

```bash
#!/bin/bash
# validate-github-setup.sh

REPO="ray-manaloto/guilde-lite-tdd-sprint"

echo "=== GitHub Self-Heal Integration Validator ==="

# Check if gh CLI is authenticated
if ! gh auth status &>/dev/null; then
  echo "ERROR: GitHub CLI not authenticated. Run 'gh auth login'"
  exit 1
fi

# Check workflow file exists
echo -n "Checking workflow file... "
if gh api "repos/$REPO/contents/.github/workflows/ai-self-heal.yml" &>/dev/null; then
  echo "OK"
else
  echo "MISSING - Workflow not found on main branch"
fi

# Check secrets (will fail if not admin)
echo -n "Checking secrets configuration... "
SECRETS=$(gh api "repos/$REPO/actions/secrets" 2>/dev/null)
if [ $? -eq 0 ]; then
  if echo "$SECRETS" | jq -e '.secrets[] | select(.name == "ANTHROPIC_API_KEY")' &>/dev/null; then
    echo "OK - ANTHROPIC_API_KEY found"
  else
    echo "MISSING - ANTHROPIC_API_KEY not configured"
  fi
else
  echo "SKIP - Requires admin access"
fi

# Check Claude app installation
echo -n "Checking Claude app... "
INSTALLATIONS=$(gh api "repos/$REPO/installation" 2>/dev/null)
if [ $? -eq 0 ]; then
  echo "OK"
else
  echo "CHECK MANUALLY - Visit https://github.com/apps/claude"
fi

echo ""
echo "=== Manual Steps Required ==="
echo "1. Ensure ANTHROPIC_API_KEY is set in repository secrets"
echo "2. Install Claude GitHub App: https://github.com/apps/claude"
echo "3. For repository_dispatch, create PAT with Contents:write scope"
```

### Script 2: Test Workflow Trigger

```bash
#!/bin/bash
# test-self-heal-workflow.sh

REPO="ray-manaloto/guilde-lite-tdd-sprint"

echo "Triggering ai-self-heal.yml with test data..."

gh workflow run ai-self-heal.yml \
  -R "$REPO" \
  -f error_message="[TEST] Validation error in test_module.py: AttributeError - 'NoneType' object has no attribute 'process'" \
  -f error_file="backend/app/services/test_module.py" \
  -f error_line="42"

echo ""
echo "Workflow triggered. Check status at:"
echo "https://github.com/$REPO/actions/workflows/ai-self-heal.yml"
```

---

## References

- [GitHub Docs: repository_dispatch](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
- [GitHub Docs: workflow_dispatch](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch)
- [claude-code-action Repository](https://github.com/anthropics/claude-code-action)
- [claude-code-action Setup Guide](https://github.com/anthropics/claude-code-action/blob/main/docs/setup.md)
- [claude-code-action Security Guide](https://github.com/anthropics/claude-code-action/blob/main/docs/security.md)
- [GitHub Community: Fine-grained PAT for dispatch](https://github.com/orgs/community/discussions/58868)
- [GitHub Community: Testing secrets in actions](https://github.com/orgs/community/discussions/26726)
