# Artifact Management System Design

> **Version:** 1.0.0
> **Status:** Draft
> **Author:** Data Scientist Agent
> **Date:** 2026-01-22
> **Phase:** Design (SDLC Phase 2)

## Executive Summary

This document specifies the design for a file-based artifact management system for SDLC phase outputs. Based on Phase 1 research findings, file-based artifact handoffs reduce token overhead by 60-80% compared to inline outputs. The system enables orchestrators to read consolidated artifacts instead of processing raw agent outputs, supports rollback to previous phase artifacts, and includes comprehensive metadata tracking.

---

## 1. Directory Structure

### 1.1 Root Layout

```
artifacts/
├── {sprint_id}/                      # Sprint-scoped artifacts
│   ├── manifest.json                 # Sprint metadata and artifact index
│   ├── requirements/                 # Phase 1 artifacts
│   │   ├── _synthesis.md             # Consolidated phase output
│   │   ├── _conflicts.json           # Detected conflicts
│   │   ├── ceo-stakeholder.md        # Agent-specific output
│   │   ├── business-analyst.md
│   │   ├── research-scientist.md
│   │   └── ux-researcher.md
│   ├── design/                       # Phase 2 artifacts
│   │   ├── _synthesis.md
│   │   ├── _conflicts.json
│   │   ├── software-architect.md
│   │   ├── data-scientist.md
│   │   ├── network-engineer.md
│   │   └── frontend-architect.md
│   ├── implementation/               # Phase 3 artifacts
│   │   ├── _synthesis.md
│   │   ├── _conflicts.json
│   │   ├── staff-engineer.md
│   │   ├── senior-engineer.md
│   │   ├── junior-engineer.md
│   │   └── devops-engineer.md
│   ├── quality/                      # Phase 4 artifacts
│   │   ├── _synthesis.md
│   │   ├── _conflicts.json
│   │   ├── qa-automation.md
│   │   ├── code-reviewer.md
│   │   └── performance-engineer.md
│   ├── release/                      # Phase 5 artifacts
│   │   ├── _synthesis.md
│   │   ├── cicd-engineer.md
│   │   ├── canary-user.md
│   │   └── documentation-engineer.md
│   ├── checkpoints/                  # Rollback snapshots
│   │   ├── cp_001_requirements_complete.tar.gz
│   │   ├── cp_002_design_complete.tar.gz
│   │   └── ...
│   └── history/                      # Version history
│       ├── requirements/
│       │   ├── v1/
│       │   └── v2/
│       └── design/
│           └── v1/
```

### 1.2 Phase Directories

Each SDLC phase has a dedicated directory containing:

| File Pattern | Purpose |
|--------------|---------|
| `_synthesis.md` | Consolidated output from synthesis agent (orchestrator reads this) |
| `_conflicts.json` | Detected conflicts between agent outputs |
| `_metadata.json` | Phase execution metadata |
| `{agent-name}.md` | Individual agent output |
| `{agent-name}.meta.json` | Agent execution metadata |

### 1.3 Directory Permissions

```python
ARTIFACT_PERMISSIONS = {
    "artifacts/": 0o755,           # Read access for all agents
    "artifacts/{sprint_id}/": 0o755,
    "artifacts/{sprint_id}/{phase}/": 0o755,
    "artifacts/{sprint_id}/checkpoints/": 0o700,  # Restricted to orchestrator
}
```

---

## 2. Naming Conventions

### 2.1 File Naming Rules

| Component | Convention | Example |
|-----------|------------|---------|
| Sprint ID | UUID (lowercase, hyphens) | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| Phase | Lowercase, singular | `requirements`, `design`, `implementation` |
| Agent | Kebab-case, matches plugin ID | `ceo-stakeholder`, `software-architect` |
| Version | `v{n}` prefix | `v1`, `v2` |
| Checkpoint | `cp_{sequence}_{label}` | `cp_001_requirements_complete` |

### 2.2 Artifact File Names

```
{agent-name}.md           # Primary output
{agent-name}.meta.json    # Execution metadata
_synthesis.md             # Underscore prefix = system-generated
_conflicts.json           # Underscore prefix = system-generated
_metadata.json            # Underscore prefix = system-generated
```

### 2.3 Path Construction

```python
def get_artifact_path(
    sprint_id: UUID,
    phase: str,
    agent: str | None = None,
    artifact_type: str = "output"
) -> Path:
    """Construct artifact path following naming conventions.

    Args:
        sprint_id: Sprint UUID
        phase: SDLC phase name
        agent: Agent name (None for phase-level artifacts)
        artifact_type: "output" | "metadata" | "synthesis" | "conflicts"

    Returns:
        Path to artifact file
    """
    base = ARTIFACTS_DIR / str(sprint_id) / phase

    if artifact_type == "synthesis":
        return base / "_synthesis.md"
    elif artifact_type == "conflicts":
        return base / "_conflicts.json"
    elif artifact_type == "metadata":
        if agent:
            return base / f"{agent}.meta.json"
        return base / "_metadata.json"
    else:  # output
        if not agent:
            raise ValueError("Agent required for output artifacts")
        return base / f"{agent}.md"
```

---

## 3. Artifact Schema

### 3.1 Agent Output Schema (Markdown)

Every agent artifact MUST follow this structure:

```markdown
---
artifact_type: agent_output
agent: {agent-name}
phase: {phase-name}
sprint_id: {sprint-id}
version: 1
created_at: {ISO-8601 timestamp}
model: {model-name}
trace_id: {logfire-trace-id}
confidence: {0.0-1.0}
status: completed | failed | partial
---

# {Agent Role}: {Task Title}

## Objective
{Clear statement of what this agent was tasked to do}

## Output

### {Section 1 Title}
{Content relevant to this agent's role}

### {Section 2 Title}
{Content relevant to this agent's role}

## Recommendations
{Bulleted list of actionable recommendations}

## Handoff Notes
{Information the next phase needs to know}

## Gaps & Uncertainties
{Areas requiring clarification or follow-up}

## References
{Sources cited, files read, tools used}
```

