#!/bin/bash
# test-self-heal-workflow.sh
# Triggers the AI self-heal workflow with test data
#
# Usage: ./test-self-heal-workflow.sh [REPO] [MODE]
# Modes:
#   dispatch  - Use workflow_dispatch (default)
#   issue     - Create a test issue with ai-fix label
#   api       - Use repository_dispatch API (requires PAT)
#
# Examples:
#   ./test-self-heal-workflow.sh
#   ./test-self-heal-workflow.sh ray-manaloto/guilde-lite-tdd-sprint dispatch
#   ./test-self-heal-workflow.sh ray-manaloto/guilde-lite-tdd-sprint issue

set -e

REPO="${1:-ray-manaloto/guilde-lite-tdd-sprint}"
MODE="${2:-dispatch}"
TIMESTAMP=$(date +%s)

echo "=============================================="
echo "AI Self-Heal Workflow Test"
echo "Repository: $REPO"
echo "Mode: $MODE"
echo "=============================================="
echo ""

# Check if gh CLI is authenticated
if ! gh auth status &>/dev/null; then
  echo "ERROR: GitHub CLI not authenticated. Run 'gh auth login'"
  exit 1
fi

case "$MODE" in
  dispatch)
    echo "Triggering workflow via workflow_dispatch..."
    echo ""

    ERROR_MSG="[TEST-$TIMESTAMP] ValidationError in test_module.py: AttributeError - 'NoneType' object has no attribute 'process'. This is a test error for workflow validation."

    gh workflow run ai-self-heal.yml \
      -R "$REPO" \
      -f error_message="$ERROR_MSG" \
      -f error_file="backend/app/services/test_module.py" \
      -f error_line="42"

    echo "Workflow triggered successfully!"
    echo ""
    echo "Monitor progress at:"
    echo "  https://github.com/$REPO/actions/workflows/ai-self-heal.yml"
    echo ""
    echo "Check latest run:"
    echo "  gh run list -R $REPO -w ai-self-heal.yml --limit 1"
    ;;

  issue)
    echo "Creating test issue with ai-fix label..."
    echo ""

    ISSUE_URL=$(gh issue create \
      -R "$REPO" \
      --title "[Test-$TIMESTAMP] AI Self-Heal Validation" \
      --body "## Test Issue for AI Self-Healing

This is a **test issue** to validate the AI self-healing workflow integration.

### Mock Error Context

- **File:** \`backend/app/services/mock_service.py\`
- **Line:** 42
- **Error Type:** AttributeError
- **Message:** 'NoneType' object has no attribute 'calculate'

### Expected Behavior

Claude should:
1. Acknowledge this is a test issue
2. Analyze the mock error context
3. Provide a diagnostic summary
4. NOT create actual code changes (this is just a validation test)

### Note

This issue was created automatically by \`test-self-heal-workflow.sh\` at $(date).
The \`ai-fix\` label will be added to trigger the workflow.

---
**Test ID:** $TIMESTAMP" \
      --label "ai-fix")

    echo "Test issue created: $ISSUE_URL"
    echo ""
    echo "The workflow should trigger automatically due to the 'ai-fix' label."
    echo ""
    echo "Monitor progress at:"
    echo "  https://github.com/$REPO/actions/workflows/ai-self-heal.yml"
    ;;

  api)
    echo "Triggering workflow via repository_dispatch API..."
    echo ""
    echo "NOTE: This requires a PAT with 'Contents: write' scope."
    echo ""

    if [ -z "$GITHUB_PAT" ]; then
      echo "ERROR: GITHUB_PAT environment variable not set."
      echo ""
      echo "Set it with:"
      echo "  export GITHUB_PAT='ghp_your_token_here'"
      echo ""
      echo "Or run:"
      echo "  GITHUB_PAT=\$(gh auth token) ./test-self-heal-workflow.sh $REPO api"
      exit 1
    fi

    OWNER=$(echo "$REPO" | cut -d'/' -f1)
    REPO_NAME=$(echo "$REPO" | cut -d'/' -f2)

    curl -X POST \
      -H "Accept: application/vnd.github+json" \
      -H "Authorization: Bearer $GITHUB_PAT" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "https://api.github.com/repos/$OWNER/$REPO_NAME/dispatches" \
      -d "{
        \"event_type\": \"error-detected\",
        \"client_payload\": {
          \"error_message\": \"[TEST-$TIMESTAMP] Mock production error for validation\",
          \"file\": \"backend/app/services/production_service.py\",
          \"line\": \"100\",
          \"trace_id\": \"test-trace-$TIMESTAMP\"
        }
      }"

    echo "Repository dispatch event sent!"
    echo ""
    echo "Monitor progress at:"
    echo "  https://github.com/$REPO/actions/workflows/ai-self-heal.yml"
    ;;

  *)
    echo "Unknown mode: $MODE"
    echo ""
    echo "Available modes:"
    echo "  dispatch - Trigger via workflow_dispatch (default)"
    echo "  issue    - Create test issue with ai-fix label"
    echo "  api      - Trigger via repository_dispatch API"
    exit 1
    ;;
esac

echo ""
echo "=============================================="
echo "Verification Commands"
echo "=============================================="
echo ""
echo "# Check workflow run status:"
echo "gh run list -R $REPO -w ai-self-heal.yml --limit 3"
echo ""
echo "# Watch latest run:"
echo "gh run watch -R $REPO \$(gh run list -R $REPO -w ai-self-heal.yml --limit 1 --json databaseId -q '.[0].databaseId')"
echo ""
echo "# View run logs:"
echo "gh run view -R $REPO --log \$(gh run list -R $REPO -w ai-self-heal.yml --limit 1 --json databaseId -q '.[0].databaseId')"
