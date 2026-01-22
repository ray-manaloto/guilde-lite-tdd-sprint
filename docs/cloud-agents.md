# Cloud Subagents (AWS Offload Plan)

This document captures the workflow integration plan for cloud-hosted AI subagents.
Conductor artifacts remain canonical; cloud agents return diffs only.

## Sources

- Research digest: `conductor/tracks/agentic_sdlc_enhancements_20260122/research.md`
- Research artifact: `conductor/tracks/agentic_sdlc_enhancements_20260122/artifacts/research/20260122T222513Z.md`
- Parallel sweep synthesis: `conductor/tracks/agentic_sdlc_enhancements_20260122/artifacts/design/parallel-cloud-agents/synthesis/20260122T222600Z.md`

## Core Workflow Principles

- Conductor artifacts (`spec.md`, `plan.md`) are the source of truth.
- Cloud subagents produce **unified diffs only** and never write to the repo directly.
- A patch pipeline validates and applies diffs after review.
- Context bundles are minimal and purpose-built per task.

## Orchestration Pattern

- Event-driven triggers (EventBridge) route tasks into Step Functions.
- SQS provides backpressure and concurrency limits.
- Lambda for short tasks; Fargate for long-running workloads with timeouts.
- A supervisor orchestrator tracks state transitions and retries.

## Security and Isolation

- Private subnets with VPC endpoints (S3, Secrets Manager); no public egress by default.
- Least-privilege IAM per subagent.
- Secrets stored in Secrets Manager and never logged.
- Timeouts and resource caps enforced per subagent.

## Observability and Cost

- CloudWatch logs + X-Ray or OpenTelemetry traces.
- Emit token usage, runtime, and Conductor task IDs.
- Budgets + anomaly detection + tagging by agent/run for cost control.

## Required Interfaces (Cloud Agent I/O)

- Input: context bundle + objective + constraints + target files.
- Output: unified diff + short summary.
- QA outputs: `verify-report.md` and JSON summary when running tests.

## Open Questions

- Lambda vs Fargate cutover thresholds.
- Patch application ownership and conflict resolution strategy.
- Cloud-run test suite scope and environments.
