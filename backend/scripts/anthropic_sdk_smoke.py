#!/usr/bin/env python3
"""Anthropic SDK smoke test using env-configured key/model."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from anthropic import Anthropic

PROMPT = (
    "How do I resolve this error: "
    "The model `openai-responses:gpt-5.2-codex` does not exist or I do not have "
    "access to it? Provide steps to fix it."
)


def _load_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("'").strip('"')
        values[key] = value
    return values


def _find_env() -> Path | None:
    cwd = Path.cwd()
    for base in (cwd, cwd.parent, Path(__file__).resolve().parents[2]):
        candidate = base / ".env"
        if candidate.exists():
            return candidate
    return None


def _resolve_value(key: str, env_values: dict[str, str]) -> str | None:
    return os.environ.get(key) or env_values.get(key)


def main() -> int:
    env_path = _find_env()
    env_values = _load_env_file(env_path) if env_path else {}

    api_key = _resolve_value("ANTHROPIC_API_KEY", env_values)
    model_raw = _resolve_value("ANTHROPIC_MODEL", env_values)
    base_url = _resolve_value("ANTHROPIC_BASE_URL", env_values)

    if not api_key:
        print("ANTHROPIC_API_KEY is missing in environment or .env.", file=sys.stderr)
        return 1
    if not model_raw:
        print("ANTHROPIC_MODEL is missing in environment or .env.", file=sys.stderr)
        return 1

    model = model_raw
    if model.startswith("anthropic:"):
        model = model.split(":", 1)[1]

    print(f"Using model: {model}")
    if base_url:
        print("Using custom ANTHROPIC_BASE_URL.")

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = Anthropic(**client_kwargs)

    response = client.messages.create(
        model=model,
        max_tokens=200,
        messages=[{"role": "user", "content": PROMPT}],
    )
    text_chunks = [block.text for block in response.content if getattr(block, "text", None)]
    print("".join(text_chunks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
