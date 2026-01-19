"""Telemetry helpers for Logfire/OTel linkage."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager


def get_trace_context() -> tuple[str | None, str | None]:
    """Return the current trace/span IDs if available."""
    try:
        from opentelemetry import trace
    except Exception:
        return None, None

    span = trace.get_current_span()
    ctx = span.get_span_context()
    if not ctx or not ctx.is_valid:
        return None, None
    return f"{ctx.trace_id:032x}", f"{ctx.span_id:016x}"


@contextmanager
def telemetry_span(name: str, **attrs) -> Iterator[tuple[str | None, str | None]]:
    """Create a Logfire span when available and return trace context."""
    try:
        import logfire
    except Exception:
        yield get_trace_context()
        return

    try:
        with logfire.span(name, **attrs):
            yield get_trace_context()
    except Exception:
        yield get_trace_context()
