---
name: add-skill-cli
description: Use the vercel-labs/add-skill CLI to scaffold and update Codex skills for this repo.
metadata:
  short-description: Add-skill CLI wrapper
---

# Add-Skill CLI

Use this skill when you need to scaffold a new Codex skill or update existing skill
structure using the `vercel-labs/add-skill` CLI.

## Workflow

1. Use the helper scripts in `scripts/` to list or install skills:
   - `scripts/list-agent-skills.sh`
   - `scripts/install-agent-skills.sh`
2. Run the CLI from the repo root so generated files land in `skills/`.
3. Validate with `scripts/check-skills.sh` and
   `uv run --directory backend pytest tests/test_skill_installation.py`.

## References

- See `references/add-skill.md` for links and notes.
