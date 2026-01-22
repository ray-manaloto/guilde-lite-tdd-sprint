# Track: [TRACK_NAME]

> **Status:** [new | in_progress | blocked | completed]
> **Created:** [DATE]
> **SDLC Phase:** [requirements | design | implementation | quality | release]

## Quick Links

- [Specification](./spec.md) - Requirements and acceptance criteria
- [Implementation Plan](./plan.md) - SDLC-phased task breakdown
- [Metadata](./metadata.json) - Track configuration

## Summary

[One paragraph describing what this track delivers]

## SDLC Role Assignments

| Phase | Primary Role | Supporting Roles |
|-------|--------------|------------------|
| Requirements | @ba | @ceo, @research |
| Design | @architect | @data (if needed) |
| Implementation | @senior | @junior, @devops |
| Quality | @qa | @reviewer, @perf |
| Release | @cicd | @canary, @docs |

## Current Status

**Active Phase:** [Phase name]
**Current Task:** [Task description]
**Blockers:** [None | Blocker description]

## Progress

- [x] Phase 1: Requirements - [checkpoint: xxxxxxx]
- [ ] Phase 2: Design
- [ ] Phase 3: Implementation
- [ ] Phase 4: Quality
- [ ] Phase 5: Release

## Commands

```bash
# Run SDLC workflow for this track
/sdlc-orchestration:full-feature "[track summary]"

# Run specific role
/sdlc-orchestration:role architect "review design for [track]"
/sdlc-orchestration:role qa "create test plan for [track]"
```
