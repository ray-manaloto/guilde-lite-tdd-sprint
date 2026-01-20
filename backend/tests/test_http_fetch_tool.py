"""Tests for HTTP fetch tool."""

import httpx
import pytest

from app.agents.tools.http_fetch import fetch_url_content


def test_fetch_requires_url():
    """Empty URL is rejected."""
    with pytest.raises(ValueError, match="URL is required"):
        fetch_url_content("")


def test_fetch_returns_text(monkeypatch):
    """Text responses are returned with status and content-type."""
    response = httpx.Response(
        200,
        headers={"content-type": "text/plain"},
        text="hello world",
    )
    monkeypatch.setattr(httpx, "get", lambda *_args, **_kwargs: response)

    output = fetch_url_content("https://example.com")
    assert output.startswith("status=200")
    assert "content-type=text/plain" in output
    assert "hello world" in output


def test_fetch_handles_request_error(monkeypatch):
    """Request errors return a readable message."""
    def _raise(*_args, **_kwargs):
        raise httpx.RequestError("boom", request=httpx.Request("GET", "https://example.com"))

    monkeypatch.setattr(httpx, "get", _raise)

    output = fetch_url_content("https://example.com")
    assert output.startswith("request failed:")


def test_fetch_truncates_text(monkeypatch):
    """Large responses are truncated with a marker."""
    response = httpx.Response(
        200,
        headers={"content-type": "text/plain"},
        text="a" * 30,
    )
    monkeypatch.setattr(httpx, "get", lambda *_args, **_kwargs: response)

    output = fetch_url_content("https://example.com", max_chars=10)
    assert output.endswith("...[truncated]")
