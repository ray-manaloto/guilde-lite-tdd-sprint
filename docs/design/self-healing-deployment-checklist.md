# Self-Healing Infrastructure Deployment Checklist

## Pre-Deployment Requirements

### Repository Setup

- [ ] **GitHub Actions workflow committed**
  - File: `.github/workflows/ai-self-heal.yml`
  - Status: Currently tracked, needs to be pushed
  - Verify with: `git status .github/workflows/`

- [ ] **Required secrets configured in GitHub**
  ```
  Settings > Secrets and variables > Actions > New repository secret
  ```
  - [ ] `ANTHROPIC_API_KEY` - Required for Claude Code Action
  - [ ] `GITHUB_TOKEN` - Auto-provided by Actions (verify permissions)

- [ ] **Workflow permissions enabled**
  ```
  Settings > Actions > General > Workflow permissions
  ```
  - [ ] "Read and write permissions" enabled
  - [ ] "Allow GitHub Actions to create and approve pull requests" checked

### Environment Configuration

- [ ] **Backend `.env` file configured**
  ```bash
  # Verify these are set:
  grep -E "^(GITHUB_TOKEN|GITHUB_REPO|SELF_HEAL)" .env
  ```
  Required variables:
  - [ ] `GITHUB_TOKEN` - Personal access token with `repo` scope
  - [ ] `GITHUB_REPO` - Format: `owner/repo`
  - [ ] `SELF_HEAL_ENABLED=true`
  - [ ] `SELF_HEAL_AUTO_FIX_CONFIDENCE_THRESHOLD=0.6`

- [ ] **Observability configured**
  - [ ] `SENTRY_DSN` - For error tracking (optional but recommended)
  - [ ] `LOGFIRE_TOKEN` - For tracing and spans (optional but recommended)

### Branch Protection (Optional but Recommended)

- [ ] **Main branch protection rules**
  ```
  Settings > Branches > Add branch protection rule
  ```
  For `main` branch:
  - [ ] "Require a pull request before merging" enabled
  - [ ] "Require approvals" set to 1 (for human review of AI fixes)
  - [ ] "Require status checks to pass before merging" enabled
  - [ ] Add required checks: `lint`, `test`
  - [ ] "Do not allow bypassing the above settings" enabled for AI-generated PRs

## Webhook Configuration

### Option A: Sentry Integration

1. [ ] **Create Sentry integration**
   ```
   Sentry > Settings > Integrations > GitHub
   ```
   - Connect your GitHub organization
   - Enable issue linking

2. [ ] **Configure Sentry webhook**
   ```
   Sentry > Settings > Integrations > Webhooks
   ```
   - URL: `https://api.github.com/repos/{owner}/{repo}/dispatches`
   - Events: `error.created`
   - Headers:
     ```
     Authorization: Bearer <GITHUB_TOKEN>
     Accept: application/vnd.github+json
     ```

3. [ ] **Test Sentry webhook**
   ```bash
   # Trigger a test error
   curl -X POST "https://api.github.com/repos/{owner}/{repo}/dispatches" \
     -H "Authorization: Bearer ${GITHUB_TOKEN}" \
     -H "Accept: application/vnd.github+json" \
     -d '{"event_type":"error-detected","client_payload":{"error_message":"Test error","file":"test.py","line":"1"}}'
   ```

### Option B: Logfire Integration

1. [ ] **Configure Logfire alerts**
   ```
   Logfire > Project > Alerts > New Alert
   ```
   - Condition: `span.status = 'error'`
   - Action: Webhook

2. [ ] **Set webhook destination**
   - URL: `https://api.github.com/repos/{owner}/{repo}/dispatches`
   - Method: POST
   - Headers: Authorization Bearer token

### Option C: Custom Webhook (via Backend)

1. [ ] **Enable webhook endpoint in backend**
   - Endpoint will be at: `/api/v1/webhooks/self-heal`
   - Configure to forward to GitHub repository_dispatch

## Local Development Setup

### Script Installation

1. [ ] **Verify restart script is executable**
   ```bash
   chmod +x scripts/self-heal-restart.sh
   ls -la scripts/self-heal-restart.sh
   ```

2. [ ] **Initialize state directory**
   ```bash
   mkdir -p .run/self-heal
   ```

3. [ ] **Test restart detection**
   ```bash
   ./scripts/self-heal-restart.sh --check-only --verbose
   ```

### DevCtl Integration

1. [ ] **Verify devctl is working**
   ```bash
   ./scripts/devctl.sh status
   ```

