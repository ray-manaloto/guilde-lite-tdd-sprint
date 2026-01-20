"""Tests for Logfire link helpers."""

from app.core.config import settings
from app.core.logfire_links import build_logfire_payload, build_logfire_trace_url


def test_build_logfire_trace_url_requires_template(monkeypatch):
    monkeypatch.setattr(settings, "LOGFIRE_TRACE_URL_TEMPLATE", None)
    assert build_logfire_trace_url("trace-123") is None


def test_build_logfire_trace_url_requires_placeholder(monkeypatch):
    monkeypatch.setattr(
        settings,
        "LOGFIRE_TRACE_URL_TEMPLATE",
        "https://logfire.example/trace",
    )
    assert build_logfire_trace_url("trace-123") is None


def test_build_logfire_trace_url_formats(monkeypatch):
    monkeypatch.setattr(
        settings,
        "LOGFIRE_TRACE_URL_TEMPLATE",
        "https://logfire.example/trace/{trace_id}",
    )
    assert (
        build_logfire_trace_url("trace-123")
        == "https://logfire.example/trace/trace-123"
    )


def test_build_logfire_payload_includes_url(monkeypatch):
    monkeypatch.setattr(
        settings,
        "LOGFIRE_TRACE_URL_TEMPLATE",
        "https://logfire.example/trace/{trace_id}",
    )
    assert build_logfire_payload("trace-123") == {
        "trace_id": "trace-123",
        "trace_url": "https://logfire.example/trace/trace-123",
    }
