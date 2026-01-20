#!/usr/bin/env python3
"""Validate that a Logfire trace exists using the read token."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from logfire.experimental.query_client import AsyncLogfireQueryClient


def _load_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip("'").strip('"')
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


async def _trace_exists(
    read_token: str,
    service_name: str,
    trace_id: str,
) -> bool:
    min_ts = datetime.now(UTC) - timedelta(hours=2)
    sql = (
        "SELECT trace_id "
        "FROM records "
        f"WHERE trace_id = '{trace_id}' "
        f"AND service_name = '{service_name}' "
        "LIMIT 1"
    )
    async with AsyncLogfireQueryClient(read_token) as client:
        result = await client.query_json_rows(sql, min_timestamp=min_ts)
        return bool(result.get("rows"))


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: logfire_validate_trace.py <trace_id>", file=sys.stderr)
        return 2

    trace_id = sys.argv[1]
    env_path = _find_env()
    env_values = _load_env_file(env_path) if env_path else {}

    read_token = _resolve_value("LOGFIRE_READ_TOKEN", env_values)
    service_name = _resolve_value("LOGFIRE_SERVICE_NAME", env_values) or "guilde_lite_tdd_sprint"

    if not read_token:
        print("LOGFIRE_READ_TOKEN is missing in environment or .env.", file=sys.stderr)
        return 2

    exists = asyncio.run(_trace_exists(read_token, service_name, trace_id))
    if not exists:
        print(f"Trace {trace_id} not found in Logfire.", file=sys.stderr)
        return 1

    print(f"Trace {trace_id} found in Logfire.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
