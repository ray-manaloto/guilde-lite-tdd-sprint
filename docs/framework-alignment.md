# Framework Alignment

This summarizes how the port aligns with the referenced frameworks/templates.

## Status Summary

| Source | Status | Evidence | Notes |
| --- | --- | --- | --- |
| vstorm-co/full-stack-fastapi-nextjs-llm-template | Aligned | `backend/`, `frontend/`, `README.md` | Base template structure and CLI are retained. |
| vstorm-co/pydantic-deepagents | Not integrated | `frontend/README.md` | Referenced only; no deepagents code in backend. |
| pydantic/pydantic-ai | Integrated | `backend/app/agents/assistant.py`, `backend/app/api/routes/v1/agent.py` | PydanticAI agent + streaming used. |
| AndyMik90/Auto-Claude | Partial parity | `docs/auto-claude-parity.md` | Spec runner, QA loop, worktrees still missing or in progress. |

## Notes

- Deepagents integration is a future decision; currently we rely on PydanticAI.
- Auto-Claude parity remains an ongoing roadmap item.
