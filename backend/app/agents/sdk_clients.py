"""Direct SDK clients for OpenAI and Anthropic."""

from __future__ import annotations

from anthropic import Anthropic
from openai import OpenAI

from app.core.config import settings


def get_openai_client(
    api_key: str | None = None,
    base_url: str | None = None,
    organization: str | None = None,
) -> OpenAI:
    """Create an OpenAI SDK client with explicit or configured settings."""
    resolved_key = api_key or settings.OPENAI_API_KEY
    if not resolved_key:
        raise ValueError("OPENAI_API_KEY is required to create an OpenAI client")

    client_kwargs: dict[str, str] = {"api_key": resolved_key}

    resolved_base_url = base_url or settings.OPENAI_BASE_URL
    if resolved_base_url:
        client_kwargs["base_url"] = resolved_base_url

    resolved_org = organization or settings.OPENAI_ORG
    if resolved_org:
        client_kwargs["organization"] = resolved_org

    return OpenAI(**client_kwargs)


def get_anthropic_client(
    api_key: str | None = None,
    base_url: str | None = None,
) -> Anthropic:
    """Create an Anthropic SDK client with explicit or configured settings."""
    resolved_key = api_key or settings.ANTHROPIC_API_KEY
    if not resolved_key:
        raise ValueError("ANTHROPIC_API_KEY is required to create an Anthropic client")

    client_kwargs: dict[str, str] = {"api_key": resolved_key}

    resolved_base_url = base_url or settings.ANTHROPIC_BASE_URL
    if resolved_base_url:
        client_kwargs["base_url"] = resolved_base_url

    return Anthropic(**client_kwargs)
