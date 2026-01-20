#!/usr/bin/env python3
"""List OpenAI models using PydanticAI's OpenAI provider."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from openai import AsyncOpenAI
from pydantic_ai.providers.openai import OpenAIProvider


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


async def main() -> int:
    env_path = _find_env()
    env_values = _load_env_file(env_path) if env_path else {}

    api_key = _resolve_value("OPENAI_API_KEY", env_values)
    base_url = _resolve_value("OPENAI_BASE_URL", env_values)
    org = _resolve_value("OPENAI_ORG", env_values) or _resolve_value("OPENAI_ORGANIZATION", env_values)

    if not api_key:
        print("OPENAI_API_KEY is missing in environment or .env.", file=sys.stderr)
        return 1

    if org or base_url:
        openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url, organization=org)
        provider = OpenAIProvider(openai_client=openai_client)
    else:
        provider = OpenAIProvider(api_key=api_key, base_url=base_url)

    try:
        models = await provider.client.models.list()
        items = getattr(models, "data", [])
        model_ids = sorted({getattr(model, "id", "") for model in items if getattr(model, "id", None)})
        print(f"Models returned: {len(model_ids)}")
        for model_id in model_ids:
            print(model_id)
    finally:
        await provider.client.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
