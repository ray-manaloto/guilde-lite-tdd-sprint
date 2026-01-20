"""Tests for direct SDK client helpers."""

from unittest.mock import Mock

import pytest

import app.agents.sdk_clients as sdk_clients


def test_get_openai_client_uses_provided_values(monkeypatch):
    """Explicit OpenAI params are forwarded to the SDK."""
    mock_openai = Mock()
    monkeypatch.setattr(sdk_clients, "OpenAI", mock_openai)

    client = sdk_clients.get_openai_client(
        api_key="test-key",
        base_url="https://api.example.com",
        organization="org-id",
    )

    mock_openai.assert_called_once_with(
        api_key="test-key",
        base_url="https://api.example.com",
        organization="org-id",
    )
    assert client is mock_openai.return_value


def test_get_openai_client_requires_key(monkeypatch):
    """Missing OpenAI key raises a helpful error."""
    monkeypatch.setattr(sdk_clients.settings, "OPENAI_API_KEY", "")
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        sdk_clients.get_openai_client()


def test_get_anthropic_client_uses_provided_values(monkeypatch):
    """Explicit Anthropic params are forwarded to the SDK."""
    mock_anthropic = Mock()
    monkeypatch.setattr(sdk_clients, "Anthropic", mock_anthropic)

    client = sdk_clients.get_anthropic_client(
        api_key="test-key",
        base_url="https://api.example.com",
    )

    mock_anthropic.assert_called_once_with(
        api_key="test-key",
        base_url="https://api.example.com",
    )
    assert client is mock_anthropic.return_value


def test_get_anthropic_client_requires_key(monkeypatch):
    """Missing Anthropic key raises a helpful error."""
    monkeypatch.setattr(sdk_clients.settings, "ANTHROPIC_API_KEY", "")
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        sdk_clients.get_anthropic_client()
