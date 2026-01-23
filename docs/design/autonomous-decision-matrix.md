# Autonomous Hooks Decision Matrix

Reference guide for determining how operations should be handled in autonomous Claude Code sessions.

## Trust Levels

| Level | Name | Decision | User Interaction |
|-------|------|----------|------------------|
| 1 | Auto-Approve | `allow` | None |
| 2 | Warn-and-Proceed | `warn` | Warning injected, continues |
| 3 | Require Approval | `ask` or `block` | Must confirm or blocked |

---

## Read Operations (Trust Level 1 - Auto-Approve)

All read operations are inherently safe and auto-approved.

| Tool | Pattern | Decision | Notes |
|------|---------|----------|-------|
| Read | `*` | Allow | Read any file |
| Grep | `*` | Allow | Search any pattern |
| Glob | `*` | Allow | Find any files |
| WebSearch | `*` | Allow | Search the web |
| WebFetch | `*` | Allow | Fetch URL content |
| ListMcpResourcesTool | `*` | Allow | List MCP resources |
| ReadMcpResourceTool | `*` | Allow | Read MCP resources |

---

## Git Operations

### Read-Only (Trust Level 1)

| Command | Decision | Rationale |
|---------|----------|-----------|
| `git status` | Allow | View working tree |
| `git diff` | Allow | View changes |
| `git diff --staged` | Allow | View staged changes |
| `git log` | Allow | View history |
| `git show` | Allow | View commits |
| `git branch` | Allow | List branches |
| `git branch -a` | Allow | List all branches |
| `git ls-files` | Allow | List tracked files |
| `git rev-parse` | Allow | Get commit info |

### Staging (Trust Level 2)

| Command | Decision | Rationale |
|---------|----------|-----------|
| `git add <file>` | Warn | Staging is reversible |
| `git add -p` | Warn | Interactive staging |
| `git stash` | Warn | Temporary storage |
| `git stash pop` | Warn | Restore stash |
| `git checkout -b <branch>` | Warn | Create branch |
| `git branch -d <branch>` | Warn | Delete merged branch |

### History-Altering (Trust Level 3)

| Command | Decision | Rationale |
|---------|----------|-----------|
| `git commit` | Ask | Creates permanent history |
| `git commit --amend` | Ask | Modifies history |
| `git push` | Ask | Remote changes |
| `git push --force` | **Block** | Destructive to remote |
| `git push -f` | **Block** | Destructive to remote |
| `git reset --hard` | **Block** | Destroys local changes |
| `git checkout .` | **Block** | Destroys uncommitted |
| `git restore .` | **Block** | Destroys uncommitted |
| `git clean -f` | **Block** | Removes untracked |
| `git clean -fd` | **Block** | Removes directories |
| `git rebase` | Ask | History rewrite |
| `git merge` | Ask | Combines branches |

---

## File Operations

### Code Files (Trust Level 2)

| Pattern | Decision | Backpressure |
|---------|----------|--------------|
| `*.py` | Warn | ruff, mypy, bandit |
| `*.ts` | Warn | tsc, prettier |
| `*.tsx` | Warn | tsc, prettier |
| `*.js` | Warn | eslint, prettier |
| `*.jsx` | Warn | eslint, prettier |

### Config Files (Trust Level 2)

| Pattern | Decision | Notes |
|---------|----------|-------|
| `*.json` | Warn | Except package-lock.json |
| `*.yaml` | Warn | Config files |
| `*.yml` | Warn | Config files |
| `*.toml` | Warn | Python/Rust config |
| `*.md` | Warn | Documentation |

### Sensitive Files (Trust Level 3)

| Pattern | Decision | Rationale |
|---------|----------|-----------|
| `.env` | **Block** | Contains secrets |
| `.env.*` | **Block** | Environment-specific secrets |
| `*/.env` | **Block** | Nested env files |
| `*.pem` | **Block** | Certificates |
| `*.key` | **Block** | Private keys |
| `*secret*` | **Block** | Secret files |
| `*credential*` | **Block** | Credential files |
| `*password*` | **Block** | Password files |
| `config/production*` | **Block** | Production config |

### Lock Files (Trust Level 3)

| Pattern | Decision | Rationale |
|---------|----------|-----------|
| `bun.lock` | **Block** | Managed by bun |
| `package-lock.json` | **Block** | Managed by npm |
| `uv.lock` | **Block** | Managed by uv |
| `*.lock` | **Block** | Generic lock files |

### Migration Files (Trust Level 3)

| Pattern | Decision | Rationale |
|---------|----------|-----------|
| `*/alembic/versions/*.py` | **Block** | Create new instead |
| `*/migrations/*.py` | **Block** | Django migrations |

---

## Test and Lint Commands (Trust Level 1)

All validation commands are auto-approved.

### Python

| Command | Decision | Output |
|---------|----------|--------|
| `uv run pytest` | Allow | Test results |
| `uv run pytest -x` | Allow | Fail fast |
| `uv run pytest --cov` | Allow | Coverage |
| `uv run ruff check` | Allow | Lint results |
| `uv run ruff format` | Allow | Format code |
| `uv run mypy` | Allow | Type check |
| `uv run bandit` | Allow | Security scan |

### JavaScript/TypeScript

