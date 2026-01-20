# Claude Diary References

- Repo: https://github.com/rlancemartin/claude-diary
- Blog: https://rlancemartin.github.io/2025/12/01/claude_diary/
- Paper: https://arxiv.org/pdf/2309.02427

Notes:
- Use upstream docs for installation and usage details.
- Record any required credentials or data paths in project docs.

## Quickstart

```bash
git clone https://github.com/rlancemartin/claude-diary claude-diary
cd claude-diary
cp commands/*.md ~/.claude/commands/
mkdir -p ~/.claude/hooks
cp hooks/pre-compact.sh ~/.claude/hooks/pre-compact.sh
chmod +x ~/.claude/hooks/pre-compact.sh
```

Add this hook to `~/.claude/settings.json` (global) or
`.claude/settings.local.json` (project):

```json
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "auto",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/pre-compact.sh"
          }
        ]
      }
    ]
  }
}
```

## Commands

- `/diary`: create a diary entry for the current session.
- `/reflect`: analyze diary entries and update `CLAUDE.md`.

Examples:

```bash
/reflect last 20 entries
/reflect for project /Users/username/Code/my-app
/reflect related to testing
/reflect include all entries
```
