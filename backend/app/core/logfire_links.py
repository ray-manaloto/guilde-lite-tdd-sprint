"""Helpers for building Logfire trace links."""

from app.core.config import settings


def build_logfire_trace_url(trace_id: str | None) -> str | None:
    if not trace_id:
        return None
    template = settings.LOGFIRE_TRACE_URL_TEMPLATE
    if not template or "{trace_id}" not in template:
        return None
    try:
        return template.format(trace_id=trace_id)
    except Exception:
        return None


def build_logfire_payload(trace_id: str | None) -> dict[str, str] | None:
    if not trace_id:
        return None
    payload: dict[str, str] = {"trace_id": trace_id}
    trace_url = build_logfire_trace_url(trace_id)
    if trace_url:
        payload["trace_url"] = trace_url
    return payload