### 3.2 Agent Metadata Schema (JSON)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["agent", "phase", "sprint_id", "execution"],
  "properties": {
    "agent": {
      "type": "string",
      "description": "Agent identifier (kebab-case)"
    },
    "phase": {
      "type": "string",
      "enum": ["requirements", "design", "implementation", "quality", "release"]
    },
    "sprint_id": {
      "type": "string",
      "format": "uuid"
    },
    "version": {
      "type": "integer",
      "minimum": 1,
      "default": 1
    },
    "execution": {
      "type": "object",
      "required": ["started_at", "status"],
      "properties": {
        "started_at": { "type": "string", "format": "date-time" },
        "completed_at": { "type": "string", "format": "date-time" },
        "duration_ms": { "type": "integer" },
        "status": {
          "type": "string",
          "enum": ["pending", "running", "completed", "failed", "skipped"]
        },
        "model": { "type": "string" },
        "model_config": { "type": "object" },
        "tokens_used": {
          "type": "object",
          "properties": {
            "input": { "type": "integer" },
            "output": { "type": "integer" },
            "thinking": { "type": "integer" }
          }
        },
        "retry_count": { "type": "integer", "default": 0 },
        "error": { "type": "string" }
      }
    },
    "observability": {
      "type": "object",
      "properties": {
        "trace_id": { "type": "string" },
        "trace_url": { "type": "string", "format": "uri" },
        "span_id": { "type": "string" },
        "parent_span_id": { "type": "string" }
      }
    },
    "input": {
      "type": "object",
      "description": "Input artifacts and parameters for this agent"
    },
    "output": {
      "type": "object",
      "properties": {
        "artifact_path": { "type": "string" },
        "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
        "key_findings": { "type": "array", "items": { "type": "string" } },
        "recommendations": { "type": "array", "items": { "type": "string" } },
        "gaps": { "type": "array", "items": { "type": "string" } }
      }
    },
    "evaluation": {
      "type": "object",
      "description": "Evaluator scores if applicable",
      "properties": {
        "pass": { "type": "boolean" },
        "score": { "type": "number", "minimum": 0, "maximum": 1 },
        "feedback": { "type": "string" },
        "criteria_scores": {
          "type": "object",
          "additionalProperties": { "type": "number" }
        }
      }
    }
  }
}
```

### 3.3 Synthesis Artifact Schema (Markdown)

```markdown
---
artifact_type: synthesis
phase: {phase-name}
sprint_id: {sprint-id}
version: 1
created_at: {ISO-8601 timestamp}
synthesized_from: [{agent-1}, {agent-2}, ...]
conflict_count: {number}
status: completed | partial
---

# {Phase} Synthesis

## Executive Summary
{1-2 paragraph summary of consolidated findings}

## Agent Contributions

### {Agent 1}
**Key Findings:**
- {Finding 1}
- {Finding 2}

**Confidence:** {0.0-1.0}

### {Agent 2}
**Key Findings:**
- {Finding 1}
- {Finding 2}

**Confidence:** {0.0-1.0}

## Conflict Resolution

### Conflict 1: {Description}
- **Agents Involved:** {agent-1}, {agent-2}
- **Resolution:** {How conflict was resolved}
- **Rationale:** {Why this resolution was chosen}

## Consolidated Recommendations
{Prioritized list combining all agent recommendations}

1. **{Priority 1}** - {Description}
2. **{Priority 2}** - {Description}

## Gaps Requiring Follow-up
{Combined gaps from all agents}

- [ ] {Gap 1} - Suggested owner: {role}
- [ ] {Gap 2} - Suggested owner: {role}

## Handoff to {Next Phase}

### Required Inputs
{What the next phase needs from this synthesis}

### Constraints
{Constraints or decisions that must be honored}

### Open Questions
{Questions for the next phase to address}

## Gate Status

| Gate | Status | Details |
|------|--------|---------|
| {gate-1} | PASS/FAIL | {details} |
| {gate-2} | PASS/FAIL | {details} |
```

### 3.4 Conflicts Schema (JSON)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["phase", "sprint_id", "conflicts", "resolution_status"],
  "properties": {
    "phase": { "type": "string" },
    "sprint_id": { "type": "string", "format": "uuid" },
    "detected_at": { "type": "string", "format": "date-time" },
    "resolution_status": {
      "type": "string",
      "enum": ["unresolved", "auto_resolved", "manually_resolved"]
    },
    "conflicts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "type", "agents", "description", "severity"],
        "properties": {
          "id": { "type": "string" },
          "type": {
            "type": "string",
            "enum": [
              "technology_mismatch",
              "requirement_conflict",
              "timeline_conflict",
              "scope_disagreement",
              "priority_conflict",
              "approach_divergence"
            ]
          },
          "agents": {
            "type": "array",
            "items": { "type": "string" },
            "minItems": 2
          },
          "description": { "type": "string" },
          "severity": {
            "type": "string",
            "enum": ["critical", "major", "minor"]
          },
          "details": {
            "type": "object",
            "properties": {
              "agent_positions": {
                "type": "object",
                "additionalProperties": { "type": "string" }
              }
            }
          },
          "resolution": {
            "type": "object",
            "properties": {
              "strategy": {
                "type": "string",
                "enum": ["favor_majority", "favor_senior", "merge", "escalate", "defer"]
              },
              "decision": { "type": "string" },
              "rationale": { "type": "string" },
              "resolved_by": { "type": "string" },
              "resolved_at": { "type": "string", "format": "date-time" }
            }
          }
        }
      }
    }
  }
}
```

---

## 4. Synthesis Agent Design

### 4.1 Overview

The Synthesis Agent (`sdlc-orchestration:synthesis`) runs after each parallel phase to:
1. Collect all agent outputs from the phase
2. Detect conflicts between outputs
3. Create a unified artifact for the orchestrator
4. Flag gaps requiring additional research

### 4.2 Agent Specification

```yaml
name: synthesis
description: |
  Consolidates parallel agent outputs into unified phase artifacts.
  Detects conflicts, resolves where possible, and creates handoff summaries.
model: sonnet  # Needs reasoning but not creative
phase: all (runs after each phase completes)
tool_restrictions:
  allowed_tools:
    - Read
    - Write
    - Glob
  disallowed_tools:
    - Bash
    - WebSearch
    - WebFetch
    - Edit
```

