---
name: testing-automation
description: Automated testing and validation workflows for this repo (backend unit/integration/API + frontend unit + Playwright E2E). Use when adding or changing features, debugging regressions, wiring CI validation, or automating browser-based checks.
---

# Testing Automation

## Overview

Define a consistent testing workflow and validation gates for new and existing code changes.
Use this skill to choose the right test type, run the test matrix, and document results.

## Workflow Decision Tree

1. **Backend changes** → add/update unit tests + API/integration tests.
2. **Frontend UI changes** → add/update unit tests + Playwright E2E.
3. **Cross-stack changes** → run the full test matrix.
4. **Auth / OAuth flows** → prioritize Playwright coverage.

When in doubt: run full matrix and add Playwright smoke for user-facing flows.

## Validation Requirements

- Every feature ships with automated tests (unit + API/integration).
- User-facing flows require Playwright coverage.
- Update `docs/testing.md`, `docs/project-plan.md`, and `docs/todos.md` before major work.

## Core Workflow

1. Update planning docs first (`docs/project-plan.md`, `docs/todos.md`).
2. Add or update tests while implementing features.
3. Run the local test matrix (see references).
4. Document results and gaps in `docs/testing.md`.
5. If UI behavior is involved, add Playwright coverage and run E2E.

## Backend Testing

- Use pytest for unit + API + integration.
- Prefer service layer + DB session for integration tests.
- Keep API tests under `backend/tests/api/`.

## Frontend + Playwright

- Use `bun run test:run` for unit tests.
- Add Playwright smoke tests for auth, sprints, and critical dashboards.
- Ensure backend is running before E2E.

## Skill Integrations

- agent-browser can be used for quick UI smoke checks when Playwright is unavailable.
- Codex skills can be installed from GitHub via the skill-installer and used to automate checks.

## References

- `references/testing-workflow.md` for commands and test matrix
- `references/external-resources.md` for skill/tool links