2. [ ] **Test service restart**
   ```bash
   ./scripts/devctl.sh restart backend
   ./scripts/devctl.sh preflight
   ```

## Verification Tests

### Workflow Test

1. [ ] **Manual workflow trigger**
   ```
   GitHub > Actions > AI Self-Heal > Run workflow
   ```
   - Input: Test error message
   - Verify: Workflow runs and completes

2. [ ] **Repository dispatch test**
   ```bash
   curl -X POST "https://api.github.com/repos/${GITHUB_REPO}/dispatches" \
     -H "Authorization: Bearer ${GITHUB_TOKEN}" \
     -H "Accept: application/vnd.github+json" \
     -d '{
       "event_type": "error-detected",
       "client_payload": {
         "error_message": "Test: Division by zero in calculator.py",
         "file": "backend/app/services/calculator.py",
         "line": "42"
       }
     }'
   ```

3. [ ] **Issue label trigger**
   - Create a test issue
   - Add `ai-fix` label
   - Verify workflow triggers

### Health Check Verification

1. [ ] **Liveness probe**
   ```bash
   curl http://localhost:8000/api/v1/health
   # Expected: {"status": "healthy"}
   ```

2. [ ] **Readiness probe**
   ```bash
   curl http://localhost:8000/api/v1/health/ready
   # Expected: {"status": "ready", "checks": {...}}
   ```

3. [ ] **Preflight check**
   ```bash
   ./scripts/devctl.sh preflight --verbose
   ```

### Restart Script Verification

1. [ ] **Dry run test**
   ```bash
   ./scripts/self-heal-restart.sh --dry-run --verbose
   ```

2. [ ] **Force restart test**
   ```bash
   ./scripts/self-heal-restart.sh --force --service backend --verbose
   ```

3. [ ] **Env change detection**
   ```bash
   # Modify .env slightly
   echo "# test" >> .env
   ./scripts/self-heal-restart.sh --check-only --verbose
   # Should report: "Restart needed: env_changed"
   ```

## Post-Deployment Monitoring

### Metrics to Track

- [ ] **Self-heal workflow runs**
  - Success rate
  - Average execution time
  - Error categories handled

- [ ] **PR metrics**
  - PRs created by AI
  - PRs merged vs rejected
  - Time to merge

- [ ] **Service availability**
  - Health check success rate
  - Restart frequency
  - Mean time to recovery (MTTR)

### Alerts to Configure

1. [ ] **Workflow failure alert**
   ```yaml
   # In monitoring.yml or separate alerting system
   - name: self-heal-failure
     condition: workflow_run.conclusion == 'failure'
     action: notify_slack
   ```

2. [ ] **Excessive restart alert**
   - Threshold: >5 restarts in 1 hour
   - Action: Page on-call

3. [ ] **Health check degradation**
   - Threshold: p99 latency > 2s
   - Action: Alert to monitoring channel

## Rollback Procedures

### If Self-Healing Creates Bad Fix

1. Close/reject the PR immediately
2. Revert any merged commits:
   ```bash
   git revert <commit-sha>
   git push
   ```
3. Disable self-healing temporarily:
   ```bash
   # In .env
   SELF_HEAL_ENABLED=false
   ```
4. Investigate root cause

### If Webhook Spam Occurs

1. Disable webhook in source (Sentry/Logfire)
2. Check rate limiting:
   - GitHub API: 5000 requests/hour
   - workflow_dispatch: limited by Actions quota
3. Add filtering rules to classify and drop duplicates

## Security Considerations

- [ ] **Token rotation schedule**
  - `GITHUB_TOKEN`: Rotate every 90 days
  - `ANTHROPIC_API_KEY`: Rotate as per policy

- [ ] **Audit logging**
  - All workflow runs logged in GitHub
  - PR creation tracked
  - Code changes auditable via git history

- [ ] **Scope limitation**
  - Claude Code Action limited to: `Edit, Read, Write, Bash, Glob, Grep`
  - No web access (`WebFetch`, `WebSearch` disabled)
  - Sandboxed execution in GitHub Actions runner

## Success Criteria

The self-healing infrastructure is considered operational when:

1. [ ] Health checks respond within 500ms
2. [ ] Workflow triggers successfully on error-detected event
3. [ ] PRs are created with proper format and labels
4. [ ] At least one fix has been merged via the automated process
5. [ ] Restart script correctly detects env/migration changes
6. [ ] No false positives for 24 hours
