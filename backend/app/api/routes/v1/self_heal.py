"""Self-healing webhook routes.

Receives error events from:
- Sentry webhooks
- Logfire alerts
- Frontend error boundaries
- Manual triggers

Triggers AI-enabled auto-fix via claude-code-action.
"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.services.self_heal import (
    SelfHealService,
    SelfHealTrigger,
    get_self_heal_service,
)

router = APIRouter()


@router.post("/webhook/sentry", status_code=status.HTTP_202_ACCEPTED)
async def sentry_webhook(
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
):
    """Receive Sentry webhook events and trigger self-healing.

    Configure in Sentry: Settings > Integrations > Webhooks
    Event types: issue, error, event_alert
    """
    event_type = payload.get("action") or payload.get("event", {}).get("type")

    if event_type not in ("created", "resolved", "error", "event_alert"):
        return {"status": "ignored", "reason": f"Event type '{event_type}' not handled"}

    # Extract error details from Sentry payload
    event = payload.get("event", payload.get("data", {}).get("event", {}))
    exception = event.get("exception", {})
    values = exception.get("values", [{}])
    error_info = values[0] if values else {}

    trigger = SelfHealTrigger(
        error_message=error_info.get("value", event.get("title", "Unknown error")),
        file=error_info.get("stacktrace", {}).get("frames", [{}])[-1].get("filename"),
        line=error_info.get("stacktrace", {}).get("frames", [{}])[-1].get("lineno"),
        trace_id=event.get("event_id"),
        stack_trace=str(error_info.get("stacktrace", {}).get("frames", [])),
        metadata={
            "source": "sentry",
            "project": payload.get("project", {}).get("slug"),
            "url": event.get("url"),
        },
    )

    # Process in background
    service = get_self_heal_service()
    background_tasks.add_task(service.handle_error, trigger)

    return {"status": "accepted", "trigger_id": trigger.trace_id}


@router.post("/webhook/logfire", status_code=status.HTTP_202_ACCEPTED)
async def logfire_webhook(
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
):
    """Receive Logfire alert webhooks and trigger self-healing.

    Configure in Logfire: Alerts > Webhooks
    """
    alert_type = payload.get("alert_type")

    if alert_type not in ("error", "exception", "anomaly"):
        return {"status": "ignored", "reason": f"Alert type '{alert_type}' not handled"}

    span = payload.get("span", {})
    attributes = span.get("attributes", {})

    trigger = SelfHealTrigger(
        error_message=payload.get("message", attributes.get("exception.message", "Unknown")),
        file=attributes.get("code.filepath"),
        line=attributes.get("code.lineno"),
        trace_id=span.get("trace_id"),
        stack_trace=attributes.get("exception.stacktrace"),
        metadata={
            "source": "logfire",
            "service": attributes.get("service.name"),
            "span_id": span.get("span_id"),
        },
    )

    service = get_self_heal_service()
    background_tasks.add_task(service.handle_error, trigger)

    return {"status": "accepted", "trace_id": trigger.trace_id}


@router.post("/webhook/frontend", status_code=status.HTTP_202_ACCEPTED)
async def frontend_error_webhook(
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
):
    """Receive errors from frontend error boundaries.

    Call from Next.js error.tsx components.
    """
    trigger = SelfHealTrigger(
        error_message=payload.get("message", "Frontend error"),
        file=payload.get("componentStack", "").split("\n")[0] if payload.get("componentStack") else None,
        trace_id=payload.get("digest"),
        stack_trace=payload.get("stack"),
        metadata={
            "source": "frontend",
            "url": payload.get("url"),
            "userAgent": payload.get("userAgent"),
        },
    )

    service = get_self_heal_service()
    background_tasks.add_task(service.handle_error, trigger)

    return {"status": "accepted", "digest": trigger.trace_id}


@router.post("/trigger", status_code=status.HTTP_200_OK)
async def manual_trigger(
    trigger: SelfHealTrigger,
):
    """Manually trigger self-healing for testing.

    Example:
    ```
    POST /api/v1/self-heal/trigger
    {
        "error_message": "TypeError: Cannot read property 'foo' of undefined",
        "file": "src/components/Dashboard.tsx",
        "line": 42
    }
    ```
    """
    service = get_self_heal_service()
    result = await service.handle_error(trigger)
    return result


@router.get("/status")
async def self_heal_status():
    """Get self-healing system status."""
    service = get_self_heal_service()
    return {
        "enabled": bool(service.github_token and service.github_repo),
        "github_repo": service.github_repo,
        "active_circuits": len(service._circuit_states),
        "error_patterns_seen": len(service._error_counts),
    }
