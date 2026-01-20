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

1. Open the upstream README for the authoritative CLI usage.
2. Run the CLI from the repo root so generated files land in `skills/`.
3. Validate the generated skill using `scripts/check-skills.sh` and the
   `backend/tests/test_skill_installation.py` test.

## References

- See `references/add-skill.md` for links and notes.
