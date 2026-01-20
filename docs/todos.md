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
- [x] Review Logfire logs for LLM provider/model usage (OpenAI/Anthropic).
- [x] Confirm OpenAI/Anthropic keys + models match env + docs (using `gpt-4o-mini`).
- [x] Configure logfire-mcp client/server (no secrets in repo) and run initial trace query.
- [x] Add Logfire trace links to chat messages (WS payload + UI).
- [x] Resolve OpenAI model access error (using `gpt-4o-mini` as resolution) and re-verify logs.
- [x] Add sprint planning telemetry panel (judge + subagent trace links, chosen model).
- [x] Document upstream OpenAI model format conventions (template, deepagents, pydantic-ai).
- [x] Verify upstream PydanticAI version pins in referenced repos (template, deepagents, Auto-Claude).
- [x] Add OpenAI SDK smoke test script (uses .env OPENAI_API_KEY + OPENAI_MODEL).
- [x] Run OpenAI model permutation test for gpt-5.2-codex.
- [x] Standardize on OpenAI Responses API model naming (openai-responses prefix).
- [x] Enforce openai-responses prefix for OpenAI model selection (settings + agent).
- [x] Add direct OpenAI + Anthropic SDK clients with smoke tests (responses API).
- [x] Document API key requirements/scopes for OpenAI + Anthropic usage.
- [x] Add agent-browser tool integration tests (allow-all URL policy).
- [x] Add HTTP fetch tool for link access (allow-all URL policy).
- [x] Add Playwright logfire telemetry validation for sprint planning.
- [x] Fix `/api/specs/planning` + `/api/specs/{id}/planning/answers` proxy and stabilize planning telemetry Playwright test.

## Skills & Automation

- [x] Install and review agent-browser skill for UI automation (project scope).
- [x] Install agent-skills set (react-best-practices, web-design-guidelines, vercel-deploy-claimable).
- [x] Add automated validation for required skills (script + pytest).
- [x] Add CLI wrapper skills for add-skill, dev3000, and claude-diary.
- [ ] Review dev3000 and add-skill repos for reusable testing skills (path check).
- [x] Package `skills/testing-automation` for Codex usage.
- [ ] Document how to use skills for smoke/regression testing.
- [x] Add AI-research-SKILLs marketplace install script + validation.
- [x] Document AI-research-SKILLs marketplace usage for Codex.
- [x] Document agent-browser tool usage (default-on browser access).
- [ ] Route all prompts through OpenAI + Anthropic subagents, then judge.
- [ ] Persist subagent outputs + judge rationale in agent run records.
- [ ] Emit telemetry spans for subagent runs + judge selection.
- [ ] Add tests for judge selection + dual-subagent orchestration.
- [x] Fix WS decision serialization for datetime payloads.
- [x] Store chosen model metadata in decision checkpoints and WS payloads.
- [x] Verify history is present in checkpoints for all prompt runs.
- [x] Document HTTP fetch tool usage (default-on URL access).

## Spec Workflow (Auto-Claude Port)

- [x] Define spec workflow data model + API contract.
- [x] Implement complexity assessment + phase selection.
- [x] Implement spec creation + validation endpoints.
- [x] Add CLI entrypoint for spec runs.
- [x] Add Ralph playbook planning interview (AskUserQuestion tool) for sprint prompts.
- [x] Add spec planning endpoints (questions + answers) with artifacts storage.
- [x] Enforce planning interview before sprint creation in UI.
