# Framework Alignment

This summarizes how the port aligns with the referenced frameworks/templates.

## Status Summary

| Source | Status | Evidence | Notes |
| --- | --- | --- | --- |
| vstorm-co/full-stack-fastapi-nextjs-llm-template | Aligned | `backend/`, `frontend/`, `README.md` | Base template structure and CLI are retained. |
| vstorm-co/pydantic-deepagents | Not integrated | `frontend/README.md` | Referenced only; no deepagents code in backend. |
| pydantic/pydantic-ai | Legacy (migration in progress) | `backend/app/agents/assistant.py`, `backend/app/api/routes/v1/agent.py` | Still used by current WS flow; do not add new usage. |
| AndyMik90/Auto-Claude | Partial parity | `docs/auto-claude-parity.md` | Spec runner, QA loop, worktrees still missing or in progress. |

## Notes

- Deepagents integration is a future decision.
- PydanticAI remains in place until the Agents SDK migration completes; avoid
  adding new PydanticAI usage in orchestration/planning.
- Auto-Claude parity remains an ongoing roadmap item.
- Upstream PydanticAI version pins for the referenced frameworks are summarized below.

## Upstream PydanticAI Versions (Checked)

- full-stack-fastapi-nextjs-llm-template: `pydantic-ai>=0.0.39` (template backend), `pydantic-ai-slim[anthropic/openrouter]>=0.0.39`.
- pydantic-deepagents: `pydantic-ai-slim>=0.1.0` (plus pydantic-ai-backend/todo).
- pydantic-ai: dynamic versioning in `pyproject.toml` (pins slim extras to the same version at release).
- Auto-Claude: no `pydantic-ai` dependency (uses `claude-agent-sdk`).

## OpenAI Model Identifier Formats (Upstream)

- full-stack-fastapi-nextjs-llm-template: `AI_MODEL=gpt-4o-mini` in env; PydanticAI example uses `model="openai:gpt-4o-mini"`.
- pydantic-deepagents: `model="openai:gpt-4.1"` (default model string includes provider prefix).
- pydantic-ai: model strings are `<provider>:<model>` (example: `openai:gpt-5`) or `openai-responses:<model>` for the Responses API.

## Project Decision (OpenAI Responses)

- This repo standardizes on the OpenAI Responses API: use `openai-responses:<model>` (for example, `openai-responses:gpt-5.2-codex`).
