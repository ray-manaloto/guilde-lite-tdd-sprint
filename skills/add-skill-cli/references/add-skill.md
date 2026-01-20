# Add-Skill CLI References

- Repo: https://github.com/vercel-labs/add-skill

Notes:
- Use the upstream README for install/usage steps.
- This repo does not ship a `skills/` directory; treat it as a CLI tool.

## Quick start

```bash
npx add-skill vercel-labs/agent-skills --list
```

Install specific skills into this repo's `skills/` directory by targeting the
`clawdbot` agent (project path: `skills/`):

```bash
npx add-skill vercel-labs/agent-skills \
  --agent clawdbot \
  --skill react-best-practices \
  --skill web-design-guidelines \
  --yes
```

## Options

- `-g, --global`: install to user directory instead of project.
- `-a, --agent <agents...>`: target agents (e.g., `codex`, `claude-code`, `clawdbot`).
- `-s, --skill <skills...>`: install specific skills by name.
- `-l, --list`: list available skills without installing.
- `-y, --yes`: skip confirmation prompts.

## Project notes

- For this repo, prefer project-scope installs that land in `skills/`.
- Validate with `scripts/check-skills.sh` after installs.
