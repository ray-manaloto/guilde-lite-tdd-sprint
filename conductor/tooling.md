# Tooling and Guardrails

## Allowed Tools (Default)

- File read/list/search tools
- File write/edit/patch tools
- Git read commands (status, diff, log)
- Test and lint commands
- OpenAI Deep Research API (planning stage)

## Restricted Tools (Require Approval)

- Network fetch
- Package installs and upgrades
- Docker and compose operations
- Git write operations (commit, merge, push)
- External service calls (GitHub, MCP, etc.)

## Prohibited Tools (Default)

- Destructive commands without explicit approval
- Unbounded shell execution in untrusted contexts

## Approval Policy

- If confidence is low, require user confirmation before executing restricted
  tools.
- Always explain why a restricted tool is needed.
