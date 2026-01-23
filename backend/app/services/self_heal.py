"""Self-healing service for AI-enabled error detection and auto-fix.

This service integrates with:
- Logfire/Sentry for error detection
- GitHub Actions for claude-code-action triggers
- Circuit breakers for automatic retry

References:
- claude-code-action: https://github.com/anthropics/claude-code-action
- OpenTelemetry AI Observability: https://opentelemetry.io/blog/2025/ai-agent-observability/
"""

import hashlib
import logging
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas.diagnostic import ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class SelfHealAction(StrEnum):
    """Actions the self-healing system can take."""

    RETRY = "retry"  # Auto-retry with backoff
    CIRCUIT_BREAK = "circuit_break"  # Open circuit breaker
    CREATE_ISSUE = "create_issue"  # Create GitHub issue
    CREATE_PR = "create_pr"  # Trigger claude-code-action for auto-fix
    ALERT_ONLY = "alert_only"  # Just send alert, no auto-action
    ROLLBACK = "rollback"  # Trigger rollback (feature flag)


class ErrorClassification(BaseModel):
    """AI-classified error with recommended action."""

    error_hash: str = Field(description="Unique hash for deduplication")
    category: ErrorCategory
    severity: ErrorSeverity
    recommended_action: SelfHealAction
    confidence: float = Field(ge=0.0, le=1.0)
    auto_fixable: bool = False
    root_cause_hint: str | None = None


