# Logfire Token Debugging Notes

Context: tests emit `Failed to export span batch code: 401, reason: unknown token`.

## Likely Causes

- `LOGFIRE_TOKEN` is missing, expired, or invalid for the project.
- A **read token** was used in place of a **write token**.
- `LOGFIRE_SEND_TO_LOGFIRE=if-token-present` enables sending during tests when
  a token is present, causing noisy failures if the token is invalid.

## Verify Environment (no secrets printed)

```bash
skills/logfire-mcp/scripts/check-logfire-env.sh
```

## Preferred Dev Setup (Logfire CLI)

These steps store a project-scoped token in a local `.logfire/` directory, so you
do not need to keep `LOGFIRE_TOKEN` in `.env` for development:

```bash
cd backend
uv run logfire auth
uv run logfire projects use guilde-lite
```

If `LOGFIRE_TOKEN` remains in `.env`, it will override the CLI token.

## Validate Token Types

- `LOGFIRE_TOKEN` (write token): used by the Logfire SDK to send telemetry.
- `LOGFIRE_READ_TOKEN` (read token): used by logfire-mcp to query traces.
- Logfire API tokens are not used by the SDK or logfire-mcp in this project.

If export errors persist, rotate the write token in Logfire and update `.env`.

## Optional: Suppress test noise

Set the following in test envs if you don't want Logfire exports during tests:

```
LOGFIRE_SEND_TO_LOGFIRE=false
```

## MCP Trace Inspection

Use the logfire-mcp skill to confirm traces are ingesting once the write token is valid.
See `skills/logfire-mcp/SKILL.md` and `skills/logfire-mcp/references/logfire-mcp.md`.