### 4.3 Synthesis Agent Prompt Template

```markdown
---
name: synthesis-agent
description: Consolidate parallel agent outputs into unified phase artifact
---

# Synthesis Agent

You are a Synthesis Agent responsible for consolidating outputs from parallel agents
into a unified artifact for the next SDLC phase.

## Objective
Consolidate outputs from {agent_count} agents in the {phase} phase into a single,
actionable synthesis artifact.

## Input Artifacts
Read the following agent outputs:
{artifact_paths}

## Output Format
Write your synthesis to: `artifacts/{sprint_id}/{phase}/_synthesis.md`
Write detected conflicts to: `artifacts/{sprint_id}/{phase}/_conflicts.json`

## Synthesis Process

### 1. Extract Key Information
For each agent output:
- Identify key findings
- Extract recommendations
- Note confidence levels
- Catalog gaps/uncertainties

### 2. Detect Conflicts
Compare agent outputs for:
- Technology/approach disagreements
- Requirement interpretation differences
- Priority misalignments
- Scope disagreements

### 3. Resolve Conflicts
Apply resolution strategy:
- **Favor Majority:** If 2+ agents agree
- **Favor Senior:** Architect > Engineer for design decisions
- **Merge:** Combine non-conflicting elements
- **Escalate:** Flag for human review if critical

### 4. Create Unified Artifact
Produce a synthesis that:
- Summarizes all agent contributions
- Resolves or documents conflicts
- Provides consolidated recommendations
- Prepares handoff for next phase

## Boundaries
- DO NOT add new ideas not present in agent outputs
- DO NOT override critical conflicts without flagging
- DO NOT proceed if >50% of agents failed
- MUST flag gaps for next phase attention

## Quality Gates
Verify before completing:
- [ ] All agent outputs processed
- [ ] Conflicts identified and documented
- [ ] Synthesis follows schema
- [ ] Handoff notes complete
```

### 4.4 Synthesis Algorithm

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
import json

