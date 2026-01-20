---
name: logfire-mcp
description: Use the Pydantic Logfire MCP server to inspect traces and debug LOGFIRE_TOKEN issues.
metadata:
  short-description: Logfire MCP debugging
---

# Logfire MCP Debugging

Use this skill to validate Logfire token setup and inspect traces via the
Pydantic Logfire MCP server.

## Workflow

1. Verify local Logfire envs with `scripts/check-logfire-env.sh` (no secrets printed).
2. Create a Logfire **read token** and export it as `LOGFIRE_READ_TOKEN`.
3. Start the MCP server with `scripts/run-logfire-mcp.sh`.
4. Use your MCP client to query recent errors or spans and confirm ingestion.

## Notes

- `LOGFIRE_TOKEN` is used by the Logfire SDK to send telemetry.
- `LOGFIRE_READ_TOKEN` is required by logfire-mcp to read traces.
- Keep tokens out of logs and commit history.

## References

- See `references/logfire-mcp.md` for command details and client config examples.
