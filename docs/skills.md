# Skills

This repo tracks Codex skills used for testing automation and browser validation.

## Local Skills (in-repo)

- `skills/testing-automation` — Workflow guidance for automated testing (unit + integration + Playwright).
- `skills/agent-browser` — Browser automation skill (installed from vercel-labs/agent-browser).
- `skills/react-best-practices` — UI best practices skill (from vercel-labs/agent-skills).
- `skills/web-design-guidelines` — Design guidance skill (from vercel-labs/agent-skills).
- `skills/vercel-deploy-claimable` — Deployment claim skill (from vercel-labs/agent-skills).
- `skills/add-skill-cli` — CLI usage wrapper for vercel-labs/add-skill.
- `skills/dev3000-cli` — CLI usage wrapper for vercel-labs/dev3000.
- `skills/claude-diary` — Workflow notes for claude-diary.

These CLI wrapper skills include reference docs and runnable scripts under each
skill's `scripts/` directory.

### Package the local skill

```bash
python /Users/rmanaloto/.codex/skills/.system/skill-creator/scripts/package_skill.py \
  /Users/rmanaloto/dev/github/ray-manaloto/guilde-lite-tdd-sprint/skills/testing-automation
```

Install the resulting `.skill` file via Codex, then restart Codex.

## External Skills To Install

Use the skill installer to add these at project scope (requires network access):

```bash
python /Users/rmanaloto/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo vercel-labs/agent-browser \
  --path skills/agent-browser \
  --dest /Users/rmanaloto/dev/github/ray-manaloto/guilde-lite-tdd-sprint/skills

python /Users/rmanaloto/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo vercel-labs/agent-skills \
  --path skills/react-best-practices \
  --path skills/web-design-guidelines \
  --path skills/claude.ai/vercel-deploy-claimable \
  --dest /Users/rmanaloto/dev/github/ray-manaloto/guilde-lite-tdd-sprint/skills

python /Users/rmanaloto/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo vercel-labs/add-skill \
  --path skills/add-skill \
  --dest /Users/rmanaloto/dev/github/ray-manaloto/guilde-lite-tdd-sprint/skills
```

Note: `vercel-labs/add-skill` does not currently expose a `skills/` directory. If
the repo layout changes, update the path above.

Restart Codex after installing new skills so they are discovered.

## Validation

Required skills are tracked in `skills/required-skills.txt`.

```bash
scripts/check-skills.sh
```

## References

- https://developers.openai.com/codex/skills/
- https://developers.openai.com/codex/skills/create-skill/
- https://github.com/openai/skills
- https://agentskills.io/