class ConflictSeverity(Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"

class ResolutionStrategy(Enum):
    FAVOR_MAJORITY = "favor_majority"
    FAVOR_SENIOR = "favor_senior"
    MERGE = "merge"
    ESCALATE = "escalate"
    DEFER = "defer"

@dataclass
class AgentOutput:
    agent: str
    content: str
    metadata: dict[str, Any]
    confidence: float
    key_findings: list[str]
    recommendations: list[str]
    gaps: list[str]

@dataclass
class Conflict:
    id: str
    type: str
    agents: list[str]
    description: str
    severity: ConflictSeverity
    agent_positions: dict[str, str]
    resolution: dict[str, Any] | None = None

class SynthesisAgent:
    """Consolidates parallel agent outputs into unified phase artifacts."""

    AGENT_SENIORITY = {
        "ceo-stakeholder": 5,
        "software-architect": 4,
        "staff-engineer": 4,
        "senior-engineer": 3,
        "data-scientist": 3,
        "research-scientist": 3,
        "business-analyst": 2,
        "junior-engineer": 1,
    }

    def __init__(self, sprint_id: str, phase: str, artifacts_dir: Path):
        self.sprint_id = sprint_id
        self.phase = phase
        self.artifacts_dir = artifacts_dir
        self.phase_dir = artifacts_dir / sprint_id / phase

    async def synthesize(self) -> tuple[str, list[Conflict]]:
        """Run synthesis pipeline.

        Returns:
            Tuple of (synthesis_markdown, detected_conflicts)
        """
        # 1. Load agent outputs
        outputs = await self._load_agent_outputs()

        if len(outputs) == 0:
            raise ValueError(f"No agent outputs found for {self.phase}")

        # 2. Detect conflicts
        conflicts = await self._detect_conflicts(outputs)

        # 3. Resolve conflicts
        resolved_conflicts = await self._resolve_conflicts(conflicts, outputs)

        # 4. Generate synthesis
        synthesis = await self._generate_synthesis(outputs, resolved_conflicts)

        # 5. Write artifacts
        await self._write_synthesis(synthesis)
        await self._write_conflicts(resolved_conflicts)

        return synthesis, resolved_conflicts

    async def _load_agent_outputs(self) -> list[AgentOutput]:
        """Load all agent outputs from phase directory."""
        outputs = []

        for artifact_file in self.phase_dir.glob("*.md"):
            if artifact_file.name.startswith("_"):
                continue  # Skip system files

            agent_name = artifact_file.stem
            content = artifact_file.read_text()

            # Load metadata if exists
            meta_file = self.phase_dir / f"{agent_name}.meta.json"
            metadata = json.loads(meta_file.read_text()) if meta_file.exists() else {}

            outputs.append(AgentOutput(
                agent=agent_name,
                content=content,
                metadata=metadata,
                confidence=metadata.get("output", {}).get("confidence", 0.5),
                key_findings=metadata.get("output", {}).get("key_findings", []),
                recommendations=metadata.get("output", {}).get("recommendations", []),
                gaps=metadata.get("output", {}).get("gaps", []),
            ))

        return outputs

    async def _detect_conflicts(self, outputs: list[AgentOutput]) -> list[Conflict]:
        """Detect conflicts between agent outputs."""
        conflicts = []
        conflict_id = 0

        # Compare each pair of outputs
        for i, output_a in enumerate(outputs):
            for output_b in outputs[i + 1:]:
                # Technology conflict detection
                tech_conflicts = self._detect_tech_conflicts(output_a, output_b)
                for tc in tech_conflicts:
                    tc.id = f"conflict_{conflict_id:03d}"
                    conflict_id += 1
                    conflicts.append(tc)

                # Approach divergence detection
                approach_conflicts = self._detect_approach_conflicts(output_a, output_b)
                for ac in approach_conflicts:
                    ac.id = f"conflict_{conflict_id:03d}"
                    conflict_id += 1
                    conflicts.append(ac)

        return conflicts

    async def _resolve_conflicts(
        self,
        conflicts: list[Conflict],
        outputs: list[AgentOutput]
    ) -> list[Conflict]:
        """Apply resolution strategies to conflicts."""
        output_map = {o.agent: o for o in outputs}

        for conflict in conflicts:
            if conflict.severity == ConflictSeverity.CRITICAL:
                # Escalate critical conflicts
                conflict.resolution = {
                    "strategy": ResolutionStrategy.ESCALATE.value,
                    "decision": "Requires human review",
                    "rationale": "Critical severity conflicts must be manually resolved",
                }
            else:
                # Try auto-resolution
                conflict.resolution = self._auto_resolve(conflict, output_map)

        return conflicts

    def _auto_resolve(
        self,
        conflict: Conflict,
        output_map: dict[str, AgentOutput]
    ) -> dict[str, Any]:
        """Attempt automatic conflict resolution."""
        agents = conflict.agents

        # Strategy 1: Favor higher seniority
        seniority_scores = [
            (agent, self.AGENT_SENIORITY.get(agent, 0))
            for agent in agents
        ]
        seniority_scores.sort(key=lambda x: x[1], reverse=True)

        if seniority_scores[0][1] > seniority_scores[1][1]:
            winner = seniority_scores[0][0]
            return {
                "strategy": ResolutionStrategy.FAVOR_SENIOR.value,
                "decision": conflict.agent_positions.get(winner, ""),
                "rationale": f"Favoring {winner} due to higher seniority for this decision type",
            }

        # Strategy 2: Favor higher confidence
        confidence_scores = [
            (agent, output_map[agent].confidence)
            for agent in agents
            if agent in output_map
        ]
        confidence_scores.sort(key=lambda x: x[1], reverse=True)

        if confidence_scores and confidence_scores[0][1] > 0.7:
            winner = confidence_scores[0][0]
            return {
                "strategy": "favor_confidence",
                "decision": conflict.agent_positions.get(winner, ""),
                "rationale": f"Favoring {winner} due to higher confidence ({confidence_scores[0][1]:.2f})",
            }

        # Default: Defer to next phase
        return {
            "strategy": ResolutionStrategy.DEFER.value,
            "decision": "Deferred to next phase for additional context",
            "rationale": "Unable to auto-resolve with available information",
        }

    def _detect_tech_conflicts(
        self,
        output_a: AgentOutput,
        output_b: AgentOutput
    ) -> list[Conflict]:
        """Detect technology/framework conflicts."""
        # Simplified implementation - real version would use NLP/LLM
        conflicts = []

        # Example: Check for database technology conflicts
        postgres_a = "postgres" in output_a.content.lower()
        mysql_a = "mysql" in output_a.content.lower()
        postgres_b = "postgres" in output_b.content.lower()
        mysql_b = "mysql" in output_b.content.lower()

        if (postgres_a and mysql_b) or (mysql_a and postgres_b):
            conflicts.append(Conflict(
                id="",
                type="technology_mismatch",
                agents=[output_a.agent, output_b.agent],
                description="Database technology disagreement",
                severity=ConflictSeverity.MAJOR,
                agent_positions={
                    output_a.agent: "PostgreSQL" if postgres_a else "MySQL",
                    output_b.agent: "PostgreSQL" if postgres_b else "MySQL",
                },
            ))

        return conflicts

    def _detect_approach_conflicts(
        self,
        output_a: AgentOutput,
        output_b: AgentOutput
    ) -> list[Conflict]:
        """Detect approach/methodology conflicts."""
        # Placeholder - implement with LLM-based semantic comparison
        return []

    async def _generate_synthesis(
        self,
        outputs: list[AgentOutput],
        conflicts: list[Conflict]
    ) -> str:
        """Generate synthesis markdown."""
        # Build synthesis document
        lines = [
            "---",
            "artifact_type: synthesis",
            f"phase: {self.phase}",
            f"sprint_id: {self.sprint_id}",
            "version: 1",
            f"created_at: {datetime.now(timezone.utc).isoformat()}",
            f"synthesized_from: [{', '.join(o.agent for o in outputs)}]",
            f"conflict_count: {len(conflicts)}",
            "status: completed",
            "---",
            "",
            f"# {self.phase.title()} Synthesis",
            "",
            "## Executive Summary",
            "",
            self._generate_executive_summary(outputs, conflicts),
            "",
            "## Agent Contributions",
            "",
        ]

        for output in outputs:
            lines.extend([
                f"### {output.agent}",
                f"**Key Findings:**",
            ])
            for finding in output.key_findings[:5]:
                lines.append(f"- {finding}")
            lines.append(f"\n**Confidence:** {output.confidence:.2f}")
            lines.append("")

        if conflicts:
            lines.extend([
                "## Conflict Resolution",
                "",
            ])
            for i, conflict in enumerate(conflicts, 1):
                lines.extend([
                    f"### Conflict {i}: {conflict.description}",
                    f"- **Agents Involved:** {', '.join(conflict.agents)}",
                    f"- **Severity:** {conflict.severity.value}",
                    f"- **Resolution:** {conflict.resolution.get('decision', 'Pending') if conflict.resolution else 'Pending'}",
                    f"- **Rationale:** {conflict.resolution.get('rationale', '') if conflict.resolution else ''}",
                    "",
                ])

        lines.extend([
            "## Consolidated Recommendations",
            "",
        ])

        all_recommendations = []
        for output in outputs:
            all_recommendations.extend(output.recommendations)

        for i, rec in enumerate(all_recommendations[:10], 1):
            lines.append(f"{i}. {rec}")

        lines.extend([
            "",
            "## Gaps Requiring Follow-up",
            "",
        ])

        all_gaps = []
        for output in outputs:
            all_gaps.extend(output.gaps)

        for gap in all_gaps[:10]:
            lines.append(f"- [ ] {gap}")

        return "\n".join(lines)

    def _generate_executive_summary(
        self,
        outputs: list[AgentOutput],
        conflicts: list[Conflict]
    ) -> str:
        """Generate executive summary paragraph."""
        total_findings = sum(len(o.key_findings) for o in outputs)
        total_recommendations = sum(len(o.recommendations) for o in outputs)
        avg_confidence = sum(o.confidence for o in outputs) / len(outputs)
        critical_conflicts = len([c for c in conflicts if c.severity == ConflictSeverity.CRITICAL])

        return (
            f"This synthesis consolidates outputs from {len(outputs)} agents in the {self.phase} phase. "
            f"A total of {total_findings} key findings and {total_recommendations} recommendations were identified. "
            f"Average agent confidence is {avg_confidence:.2f}. "
            f"{len(conflicts)} conflicts were detected ({critical_conflicts} critical). "
        )

    async def _write_synthesis(self, content: str) -> None:
        """Write synthesis artifact to disk."""
        synthesis_path = self.phase_dir / "_synthesis.md"
        synthesis_path.parent.mkdir(parents=True, exist_ok=True)
        synthesis_path.write_text(content)

    async def _write_conflicts(self, conflicts: list[Conflict]) -> None:
        """Write conflicts JSON to disk."""
        conflicts_path = self.phase_dir / "_conflicts.json"

        conflicts_data = {
            "phase": self.phase,
            "sprint_id": self.sprint_id,
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "resolution_status": self._get_resolution_status(conflicts),
            "conflicts": [
                {
                    "id": c.id,
                    "type": c.type,
                    "agents": c.agents,
                    "description": c.description,
                    "severity": c.severity.value,
                    "details": {"agent_positions": c.agent_positions},
                    "resolution": c.resolution,
                }
                for c in conflicts
            ],
        }

        conflicts_path.write_text(json.dumps(conflicts_data, indent=2))

    def _get_resolution_status(self, conflicts: list[Conflict]) -> str:
        """Determine overall resolution status."""
        if not conflicts:
            return "no_conflicts"

        unresolved = [c for c in conflicts if not c.resolution or c.resolution.get("strategy") == "escalate"]

        if len(unresolved) == 0:
            return "auto_resolved"
        elif len(unresolved) < len(conflicts):
            return "partially_resolved"
        else:
            return "unresolved"
```

### 4.5 Synthesis Integration Points

```
                                      +------------------+
                                      |   Orchestrator   |
                                      +--------+---------+
                                               |
                     +-------------------------+-------------------------+
                     |                         |                         |
              +------+------+          +-------+-------+          +------+------+
              |   Agent 1   |          |   Agent 2     |          |   Agent 3   |
              +------+------+          +-------+-------+          +------+------+
                     |                         |                         |
                     v                         v                         v
              +------+------+          +-------+-------+          +------+------+
              |  agent1.md  |          |  agent2.md    |          |  agent3.md  |
              +------+------+          +-------+-------+          +------+------+
                     |                         |                         |
                     +------------+------------+------------+------------+
                                  |                         |
                                  v                         v
                          +-------+-------+         +-------+-------+
                          | Synthesis     |         | Conflict      |
                          | Agent         |-------->| Detection     |
                          +-------+-------+         +-------+-------+
                                  |                         |
                                  v                         v
                          +-------+-------+         +-------+-------+
                          | _synthesis.md |         | _conflicts.json|
                          +-------+-------+         +-------+-------+
                                  |
                                  v
                          +-------+-------+
                          | Orchestrator  |
                          | (reads only   |
                          |  synthesis)   |
                          +---------------+
```

---

## 5. PhaseRunner Integration

### 5.1 Updated PhaseRunner Architecture

```python
from pathlib import Path
from uuid import UUID

from app.services.artifact_manager import ArtifactManager
from app.agents.synthesis_agent import SynthesisAgent

class PhaseRunner:
    """Orchestrates SDLC phases with artifact management."""

    def __init__(
        self,
        sprint_id: UUID,
        artifacts_dir: Path | None = None
    ):
        self.sprint_id = sprint_id
        self.artifact_manager = ArtifactManager(
            sprint_id=sprint_id,
            artifacts_dir=artifacts_dir or settings.ARTIFACTS_DIR
        )

    async def execute_phase(
        self,
        phase: str,
        feature: str,
        agents: list[str] | None = None
    ) -> PhaseResult:
        """Execute a single SDLC phase.

        Args:
            phase: Phase name
            feature: Feature description
            agents: Override default agents for phase

        Returns:
            PhaseResult with synthesis and status
        """
        # 1. Initialize phase artifacts
        await self.artifact_manager.init_phase(phase)

        # 2. Read previous phase synthesis (if not requirements)
        previous_context = None
        if phase != "requirements":
            previous_phase = self._get_previous_phase(phase)
            previous_context = await self.artifact_manager.read_synthesis(previous_phase)

        # 3. Execute parallel agents
        phase_agents = agents or PHASE_AGENTS[phase]
        agent_results = await self._execute_parallel_agents(
            phase=phase,
            agents=phase_agents,
            feature=feature,
            context=previous_context
        )

        # 4. Write agent artifacts
        for agent, result in agent_results.items():
            await self.artifact_manager.write_agent_artifact(
                phase=phase,
                agent=agent,
                content=result.content,
                metadata=result.metadata
            )

        # 5. Run synthesis
        synthesis_agent = SynthesisAgent(
            sprint_id=str(self.sprint_id),
            phase=phase,
            artifacts_dir=self.artifact_manager.artifacts_dir
        )
        synthesis, conflicts = await synthesis_agent.synthesize()

        # 6. Validate phase gates
        gates_passed = await self._validate_phase_gates(phase, synthesis, conflicts)

        # 7. Create checkpoint if gates passed
        if all(gates_passed.values()):
            await self.artifact_manager.create_checkpoint(
                phase=phase,
                label=f"{phase}_complete"
            )

        return PhaseResult(
            phase=phase,
            synthesis=synthesis,
            conflicts=conflicts,
            gates_passed=gates_passed,
            can_proceed=all(gates_passed.values())
        )
```

### 5.2 ArtifactManager Service

```python
class ArtifactManager:
    """Manages artifact lifecycle for SDLC phases."""

    VERSION = "1.0.0"

    def __init__(self, sprint_id: UUID, artifacts_dir: Path):
        self.sprint_id = sprint_id
        self.artifacts_dir = artifacts_dir
        self.base_dir = artifacts_dir / str(sprint_id)

    async def init_phase(self, phase: str) -> None:
        """Initialize directory structure for a phase."""
        phase_dir = self.base_dir / phase
        phase_dir.mkdir(parents=True, exist_ok=True)

        # Write phase metadata
        metadata = {
            "phase": phase,
            "sprint_id": str(self.sprint_id),
            "initialized_at": datetime.now(timezone.utc).isoformat(),
            "version": self.VERSION,
            "status": "initialized"
        }

        meta_path = phase_dir / "_metadata.json"
        meta_path.write_text(json.dumps(metadata, indent=2))

    async def write_agent_artifact(
        self,
        phase: str,
        agent: str,
        content: str,
        metadata: dict[str, Any]
    ) -> Path:
        """Write agent output artifact.

        Args:
            phase: Phase name
            agent: Agent identifier
            content: Markdown content
            metadata: Agent execution metadata

        Returns:
            Path to written artifact
        """
        phase_dir = self.base_dir / phase

        # Write content
        artifact_path = phase_dir / f"{agent}.md"
        artifact_path.write_text(content)

        # Write metadata
        meta_path = phase_dir / f"{agent}.meta.json"
        meta_path.write_text(json.dumps(metadata, indent=2))

        return artifact_path

    async def read_synthesis(self, phase: str) -> str | None:
        """Read phase synthesis artifact.

        Args:
            phase: Phase name

        Returns:
            Synthesis content or None if not found
        """
        synthesis_path = self.base_dir / phase / "_synthesis.md"

        if synthesis_path.exists():
            return synthesis_path.read_text()
        return None

    async def read_agent_artifact(self, phase: str, agent: str) -> tuple[str, dict] | None:
        """Read agent artifact and metadata.

        Args:
            phase: Phase name
            agent: Agent identifier

        Returns:
            Tuple of (content, metadata) or None
        """
        artifact_path = self.base_dir / phase / f"{agent}.md"
        meta_path = self.base_dir / phase / f"{agent}.meta.json"

        if not artifact_path.exists():
            return None

        content = artifact_path.read_text()
        metadata = json.loads(meta_path.read_text()) if meta_path.exists() else {}

        return content, metadata

    async def create_checkpoint(self, phase: str, label: str) -> str:
        """Create a rollback checkpoint.

        Args:
            phase: Phase that completed
            label: Checkpoint label

        Returns:
            Checkpoint ID
        """
        checkpoints_dir = self.base_dir / "checkpoints"
        checkpoints_dir.mkdir(parents=True, exist_ok=True)

        # Get next checkpoint number
        existing = list(checkpoints_dir.glob("cp_*.tar.gz"))
        checkpoint_num = len(existing) + 1
        checkpoint_id = f"cp_{checkpoint_num:03d}_{label}"

        # Create tarball of phase directory
        import tarfile
        checkpoint_path = checkpoints_dir / f"{checkpoint_id}.tar.gz"

        with tarfile.open(checkpoint_path, "w:gz") as tar:
            phase_dir = self.base_dir / phase
            tar.add(phase_dir, arcname=phase)

        # Write checkpoint metadata
        checkpoint_meta = {
            "checkpoint_id": checkpoint_id,
            "phase": phase,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sprint_id": str(self.sprint_id),
            "archive_path": str(checkpoint_path),
            "files_included": [
                str(f.relative_to(self.base_dir))
                for f in (self.base_dir / phase).rglob("*")
                if f.is_file()
            ]
        }

        meta_path = checkpoints_dir / f"{checkpoint_id}.meta.json"
        meta_path.write_text(json.dumps(checkpoint_meta, indent=2))

        return checkpoint_id

    async def rollback_to_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore artifacts from a checkpoint.

        Args:
            checkpoint_id: Checkpoint to restore

        Returns:
            True if successful
        """
        checkpoints_dir = self.base_dir / "checkpoints"
        checkpoint_path = checkpoints_dir / f"{checkpoint_id}.tar.gz"
        meta_path = checkpoints_dir / f"{checkpoint_id}.meta.json"

        if not checkpoint_path.exists():
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        # Read metadata
        metadata = json.loads(meta_path.read_text())
        phase = metadata["phase"]

        # Archive current state to history
        history_dir = self.base_dir / "history" / phase
        history_dir.mkdir(parents=True, exist_ok=True)

        existing_versions = list(history_dir.glob("v*"))
        next_version = f"v{len(existing_versions) + 1}"

        current_phase_dir = self.base_dir / phase
        if current_phase_dir.exists():
            import shutil
            shutil.move(str(current_phase_dir), str(history_dir / next_version))

        # Extract checkpoint
        import tarfile
        with tarfile.open(checkpoint_path, "r:gz") as tar:
            tar.extractall(self.base_dir)

        return True

    async def list_checkpoints(self) -> list[dict[str, Any]]:
        """List available checkpoints.

        Returns:
            List of checkpoint metadata
        """
        checkpoints_dir = self.base_dir / "checkpoints"

        if not checkpoints_dir.exists():
            return []

        checkpoints = []
        for meta_path in sorted(checkpoints_dir.glob("cp_*.meta.json")):
            metadata = json.loads(meta_path.read_text())
            checkpoints.append(metadata)

        return checkpoints
```

### 5.3 Phase Flow with Artifacts

```
+------------------+     +-------------------+     +------------------+
|                  |     |                   |     |                  |
|  Requirements    |---->|  Design           |---->|  Implementation  |
|  Phase           |     |  Phase            |     |  Phase           |
|                  |     |                   |     |                  |
+--------+---------+     +--------+----------+     +--------+---------+
         |                        |                         |
         v                        v                         v
+--------+---------+     +--------+----------+     +--------+---------+
| artifacts/       |     | artifacts/        |     | artifacts/       |
| {sprint}/        |     | {sprint}/         |     | {sprint}/        |
| requirements/    |     | design/           |     | implementation/  |
| _synthesis.md    |     | _synthesis.md     |     | _synthesis.md    |
+------------------+     +-------------------+     +------------------+
         |                        |                         |
         |    +------------------+|                         |
         +--->| Orchestrator     |<-------------------------+
              | reads synthesis  |
              | only (60-80%     |
              | token savings)   |
              +------------------+
```

---

## 6. Manifest Schema

### 6.1 Sprint Manifest

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Sprint Artifact Manifest",
  "type": "object",
  "required": ["version", "sprint_id", "created_at", "phases"],
  "properties": {
    "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "sprint_id": { "type": "string", "format": "uuid" },
    "spec_id": { "type": "string", "format": "uuid" },
    "created_at": { "type": "string", "format": "date-time" },
    "updated_at": { "type": "string", "format": "date-time" },
    "status": {
      "type": "string",
      "enum": ["planned", "active", "completed", "failed", "cancelled"]
    },
    "current_phase": { "type": "string" },
    "phases": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "status": { "type": "string" },
          "started_at": { "type": "string", "format": "date-time" },
          "completed_at": { "type": "string", "format": "date-time" },
          "checkpoint_id": { "type": "string" },
          "synthesis_path": { "type": "string" },
          "agent_count": { "type": "integer" },
          "conflict_count": { "type": "integer" }
        }
      }
    },
    "checkpoints": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "checkpoint_id": { "type": "string" },
          "phase": { "type": "string" },
          "created_at": { "type": "string", "format": "date-time" }
        }
      }
    },
    "observability": {
      "type": "object",
      "properties": {
        "logfire_project_url": { "type": "string", "format": "uri" },
        "total_tokens_used": { "type": "integer" },
        "total_duration_ms": { "type": "integer" }
      }
    }
  }
}
```

---

## 7. Token Efficiency Analysis

### 7.1 Before: Inline Outputs

```
Orchestrator Context Window:
+----------------------------------------------------------+
| System Prompt                              ~2,000 tokens  |
+----------------------------------------------------------+
| Agent 1 Full Output (requirements)        ~15,000 tokens  |
+----------------------------------------------------------+
| Agent 2 Full Output (requirements)        ~12,000 tokens  |
+----------------------------------------------------------+
| Agent 3 Full Output (requirements)        ~10,000 tokens  |
+----------------------------------------------------------+
| Previous Conversation History              ~5,000 tokens  |
+----------------------------------------------------------+
| Total:                                    ~44,000 tokens  |
+----------------------------------------------------------+
```

### 7.2 After: Synthesis-Only

```
Orchestrator Context Window:
+----------------------------------------------------------+
| System Prompt                              ~2,000 tokens  |
+----------------------------------------------------------+
| Requirements Synthesis (_synthesis.md)     ~3,000 tokens  |
+----------------------------------------------------------+
| Previous Conversation History              ~5,000 tokens  |
+----------------------------------------------------------+
| Total:                                    ~10,000 tokens  |
+----------------------------------------------------------+

Token Savings: 77% (34,000 tokens saved per phase)
```

### 7.3 Cost Impact

| Scenario | Tokens/Phase | 5 Phases | Cost (Opus @$15/1M) |
|----------|--------------|----------|---------------------|
| Before (inline) | 44,000 | 220,000 | $3.30 |
| After (synthesis) | 10,000 | 50,000 | $0.75 |
| **Savings** | 34,000 | 170,000 | **$2.55 (77%)** |

---

## 8. Rollback & Recovery

### 8.1 Rollback Scenarios

| Scenario | Action | Command |
|----------|--------|---------|
| Bad design decisions | Rollback to requirements checkpoint | `rollback_to_checkpoint("cp_001_requirements_complete")` |
| Failed implementation | Rollback to design checkpoint | `rollback_to_checkpoint("cp_002_design_complete")` |
| QA failures | Rollback to implementation checkpoint | `rollback_to_checkpoint("cp_003_implementation_complete")` |
| Full restart | Delete sprint artifacts, re-run | Manual or via API |

### 8.2 Rollback Safety

```python
async def safe_rollback(
    artifact_manager: ArtifactManager,
    checkpoint_id: str,
    confirm: bool = False
) -> dict[str, Any]:
    """Perform safe rollback with validation.

    Args:
        artifact_manager: Artifact manager instance
        checkpoint_id: Target checkpoint
        confirm: Must be True to proceed

    Returns:
        Rollback result with affected phases
    """
    if not confirm:
        # Return preview of what will be affected
        checkpoints = await artifact_manager.list_checkpoints()
        target_idx = next(
            (i for i, cp in enumerate(checkpoints) if cp["checkpoint_id"] == checkpoint_id),
            None
        )

        if target_idx is None:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        affected_phases = [
            cp["phase"] for cp in checkpoints[target_idx + 1:]
        ]

        return {
            "action": "preview",
            "checkpoint": checkpoint_id,
            "affected_phases": affected_phases,
            "warning": f"This will discard work from {len(affected_phases)} phase(s)",
            "confirm_required": True
        }

    # Perform actual rollback
    success = await artifact_manager.rollback_to_checkpoint(checkpoint_id)

    return {
        "action": "rollback",
        "checkpoint": checkpoint_id,
        "success": success,
        "message": f"Rolled back to {checkpoint_id}"
    }
```

---

## 9. API Extensions

### 9.1 New Endpoints

```python
# backend/app/api/routes/v1/artifacts.py

from fastapi import APIRouter, Depends, HTTPException
from app.services.artifact_manager import ArtifactManager

router = APIRouter(prefix="/sprints/{sprint_id}/artifacts", tags=["artifacts"])

@router.get("/")
async def list_artifacts(sprint_id: UUID) -> ArtifactListResponse:
    """List all artifacts for a sprint."""
    ...

@router.get("/phases/{phase}/synthesis")
async def get_phase_synthesis(sprint_id: UUID, phase: str) -> SynthesisResponse:
    """Get synthesis artifact for a phase."""
    ...

@router.get("/phases/{phase}/agents/{agent}")
async def get_agent_artifact(sprint_id: UUID, phase: str, agent: str) -> AgentArtifactResponse:
    """Get specific agent artifact."""
    ...

@router.get("/checkpoints")
async def list_checkpoints(sprint_id: UUID) -> CheckpointListResponse:
    """List available checkpoints."""
    ...

@router.post("/checkpoints/{checkpoint_id}/rollback")
async def rollback_checkpoint(
    sprint_id: UUID,
    checkpoint_id: str,
    confirm: bool = False
) -> RollbackResponse:
    """Rollback to a checkpoint."""
    ...

@router.get("/conflicts")
async def get_conflicts(sprint_id: UUID, phase: str | None = None) -> ConflictListResponse:
    """Get detected conflicts, optionally filtered by phase."""
    ...
```

### 9.2 Response Schemas

```python
# backend/app/schemas/artifacts.py

from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class ArtifactMetadata(BaseModel):
    agent: str
    phase: str
    created_at: datetime
    confidence: float | None
    status: str

class SynthesisResponse(BaseModel):
    phase: str
    sprint_id: UUID
    content: str
    conflict_count: int
    agent_count: int
    created_at: datetime

class AgentArtifactResponse(BaseModel):
    agent: str
    phase: str
    content: str
    metadata: dict

class CheckpointResponse(BaseModel):
    checkpoint_id: str
    phase: str
    created_at: datetime
    files_included: list[str]

class RollbackResponse(BaseModel):
    action: str
    checkpoint: str
    success: bool | None
    affected_phases: list[str] | None
    message: str
```

---

## 10. Implementation Checklist

### Phase 1: Core Infrastructure (Week 1)

- [ ] Create `ArtifactManager` service class
- [ ] Implement directory structure initialization
- [ ] Add artifact write/read methods
- [ ] Create checkpoint creation/restore logic
- [ ] Write unit tests for `ArtifactManager`

### Phase 2: Synthesis Agent (Week 1-2)

- [ ] Create synthesis agent prompt template
- [ ] Implement conflict detection algorithm
- [ ] Build resolution strategy logic
- [ ] Add synthesis generation
- [ ] Write integration tests

### Phase 3: PhaseRunner Integration (Week 2)

- [ ] Update `PhaseRunner` to use `ArtifactManager`
- [ ] Add synthesis step after parallel agents
- [ ] Implement phase gate validation
- [ ] Add checkpoint creation on phase completion
- [ ] Update WebSocket events for artifact status

### Phase 4: API & Frontend (Week 2-3)

- [ ] Create `/artifacts` API routes
- [ ] Add rollback endpoint with confirmation
- [ ] Build artifact viewer component
- [ ] Add rollback UI in sprint dashboard

### Phase 5: Validation & Rollout (Week 3)

- [ ] Run token usage benchmarks
- [ ] Test rollback scenarios
- [ ] Document edge cases
- [ ] Feature flag for gradual rollout

---

## 11. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Synthesis loses critical details | Medium | High | Include "key findings" in metadata for validation |
| Checkpoint disk usage grows | Low | Medium | Implement retention policy (keep last 10 checkpoints) |
| Conflict resolution errors | Medium | Medium | Always surface unresolved conflicts to orchestrator |
| File I/O latency | Low | Low | Use async I/O, consider caching hot artifacts |
| Schema version drift | Medium | Medium | Include version in all artifacts, add migration support |

---

## 12. Future Enhancements

1. **Semantic Conflict Detection** - Use embeddings to detect subtle conflicts
2. **Artifact Diffing** - Show what changed between versions
3. **Cross-Sprint Learning** - Aggregate insights across sprints
4. **Artifact Search** - Full-text search across all artifacts
5. **Export to Notion/Confluence** - Integration with external documentation

---

## Appendix A: Example Artifacts

### A.1 Agent Output Example

```markdown
---
artifact_type: agent_output
agent: software-architect
phase: design
sprint_id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
version: 1
created_at: 2026-01-22T10:30:00Z
model: claude-opus-4-5
trace_id: tr_abc123def456
confidence: 0.85
status: completed
---

# Software Architect: User Authentication System Design

## Objective
Design the system architecture for OAuth2-based user authentication with support for Google and GitHub social login providers.

## Output

### System Architecture

```
+-------------+     +----------------+     +------------------+
|   Frontend  |---->|  Auth Gateway  |---->|  Auth Service    |
|   (Next.js) |     |  (API Route)   |     |  (FastAPI)       |
+-------------+     +----------------+     +--------+---------+
                                                    |
                    +-------------------------------+
                    |                               |
           +--------v--------+            +--------v--------+
           |  User Store     |            |  Token Store    |
           |  (PostgreSQL)   |            |  (Redis)        |
           +-----------------+            +-----------------+
```

### API Contract

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/login` | POST | Initiate OAuth flow |
| `/auth/callback` | GET | OAuth callback handler |
| `/auth/refresh` | POST | Refresh access token |
| `/auth/logout` | POST | Invalidate session |

### Database Schema

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    oauth_provider VARCHAR(50) NOT NULL,
    oauth_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(oauth_provider, oauth_id)
);

CREATE TABLE oauth_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    access_token_hash VARCHAR(255) NOT NULL,
    refresh_token_hash VARCHAR(255),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Recommendations

1. Use JWT for stateless access tokens (15-minute expiry)
2. Store refresh tokens in Redis with 7-day TTL
3. Implement PKCE for OAuth flow security
4. Add rate limiting on auth endpoints (10 req/min)

## Handoff Notes

- Frontend team needs OAuth client IDs from DevOps
- Database migration must run before deployment
- Redis cluster required for token storage

## Gaps & Uncertainties

- MFA requirements not specified - recommend deferring to Phase 2
- Session management across multiple devices unclear

## References

- OAuth 2.0 RFC 6749
- PKCE RFC 7636
- Project: `conductor/tech-stack.md` (PostgreSQL, Redis confirmed)
```

### A.2 Synthesis Example

See Section 3.3 for full schema.

---

## Appendix B: Configuration

```python
# backend/app/core/config.py (additions)

class Settings(BaseSettings):
    # Artifact Management
    ARTIFACTS_DIR: Path = Path("./artifacts")
    ARTIFACT_VERSION: str = "1.0.0"
    CHECKPOINT_RETENTION_COUNT: int = 10
    MAX_ARTIFACT_SIZE_MB: int = 10

    # Synthesis Agent
    SYNTHESIS_MODEL: str = "claude-sonnet-4-5"
    SYNTHESIS_MAX_TOKENS: int = 8000
    CONFLICT_AUTO_RESOLVE_THRESHOLD: float = 0.7
```

---

## References

- [Phase 1 Requirements Summary](./docs/research/phase1-requirements-summary.md)
- [Orchestrator-Workers Pattern Research](./docs/design/research-orchestrator-workers-pattern.md)
- [SDLC Orchestration Plugin](../.claude/plugins/sdlc-orchestration/README.md)
- [Anthropic Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)
