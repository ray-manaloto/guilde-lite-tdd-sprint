# everything-claude-code Review (Codex Adaptation)

Source repo: https://github.com/affaan-m/everything-claude-code

Parallel sweep artifacts:
- `conductor/tracks/agentic_sdlc_enhancements_20260122/artifacts/design/parallel-ecc/ui-ux/20260122T215158Z.md`
- `conductor/tracks/agentic_sdlc_enhancements_20260122/artifacts/design/parallel-ecc/context-engineering/20260122T215158Z.md`
- `conductor/tracks/agentic_sdlc_enhancements_20260122/artifacts/design/parallel-ecc/documentation/20260122T215158Z.md`
- `conductor/tracks/agentic_sdlc_enhancements_20260122/artifacts/design/parallel-ecc/qa-automation/20260122T215158Z.md`
- `conductor/tracks/agentic_sdlc_enhancements_20260122/artifacts/design/parallel-ecc/synthesis/20260122T215158Z.md`

## Recommended Adoptions (Codex)

### Agents
- planner
- architect
- code-reviewer
- security-reviewer
- e2e-runner
- doc-updater
- build-error-resolver

### Commands
- /plan
- /verify
- /code-review
- /e2e
- /tdd
- /test-coverage
- /update-docs
- /update-codemaps
- /checkpoint

### Hooks (Codex wrappers)
- SessionStart/Stop/PreCompact memory persistence
- strategic-compact reminder hook
- PostToolUse formatting: Prettier + TypeScript check
- PostToolUse console.log warnings + final audit

### Skills
- frontend-patterns
- coding-standards
- verification-loop
- eval-harness
- security-review
- tdd-workflow

## UI/UX Role Integration

- Add `ui-ux-reviewer` or extend `code-reviewer` with a UI/UX checklist:
  - Accessibility (a11y), contrast, keyboard navigation
  - Responsive behavior, spacing consistency, typography hierarchy
  - Motion and interaction feedback in critical flows
- Route UI/UX checks through `/code-review` + `/e2e` when UI changes land.

## Documentation Sync

- Treat `/update-docs` + `/update-codemaps` as a standard Doc Sync phase before PR creation.
- Keep doc updates parallel with implementation using a dedicated `doc-updater` agent.

## Do-Not-Adopt (for Codex)

- PreToolUse hook that blocks new `.md/.txt` files (conflicts with documentation workflows).
- tmux reminder and dev-server block hooks (low value in CI or Codex context).
- git push pause hook (interferes with automation).
- Auto-merge of continuous-learning outputs (risk of unreviewed changes).
- Mandatory `/e2e` on every PR (too slow; reserve for nightly or UI-critical changes).

## Integration Guidance

- Add `CODEX.md` as the canonical project context (Codex equivalent of CLAUDE.md).
- Port everything-claude-code hooks into Codex wrapper scripts (repo scripts + CI gates).
- Use a two-tier gate:
  - PR Smoke: format + TS check + /code-review + /verify + /test-coverage
  - Nightly: /e2e + eval-harness + build-error-resolver

