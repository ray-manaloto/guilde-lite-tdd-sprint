#!/bin/bash
# validate-github-setup.sh
# Validates GitHub integration setup for the AI self-healing system
#
# Usage: ./validate-github-setup.sh [REPO]
# Example: ./validate-github-setup.sh ray-manaloto/guilde-lite-tdd-sprint

set -e

REPO="${1:-ray-manaloto/guilde-lite-tdd-sprint}"

echo "=============================================="
echo "GitHub Self-Heal Integration Validator"
echo "Repository: $REPO"
echo "=============================================="
echo ""

# Check if gh CLI is installed
if ! command -v gh &>/dev/null; then
  echo "ERROR: GitHub CLI (gh) is not installed."
  echo "Install it from: https://cli.github.com/"
  exit 1
fi

# Check if gh CLI is authenticated
echo -n "[1/5] Checking GitHub CLI authentication... "
if gh auth status &>/dev/null; then
  echo "OK"
else
  echo "FAILED"
  echo "  -> Run 'gh auth login' to authenticate"
  exit 1
fi

# Check workflow file exists
echo -n "[2/5] Checking workflow file exists on main... "
WORKFLOW_CHECK=$(gh api "repos/$REPO/contents/.github/workflows/ai-self-heal.yml" 2>&1)
if [ $? -eq 0 ]; then
  echo "OK"
else
  echo "MISSING"
  echo "  -> Workflow file not found on main branch"
  echo "  -> Ensure .github/workflows/ai-self-heal.yml is pushed to main"
fi

# Check secrets configuration
echo -n "[3/5] Checking ANTHROPIC_API_KEY secret... "
SECRETS=$(gh api "repos/$REPO/actions/secrets" 2>/dev/null)
if [ $? -eq 0 ]; then
  if echo "$SECRETS" | grep -q "ANTHROPIC_API_KEY"; then
    UPDATED=$(echo "$SECRETS" | jq -r '.secrets[] | select(.name == "ANTHROPIC_API_KEY") | .updated_at')
    echo "OK (last updated: $UPDATED)"
  else
    echo "MISSING"
    echo "  -> Go to: https://github.com/$REPO/settings/secrets/actions"
    echo "  -> Add secret: ANTHROPIC_API_KEY"
  fi
else
  echo "SKIP (requires admin access)"
  echo "  -> Manually check: https://github.com/$REPO/settings/secrets/actions"
fi

# Check repository permissions
echo -n "[4/5] Checking repository access... "
REPO_INFO=$(gh api "repos/$REPO" 2>/dev/null)
if [ $? -eq 0 ]; then
  PERMISSIONS=$(echo "$REPO_INFO" | jq -r '.permissions // {}')
  CAN_PUSH=$(echo "$PERMISSIONS" | jq -r '.push // false')
  CAN_ADMIN=$(echo "$PERMISSIONS" | jq -r '.admin // false')

  if [ "$CAN_ADMIN" = "true" ]; then
    echo "OK (admin access)"
  elif [ "$CAN_PUSH" = "true" ]; then
    echo "OK (write access)"
  else
    echo "LIMITED (read-only)"
    echo "  -> You may need write access to trigger workflows"
  fi
else
  echo "FAILED"
  echo "  -> Cannot access repository"
fi

# Check if workflow can be triggered
echo -n "[5/5] Checking workflow trigger availability... "
WORKFLOWS=$(gh api "repos/$REPO/actions/workflows" 2>/dev/null)
if [ $? -eq 0 ]; then
  SELF_HEAL=$(echo "$WORKFLOWS" | jq -r '.workflows[] | select(.name == "AI Self-Heal") | .id')
  if [ -n "$SELF_HEAL" ]; then
    echo "OK (workflow ID: $SELF_HEAL)"
  else
    echo "NOT FOUND"
    echo "  -> Workflow not registered in GitHub Actions"
    echo "  -> Push the workflow file to main branch first"
  fi
else
  echo "SKIP"
fi

echo ""
echo "=============================================="
echo "Summary"
echo "=============================================="
echo ""
echo "To complete setup, ensure:"
echo "  1. Workflow file is on main branch"
echo "  2. ANTHROPIC_API_KEY secret is configured"
echo "  3. Claude GitHub App is installed: https://github.com/apps/claude"
echo ""
echo "Test the workflow:"
echo "  gh workflow run ai-self-heal.yml -R $REPO \\"
echo "    -f error_message='Test error message' \\"
echo "    -f error_file='backend/app/test.py' \\"
echo "    -f error_line='1'"
echo ""
echo "Monitor at: https://github.com/$REPO/actions/workflows/ai-self-heal.yml"
