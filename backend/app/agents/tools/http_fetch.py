"""HTTP fetch tool for retrieving URL content."""

from __future__ import annotations

import httpx


def fetch_url_content(
    url: str,
    timeout_seconds: int = 15,
    max_chars: int = 12000,
) -> str:
    """Fetch URL content and return a trimmed text response."""
    if not url or not url.strip():
        raise ValueError("URL is required")

    try:
        response = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
    except httpx.RequestError as exc:
        return f"request failed: {exc}"

    content_type = response.headers.get("content-type", "").strip()
    text = response.text or ""

    if not text.strip():
        return (
            f"non-text response: status={response.status_code} "
            f"content-type={content_type or 'unknown'}"
        )

    text = text.strip()
    if len(text) > max_chars:
        text = f"{text[:max_chars]}\n...[truncated]"

    return f"status={response.status_code}\ncontent-type={content_type}\n\n{text}"
