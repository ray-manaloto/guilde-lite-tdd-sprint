# Auto-Claude Feature Parity Review

Scope: Auto-Claude repo at `/Users/rmanaloto/Auto-Claude` compared to the current port in
`/Users/rmanaloto/dev/github/ray-manaloto/guilde-lite-tdd-sprint`.

Status legend:
- Present: comparable capability exists in the port
- Partial: related capability exists but lacks core behavior or scope
- Missing: no comparable capability found in the port

## Core Workflow And Specs

| Capability | Auto-Claude evidence | Port status | Port evidence / notes |
| --- | --- | --- | --- |
| Spec creation (interactive) | `guides/CLI-USAGE.md`, `apps/backend/runners/spec_runner.py` | Partial | Spec draft API + CLI exist; planning interview still pending. |
| Spec complexity tiers | `guides/CLI-USAGE.md`, `apps/backend/spec/complexity.py` | Partial | Heuristic complexity tiers exist; needs richer signals. |
| Spec validation checkpoints | `apps/backend/spec/validate_spec.py` | Partial | Basic validation endpoint exists; no QA loop yet. |
| Implementation plan + phases | `apps/backend/implementation_plan/`, `apps/backend/spec/phases.py` | Missing | No implementation plan model or phase runner. |
| Follow-up planning | `apps/backend/agents/planner.py`, `apps/backend/cli/followup_commands.py` | Missing | No follow-up planner or CLI. |

## Agent Architecture And Orchestration

| Capability | Auto-Claude evidence | Port status | Port evidence / notes |
| --- | --- | --- | --- |
| Multi-role agents (planner/coder/QA) | `apps/backend/agents/` | Missing | Port has a single assistant agent. |
| Session orchestration + recovery | `apps/backend/agents/session.py`, `apps/backend/recovery.py` | Missing | No recovery or session orchestrator. |
| Multi-agent parallel runs | `apps/backend/service_orchestrator.py` | Partial | Port runs parallel subagents in TDD flow. `backend/app/services/agent_tdd.py`. |
| Tool permission system | `apps/backend/agents/tools_pkg/` | Missing | Port only registers a simple datetime tool. |

## QA And Review

| Capability | Auto-Claude evidence | Port status | Port evidence / notes |
| --- | --- | --- | --- |
| QA validation loop (reviewer/fixer) | `apps/backend/qa/loop.py`, `apps/backend/qa/reviewer.py`, `apps/backend/qa/fixer.py` | Missing | No QA loop or QA agents. |
| QA reports and criteria | `apps/backend/qa/report.py`, `apps/backend/qa/criteria.py` | Missing | No QA report generation. |
| Human review checkpoint | `apps/backend/review/` | Missing | No review gating in port. |

## Workspace Isolation And Git Flow

| Capability | Auto-Claude evidence | Port status | Port evidence / notes |
| --- | --- | --- | --- |
| Git worktrees per spec | `apps/backend/core/worktree.py` | Missing | No worktree logic. |
| Review/merge/discard workspaces | `apps/backend/cli/workspace_commands.py` | Missing | No workspace management commands. |
| Create PR from worktree | `apps/backend/core/worktree.py` | Missing | No PR creation workflow. |

## Merge And Conflict Resolution

| Capability | Auto-Claude evidence | Port status | Port evidence / notes |
| --- | --- | --- | --- |
| AI merge + conflict analysis | `apps/backend/merge/` | Missing | No merge assistant or conflict analysis. |
| Semantic file evolution tracking | `apps/backend/merge/file_evolution/` | Missing | No file evolution tracking. |

## Memory And Knowledge

| Capability | Auto-Claude evidence | Port status | Port evidence / notes |
| --- | --- | --- | --- |
| Graphiti memory layer | `apps/backend/integrations/graphiti/`, `apps/backend/graphiti_config.py` | Missing | No Graphiti integration in port. |
| File-based memory fallback | `apps/backend/agents/memory_manager.py` | Missing | No memory persistence outside DB runs. |

## Integrations

| Capability | Auto-Claude evidence | Port status | Port evidence / notes |
| --- | --- | --- | --- |
| GitHub integration | `apps/backend/runners/github/` | Missing | No GitHub client or workflows. |
| GitLab integration | `apps/backend/integrations/` + `.env.example` | Missing | No GitLab support. |
| Linear integration | `apps/backend/integrations/linear/` | Missing | No Linear support. |
| Electron MCP integration | `apps/backend/.env.example` | Missing | No Electron MCP tooling. |

## UI/UX

| Capability | Auto-Claude evidence | Port status | Port evidence / notes |
| --- | --- | --- | --- |
| Desktop Electron app | `apps/frontend/` | Missing | Port ships a Next.js web UI instead. |
| Kanban board + agent terminals | `README.md` (Auto-Claude UI section) | Partial | Sprint board exists in Next.js (`frontend/src/app/[locale]/(dashboard)/sprints/page.tsx`). Kanban is a placeholder and agent terminals are missing. |
| Auto updates + packaging | `README.md`, `scripts/` | Missing | No desktop packaging pipeline. |

## Analysis, Ideation, Roadmap

| Capability | Auto-Claude evidence | Port status | Port evidence / notes |
| --- | --- | --- | --- |
| Ideation pipeline | `apps/backend/ideation/` | Missing | No ideation workflows. |
| Roadmap generator | `apps/backend/runners/roadmap_runner.py` | Missing | No roadmap tooling. |
| Insights and risk analysis | `apps/backend/analysis/`, `apps/backend/insight_extractor.py` | Missing | No insight extractor or risk classifier. |

## Security And Guardrails

| Capability | Auto-Claude evidence | Port status | Port evidence / notes |
| --- | --- | --- | --- |
| Command allowlist + sandboxing | `apps/backend/security/` | Missing | Port has standard API security but no tool sandbox. |
| Secret scanning | `apps/backend/scan_secrets.py`, `apps/backend/scan-for-secrets` | Missing | No secret scanner. |

## Observability And Telemetry

| Capability | Auto-Claude evidence | Port status | Port evidence / notes |
| --- | --- | --- | --- |
| Phase/progress event logging | `apps/backend/phase_event.py`, `apps/backend/progress.py` | Missing | No phase event system. |
| Run checkpointing + replay | `apps/backend/qa_loop.py` (state), `apps/backend/progress.py` | Partial | Port has run/candidate/checkpoint models with fork support. `backend/app/services/agent_run.py`. |
| Logfire or equivalent tracing | Not explicit in Auto-Claude | Present | Port uses Logfire and file telemetry. `backend/app/core/logfire_setup.py`, `backend/app/core/telemetry.py`. |

## Provider And Auth Model

| Capability | Auto-Claude evidence | Port status | Port evidence / notes |
| --- | --- | --- | --- |
| Claude Code OAuth flow | `apps/backend/.env.example`, `guides/CLI-USAGE.md` | Missing | Port uses API keys, not Claude Code OAuth. |
| Multi-provider LLM support | `apps/backend/.env.example` (Graphiti providers) | Present | Port supports OpenAI/Anthropic/OpenRouter in `backend/app/agents/assistant.py`. |

## Notes And Risks

- The port currently provides a general AI web app scaffold with a TDD-style multi-subagent run,
  but it does not implement Auto-Claude's spec-driven planning, QA loop, worktree isolation, or
  merge automation.
- Sprint planning UI is now available in the web app, but Kanban and agent terminals remain gaps.
- PydanticAI Web UI is available for agent demos via CLI; it is not a replacement for Auto-Claude's desktop UX.
- If full parity is required, the missing capabilities above represent substantial new feature
  work (not configuration changes).
