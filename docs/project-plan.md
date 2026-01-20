# Project Plan

## Goals

- Port Auto-Claude workflows onto the full-stack FastAPI + Next.js template.
- Provide sprint planning with an optional Kanban view.
- Keep agent UX parity where it matters (agent runs, review loops, UI).

## Milestones

1. Sprint planning API + web UI (done)
2. PydanticAI Web UI integration (done)
3. Testing automation + validation gates (planned)
4. Codex skills for test automation (planned)
5. Kanban board parity (planned)
6. Auto-Claude workflow parity (planned)

## Current Sprint (Foundation)

- [x] Sprint models, services, routes, tests
- [x] Sprint board UI (Next.js)
- [x] PydanticAI Web UI CLI entrypoint
- [ ] Automated validation plan for new/existing features
- [ ] Codex testing-automation skill (local + package)
- [ ] Install agent-browser + agent-skills in Codex
- [ ] Kanban board implementation (optional)
- [ ] Agent terminals / live run dashboard

## Validation Requirements

- Every new feature ships with automated tests (unit + API or integration).
- User-facing flows require Playwright coverage.
- CI must run unit + integration + Playwright smoke.

## Next Up

- Testing strategy doc and test scaffolds
- Kanban board UX + drag/drop
- Sprint metrics (velocity, burndown)
- Auto-Claude spec runner + phase tracking
