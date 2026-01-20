# AI Research Skills Marketplace

This repo can install the zechenzhangAGI/AI-research-SKILLs marketplace (all plugins) into
project-scoped Codex skills.

Source:
- https://github.com/zechenzhangAGI/AI-research-SKILLs

## Install

From the repo root:

```bash
scripts/install-ai-research-skills.sh
```

This script:
- Clones the marketplace repo to a temp directory.
- Reads `.claude-plugin/marketplace.json`.
- Installs every plugin skill into `skills/` with an `ai-research-<plugin>-<skill>` prefix.
- Writes `skills/ai-research-skills.manifest.json` for validation.

## Validate

```bash
scripts/validate-ai-research-skills.sh
```

Validation checks:
- Manifest exists.
- Each installed skill has a `SKILL.md` file.
- Installed count matches the manifest.

## Notes

- Re-run the install script after upstream updates.
- Use `--force` to overwrite existing installed skills.
