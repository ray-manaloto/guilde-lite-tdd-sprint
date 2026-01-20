# Skills

This repo tracks Codex skills used for testing automation and browser validation.

## Local Skills (in-repo)

- `skills/testing-automation` — Workflow guidance for automated testing (unit + integration + Playwright).

### Package the local skill

```bash
python /Users/rmanaloto/.codex/skills/.system/skill-creator/scripts/package_skill.py \
  /Users/rmanaloto/dev/github/ray-manaloto/guilde-lite-tdd-sprint/skills/testing-automation
```

Install the resulting `.skill` file via Codex, then restart Codex.

## External Skills To Install

Use the skill installer to add these to Codex (requires network access):

```bash
/Users/rmanaloto/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo vercel-labs/agent-browser \
  --path skills/agent-browser

/Users/rmanaloto/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo vercel-labs/agent-skills \
  --path skills/react-best-practices \
  --path skills/web-design-guidelines \
  --path skills/claude.ai/vercel-deploy-claimable
```

Restart Codex after installing new skills.

## References

- https://developers.openai.com/codex/skills/
- https://developers.openai.com/codex/skills/create-skill/
- https://github.com/openai/skills
- https://agentskills.io/
