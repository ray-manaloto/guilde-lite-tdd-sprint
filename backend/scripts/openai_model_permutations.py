#!/usr/bin/env python3
"""Test OpenAI model string permutations across SDK + PydanticAI."""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings


PROMPT = "Reply with the single word: pong"
MAX_OUTPUT_TOKENS = 16
MODEL_VARIANTS = (
    "gpt-5.2-codex",
    "openai:gpt-5.2-codex",
    "openai-responses:gpt-5.2-codex",
)


@dataclass
class Result:
    label: str
    model: str
    ok: bool
    detail: str


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


async def _openai_sdk_responses(client: AsyncOpenAI, model: str) -> Result:
    label = "openai-sdk.responses"
    try:
        response = await client.responses.create(
            model=model,
            input=PROMPT,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        output = response.output_text.strip()
        return Result(label, model, True, output or "<empty>")
    except Exception as exc:  # pragma: no cover - runtime error path
        return Result(label, model, False, f"{type(exc).__name__}: {exc}")


async def _pydanticai_chat(provider: OpenAIProvider, model: str) -> Result:
    label = "pydantic-ai.chat"
    try:
        agent = Agent(
            model=OpenAIChatModel(model, provider=provider),
            model_settings=ModelSettings(max_tokens=MAX_OUTPUT_TOKENS, temperature=0),
        )
        result = await agent.run(PROMPT)
        return Result(label, model, True, result.output.strip() or "<empty>")
    except Exception as exc:  # pragma: no cover - runtime error path
        return Result(label, model, False, f"{type(exc).__name__}: {exc}")


async def _pydanticai_responses(provider: OpenAIProvider, model: str) -> Result:
    label = "pydantic-ai.responses"
    try:
        agent = Agent(
            model=OpenAIResponsesModel(model, provider=provider),
            model_settings=ModelSettings(max_tokens=MAX_OUTPUT_TOKENS, temperature=0),
        )
        result = await agent.run(PROMPT)
        return Result(label, model, True, result.output.strip() or "<empty>")
    except Exception as exc:  # pragma: no cover - runtime error path
        return Result(label, model, False, f"{type(exc).__name__}: {exc}")


async def _pydanticai_agent_string(model: str) -> Result:
    label = "pydantic-ai.agent-string"
    try:
        agent = Agent(
            model=model,
            model_settings=ModelSettings(max_tokens=MAX_OUTPUT_TOKENS, temperature=0),
        )
        result = await agent.run(PROMPT)
        return Result(label, model, True, result.output.strip() or "<empty>")
    except Exception as exc:  # pragma: no cover - runtime error path
        return Result(label, model, False, f"{type(exc).__name__}: {exc}")


async def main() -> int:
    env_path = _find_env()
    env_values = _load_env_file(env_path) if env_path else {}

    api_key = _resolve_value("OPENAI_API_KEY", env_values)
    base_url = _resolve_value("OPENAI_BASE_URL", env_values)
    org = _resolve_value("OPENAI_ORG", env_values) or _resolve_value("OPENAI_ORGANIZATION", env_values)

    if not api_key:
        print("OPENAI_API_KEY is missing in environment or .env.", file=sys.stderr)
        return 1

    os.environ.setdefault("OPENAI_API_KEY", api_key)
    if base_url:
        os.environ.setdefault("OPENAI_BASE_URL", base_url)
    if org:
        os.environ.setdefault("OPENAI_ORG", org)

    client = AsyncOpenAI(api_key=api_key, base_url=base_url, organization=org)
    provider = OpenAIProvider(openai_client=client)

    results: list[Result] = []
    for model in MODEL_VARIANTS:
        results.append(await _openai_sdk_responses(client, model))
        results.append(await _pydanticai_chat(provider, model))
        results.append(await _pydanticai_responses(provider, model))
        results.append(await _pydanticai_agent_string(model))

    await client.close()

    print("Results:")
    for result in results:
        status = "ok" if result.ok else "fail"
        print(f"- {result.label} | {result.model} | {status} | {result.detail}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
