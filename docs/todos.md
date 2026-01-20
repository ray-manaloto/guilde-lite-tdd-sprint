# TODOs

## Testing & Validation

- [x] Align Playwright smoke suite to current UI (auth/home/sprints).
- [x] Fix sprints list pagination (fastapi_pagination.ext.sqlalchemy).
- [x] Fix Button asChild navigation to stabilize Playwright runs.
- [ ] Define integration test matrix for critical endpoints (auth, sprints, chat, tdd runs).
- [ ] Add integration tests for sprint + chat flows in backend.
- [ ] Add tests for spec workflow (complexity + API endpoints).
- [ ] Wire CI to run backend tests + Playwright smoke (LLM-gated).
- [ ] Add validation checklist to PR template or docs.
- [x] Validate Logfire token with logfire-mcp workflow.
- [ ] Review Logfire logs for LLM provider/model usage (OpenAI/Anthropic).
- [ ] Confirm OpenAI/Anthropic keys + models match env + docs.
- [ ] Configure logfire-mcp client/server (no secrets in repo) and run initial trace query.
- [ ] Resolve OpenAI model access error (openai-responses:gpt-5.2-codex 404) and re-verify logs.
- [x] Document upstream OpenAI model format conventions (template, deepagents, pydantic-ai).
- [x] Verify upstream PydanticAI version pins in referenced repos (template, deepagents, Auto-Claude).
- [x] Add OpenAI SDK smoke test script (uses .env OPENAI_API_KEY + OPENAI_MODEL).
- [x] Run OpenAI model permutation test for gpt-5.2-codex.
- [x] Standardize on OpenAI Responses API model naming (openai-responses prefix).
- [x] Enforce openai-responses prefix for OpenAI model selection (settings + agent).

## Skills & Automation

- [x] Install and review agent-browser skill for UI automation (project scope).
- [x] Install agent-skills set (react-best-practices, web-design-guidelines, vercel-deploy-claimable).
- [x] Add automated validation for required skills (script + pytest).
- [x] Add CLI wrapper skills for add-skill, dev3000, and claude-diary.
- [ ] Review dev3000 and add-skill repos for reusable testing skills (path check).
- [x] Package `skills/testing-automation` for Codex usage.
- [ ] Document how to use skills for smoke/regression testing.

## Spec Workflow (Auto-Claude Port)

- [x] Define spec workflow data model + API contract.
- [x] Implement complexity assessment + phase selection.
- [x] Implement spec creation + validation endpoints.
- [x] Add CLI entrypoint for spec runs.
