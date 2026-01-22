# Conductor Workflow Initiation Prompt

Enhance the parallel agentic SDLC workflow with UI/UX roles, context engineering
subagents, documentation synchronization, crash recovery, and improved QA gates.

Inputs:
- Conductor context: conductor/product.md, conductor/tech-stack.md,
  conductor/workflow.md, conductor/tooling.md, conductor/evals.md
- Track docs: spec.md, plan.md, research.md
- Current hooks config: .claude/settings.json (project + global)

Objectives:
1. Add UI/UX roles with code-change responsibility.
2. Improve context engineering and compaction/recovery workflows.
3. Run documentation-engineer subagents in parallel and sync artifacts.
4. Update hooks strategy based on latest Claude Code guidance.
5. Improve QA automation with smoke E2E on PR and full nightly suite.
6. Document skills/plugins/tools/commands to streamline SDLC.

Traceability:
- Capture per-role artifacts in `artifacts/requirements/<role>/`.
- Store per-role state JSON for tools, skills, model, and usage.