| Command | Decision | Output |
|---------|----------|--------|
| `bun run test` | Allow | Test results |
| `bun run lint` | Allow | Lint results |
| `bun run type-check` | Allow | tsc --noEmit |
| `bun run prettier` | Allow | Format code |
| `npm test` | Allow | Test results |
| `npm run lint` | Allow | Lint results |
| `npm run build` | Allow | Build output |

---

## Package Management (Trust Level 2)

| Command | Decision | Rationale |
|---------|----------|-----------|
| `npm install` | Warn | Modifies node_modules |
| `npm install <pkg>` | Warn | Adds dependency |
| `bun install` | Warn | Modifies node_modules |
| `bun add <pkg>` | Warn | Adds dependency |
| `uv add <pkg>` | Warn | Adds dependency |
| `uv sync` | Warn | Syncs dependencies |

---

## Docker Operations

### Read-Only (Trust Level 1)

| Command | Decision | Rationale |
|---------|----------|-----------|
| `docker ps` | Allow | List containers |
| `docker ps -a` | Allow | List all containers |
| `docker logs` | Allow | View logs |
| `docker inspect` | Allow | View config |
| `docker images` | Allow | List images |

### Create (Trust Level 2)

| Command | Decision | Rationale |
|---------|----------|-----------|
| `docker build` | Warn | Creates image |
| `docker run` | Warn | Creates container |
| `docker-compose up` | Warn | Creates services |

### Destructive (Trust Level 3)

| Command | Decision | Rationale |
|---------|----------|-----------|
| `docker rm` | Ask | Removes container |
| `docker rmi` | Ask | Removes image |
| `docker system prune` | **Block** | Bulk removal |
| `docker-compose down -v` | Ask | Removes volumes |

---

## Deployment Commands (Trust Level 3)

All deployment commands require approval and SDLC release phase.

| Command | Decision | Phase Gate |
|---------|----------|------------|
| `kubectl apply` | Ask | Release only |
| `kubectl delete` | Ask | Release only |
| `terraform apply` | Ask | Release only |
| `terraform destroy` | **Block** | Manual only |
| `git push` (to main) | Ask | Release only |

---

## SDLC Phase Gates

Independent of trust levels, these gates enforce workflow order.

| Current Phase | Blocked Operations | Message |
|--------------|-------------------|---------|
| requirements | `implement`, `code`, `build` | "Complete design phase first" |
| design | `deploy`, `release`, `ship` | "Complete implementation+quality first" |
| implementation | `deploy`, `release`, `ship` | "Complete quality phase first" |
| quality | (none blocked) | - |
| release | (none blocked) | - |

---

## Backpressure Signals

Signals injected into model context after operations.

| Signal | Source | Severity | Agent Response |
|--------|--------|----------|----------------|
| `[BACKPRESSURE:LINT]` | ruff, eslint | Warning | Fix before continuing |
| `[BACKPRESSURE:TYPE]` | mypy, tsc | Warning | Fix type errors |
| `[BACKPRESSURE:TEST]` | pytest, jest | Error | Must fix failing tests |
| `[BACKPRESSURE:SECURITY]` | bandit | Critical | Address vulnerabilities |
| `[BACKPRESSURE:COMMAND]` | Non-zero exit | Warning | Review output |
| `[SDLC GATE]` | Phase check | Block | Cannot skip phases |
| `[STOP VALIDATION]` | Stop hook | Info | Summary at end |

---

## Decision Flowchart

```
Operation Requested
        |
        v
+-------+-------+
| Is it a Read  |--Yes--> ALLOW (Trust Level 1)
| operation?    |
+-------+-------+
        | No
        v
+-------+-------+
| Does it match |--Yes--> BLOCK (Trust Level 3)
| deny pattern? |
+-------+-------+
        | No
        v
+-------+-------+
| Does it match |--Yes--> ALLOW (Trust Level 1)
| allow pattern?|
+-------+-------+
        | No
        v
+-------+-------+
| Is it a write |--Yes--> WARN + Backpressure (Trust Level 2)
| to code file? |
+-------+-------+
        | No
        v
+-------+-------+
| Is it history |--Yes--> ASK for approval (Trust Level 3)
| altering git? |
+-------+-------+
        | No
        v
+-------+-------+
| Is SDLC phase |--Yes--> BLOCK with phase message
| gate violated?|
+-------+-------+
        | No
        v
    DEFAULT: ASK
```

---

## Configuration Quick Reference

### settings.json `permissions.allow` patterns

```json
[
  "Read(*)",
  "Grep(*)",
  "Glob(*)",
  "Task(*)",
  "WebSearch(*)",
  "WebFetch(*)",
  "Bash(git status*)",
  "Bash(git diff*)",
  "Bash(git log*)",
  "Bash(uv run pytest*)",
  "Bash(uv run ruff*)",
  "Bash(bun run test*)",
  "Bash(bun run lint*)"
]
```

### settings.json `permissions.deny` patterns

```json
[
  "Edit(.env*)",
  "Edit(*.lock)",
  "Write(.env*)",
  "Write(*.key)",
  "Bash(git push --force*)",
  "Bash(git reset --hard*)",
  "Bash(rm -rf*)",
  "Bash(sudo *)"
]
```