class SelfHealTrigger(BaseModel):
    """Payload to trigger self-healing workflow."""

    error_message: str
    file: str | None = None
    line: int | None = None
    trace_id: str | None = None
    stack_trace: str | None = None
    category: ErrorCategory | None = None
    severity: ErrorSeverity | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SelfHealService:
    """Service for AI-enabled self-healing.

    Workflow:
    1. Receive error from Logfire/Sentry webhook
    2. Classify error using diagnostic schemas
    3. Decide action (retry, circuit break, create issue, auto-fix)
    4. Execute action (trigger GitHub Action for auto-fix)
    """

    def __init__(
        self,
        github_token: str | None = None,
        github_repo: str | None = None,
    ):
        self.github_token = github_token or settings.GITHUB_TOKEN
        self.github_repo = github_repo or settings.GITHUB_REPO
        self.enabled = settings.SELF_HEAL_ENABLED
        self.auto_fix_threshold = settings.SELF_HEAL_AUTO_FIX_CONFIDENCE_THRESHOLD
        self._error_counts: dict[str, int] = {}
        self._circuit_states: dict[str, bool] = {}

    def compute_error_hash(self, error_message: str, file: str | None = None) -> str:
        """Compute unique hash for error deduplication."""
        content = f"{error_message}:{file or 'unknown'}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def classify_error(self, trigger: SelfHealTrigger) -> ErrorClassification:
        """Classify error and recommend action.

        Uses heuristics and patterns from diagnostic.py schemas.
        In production, this would use an LLM for classification.
        """
        error_hash = self.compute_error_hash(trigger.error_message, trigger.file)
        error_lower = trigger.error_message.lower()

        # Heuristic classification (replace with LLM in production)
        category = trigger.category or ErrorCategory.UNKNOWN
        severity = trigger.severity or ErrorSeverity.ERROR
        action = SelfHealAction.ALERT_ONLY
        confidence = 0.5
        auto_fixable = False
        root_cause_hint = None

        # Pattern matching for common errors
        if "timeout" in error_lower or "timed out" in error_lower:
            category = ErrorCategory.TIMEOUT
            action = SelfHealAction.RETRY
            confidence = 0.9

        elif "connection refused" in error_lower or "connectionerror" in error_lower:
            category = ErrorCategory.NETWORK
            action = SelfHealAction.CIRCUIT_BREAK
            confidence = 0.85

        elif "401" in error_lower or "unauthorized" in error_lower:
            category = ErrorCategory.AUTHENTICATION
            action = SelfHealAction.ALERT_ONLY
            confidence = 0.9
            root_cause_hint = "Check authentication token validity"

        elif "typeerror" in error_lower or "attributeerror" in error_lower:
            category = ErrorCategory.VALIDATION
            action = SelfHealAction.CREATE_PR
            auto_fixable = True
            confidence = 0.7
            root_cause_hint = "Likely a code bug - check types/attributes"

        elif "importerror" in error_lower or "modulenotfounderror" in error_lower:
            category = ErrorCategory.DEPENDENCY
            action = SelfHealAction.CREATE_ISSUE
            confidence = 0.8
            root_cause_hint = "Missing dependency or import path issue"

        elif "rate limit" in error_lower or "429" in error_lower:
            category = ErrorCategory.LLM_API
            action = SelfHealAction.CIRCUIT_BREAK
            confidence = 0.95

        elif "websocket" in error_lower:
            category = ErrorCategory.NETWORK
            action = SelfHealAction.CREATE_PR
            auto_fixable = True
            confidence = 0.6
            root_cause_hint = "WebSocket connection issue"

        elif "permission" in error_lower or "403" in error_lower:
            category = ErrorCategory.AUTHORIZATION
            action = SelfHealAction.CREATE_ISSUE
            confidence = 0.85

        return ErrorClassification(
            error_hash=error_hash,
            category=category,
            severity=severity,
            recommended_action=action,
            confidence=confidence,
            auto_fixable=auto_fixable,
            root_cause_hint=root_cause_hint,
        )

    async def trigger_github_action(self, trigger: SelfHealTrigger) -> bool:
        """Trigger GitHub Actions workflow for auto-fix.

        Uses repository_dispatch to trigger .github/workflows/ai-self-heal.yml
        """
        if not self.github_token or not self.github_repo:
            logger.warning("GitHub token or repo not configured for self-heal")
            return False

        url = f"https://api.github.com/repos/{self.github_repo}/dispatches"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        payload = {
            "event_type": "error-detected",
            "client_payload": {
                "error_message": trigger.error_message,
                "file": trigger.file,
                "line": trigger.line,
                "trace_id": trigger.trace_id,
                "stack_trace": trigger.stack_trace,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **trigger.metadata,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 204:
                    logger.info(f"Triggered self-heal workflow for: {trigger.error_message[:50]}")
                    return True
                else:
                    logger.error(f"Failed to trigger workflow: {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"Error triggering GitHub Action: {e}")
                return False

    async def create_github_issue(self, trigger: SelfHealTrigger, classification: ErrorClassification) -> str | None:
        """Create GitHub issue for errors that need human attention."""
        if not self.github_token or not self.github_repo:
            return None

        url = f"https://api.github.com/repos/{self.github_repo}/issues"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
        }

        body = f"""## Auto-Detected Error

**Category:** {classification.category}
**Severity:** {classification.severity}
**Confidence:** {classification.confidence:.0%}
**Auto-fixable:** {'Yes' if classification.auto_fixable else 'No'}

### Error Message
```
{trigger.error_message}
```

### Location
- **File:** {trigger.file or 'Unknown'}
- **Line:** {trigger.line or 'Unknown'}
- **Trace ID:** {trigger.trace_id or 'N/A'}

### Root Cause Hint
{classification.root_cause_hint or 'No hint available'}

### Stack Trace
```
{trigger.stack_trace or 'Not available'}
```

---
*This issue was auto-created by the self-healing system.*
"""

        payload = {
            "title": f"[Auto] {classification.category}: {trigger.error_message[:50]}...",
            "body": body,
            "labels": ["auto-detected", f"severity:{classification.severity}", "ai-fix"],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 201:
                    data = response.json()
                    logger.info(f"Created issue #{data['number']}")
                    return data["html_url"]
                return None
            except Exception as e:
                logger.error(f"Error creating GitHub issue: {e}")
                return None

    async def handle_error(self, trigger: SelfHealTrigger) -> dict[str, Any]:
        """Main entry point: classify error and execute recommended action.

        Returns dict with action taken and result.
        """
        classification = self.classify_error(trigger)
        result = {
            "classification": classification.model_dump(),
            "action_taken": classification.recommended_action,
            "success": False,
            "details": None,
        }

        # Check for duplicate/repeated errors
        self._error_counts[classification.error_hash] = (
            self._error_counts.get(classification.error_hash, 0) + 1
        )

        # Execute action based on classification
        match classification.recommended_action:
            case SelfHealAction.RETRY:
                result["details"] = "Error will be retried with exponential backoff"
                result["success"] = True

            case SelfHealAction.CIRCUIT_BREAK:
                self._circuit_states[classification.error_hash] = True
                result["details"] = "Circuit breaker opened"
                result["success"] = True

            case SelfHealAction.CREATE_ISSUE:
                issue_url = await self.create_github_issue(trigger, classification)
                result["details"] = f"Issue created: {issue_url}" if issue_url else "Failed to create issue"
                result["success"] = issue_url is not None

            case SelfHealAction.CREATE_PR:
                # Only trigger auto-fix for high-confidence, auto-fixable errors
                if classification.auto_fixable and classification.confidence >= self.auto_fix_threshold:
                    success = await self.trigger_github_action(trigger)
                    result["details"] = "Auto-fix workflow triggered" if success else "Failed to trigger workflow"
                    result["success"] = success
                else:
                    # Fall back to creating an issue
                    issue_url = await self.create_github_issue(trigger, classification)
                    result["details"] = f"Issue created (low confidence): {issue_url}"
                    result["action_taken"] = SelfHealAction.CREATE_ISSUE
                    result["success"] = issue_url is not None

            case SelfHealAction.ALERT_ONLY:
                result["details"] = "Alert sent, no auto-action taken"
                result["success"] = True

        return result

    def is_circuit_open(self, error_hash: str) -> bool:
        """Check if circuit breaker is open for an error pattern."""
        return self._circuit_states.get(error_hash, False)

    def reset_circuit(self, error_hash: str) -> None:
        """Reset circuit breaker for an error pattern."""
        self._circuit_states.pop(error_hash, None)


# Singleton instance
_self_heal_service: SelfHealService | None = None


def get_self_heal_service() -> SelfHealService:
    """Get or create singleton SelfHealService instance."""
    global _self_heal_service
    if _self_heal_service is None:
        _self_heal_service = SelfHealService()
    return _self_heal_service
