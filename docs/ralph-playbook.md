# Ralph Playbook Integration

We are adopting the Ralph playbook loop as the agentic workflow for the
Auto-Claude port. This focuses on disciplined planning, clear JTBD scope, and
backpressure through tests.

Reference:
- https://github.com/ClaytonFarr/ralph-playbook
- https://github.com/ClaytonFarr/ralph-playbook#use-claudes-askuserquestiontool-for-planning

## Planning Interview (AskUserQuestion)

When a user submits a sprint prompt, we must start with an interview step that
collects clarifying questions (JTBD, edge cases, acceptance criteria) before
planning or implementation.

Implementation notes:
- Use an AskUserQuestion-style tool inside the planning agent.
- Store questions/answers in `spec.artifacts.planning`.
- Block sprint creation in the UI until interview answers are captured.

## Loop Phases

1. Planning interview (AskUserQuestion)
2. Plan generation (gap analysis, prioritized tasks)
3. Build/validate (tests as backpressure)

The loop is encoded as API-driven steps rather than a CLI bash loop to match the
web UI flow. Current implementation covers the planning interview and sprint
spec linkage; plan/build steps will follow.
