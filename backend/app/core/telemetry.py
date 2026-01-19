"""Telemetry helpers for Logfire/OTel linkage."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.core.config import settings


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


def _write_telemetry_record(
    name: str,
    attrs: dict[str, Any],
    trace_id: str | None,
    span_id: str | None,
    duration_ms: int | None,
    error: str | None,
) -> None:
    """Write telemetry data to a local JSONL file when configured."""
    if not settings.TELEMETRY_FILE:
        return

    path = Path(settings.TELEMETRY_FILE)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": time.time(),
            "name": name,
            "trace_id": trace_id,
            "span_id": span_id,
            "duration_ms": duration_ms,
            "error": error,
            "attrs": attrs,
        }
        if not path.exists():
            path.touch()
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
    except Exception:
        return


@contextmanager
def telemetry_span(name: str, **attrs) -> Iterator[tuple[str | None, str | None]]:
    """Create a Logfire span when available and return trace context."""
    start = time.monotonic()
    trace_id: str | None = None
    span_id: str | None = None
    error: str | None = None

    try:
        import logfire
    except Exception:
        try:
            trace_id, span_id = get_trace_context()
            yield trace_id, span_id
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            duration_ms = int((time.monotonic() - start) * 1000)
            _write_telemetry_record(name, attrs, trace_id, span_id, duration_ms, error)
        return

    try:
        with logfire.span(name, **attrs):
            trace_id, span_id = get_trace_context()
            yield trace_id, span_id
    except Exception as exc:
        error = str(exc)
        raise
    finally:
        duration_ms = int((time.monotonic() - start) * 1000)
        _write_telemetry_record(name, attrs, trace_id, span_id, duration_ms, error)
