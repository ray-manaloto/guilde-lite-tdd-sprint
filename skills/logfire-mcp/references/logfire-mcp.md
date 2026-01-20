# Logfire MCP References

- Repo: https://github.com/pydantic/logfire-mcp

## Requirements

- `uv` installed (`uvx` is used to run the MCP server).
- Logfire **read token** (project-specific).

Create a read token:
https://logfire.pydantic.dev/-/redirect/latest-project/settings/read-tokens

## Run the MCP server

```bash
LOGFIRE_READ_TOKEN=YOUR_READ_TOKEN uvx logfire-mcp@latest
```

Using a repo `.env`:

```bash
LOGFIRE_READ_TOKEN=pylf_v1_us_...
```

The helper script `scripts/run-logfire-mcp.sh` will read this value if the
environment variable is not already set.

Or pass flags:

```bash
uvx logfire-mcp@latest --read-token=YOUR_READ_TOKEN
```

## Base URL (self-hosted)

```bash
LOGFIRE_BASE_URL=https://logfire.my-company.com uvx logfire-mcp@latest --read-token=YOUR_READ_TOKEN
```

## Client examples

Claude Code:
```bash
claude mcp add logfire -e LOGFIRE_READ_TOKEN=YOUR_TOKEN -- uvx logfire-mcp@latest
```

Cursor (project `.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "logfire": {
      "command": "uvx",
      "args": ["logfire-mcp@latest", "--read-token=YOUR-TOKEN"]
    }
  }
}
```
