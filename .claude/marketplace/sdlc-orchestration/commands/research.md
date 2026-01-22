---
name: research
description: |
  Execute parallel research phase with 3+ specialized agents.
  Demonstrates true parallelization for technical, business, and architectural research.
---

# Parallel Research Command

Execute a focused research sprint with multiple specialized agents working in parallel.

## Usage

```
/sdlc-orchestration:research "<research topic>"
```

---

## CRITICAL: Parallel Execution Pattern

**To achieve true parallelism, invoke ALL 3 Task tools in a SINGLE message.**

### Execution

```python
# Invoke these 3 Task tools in ONE message:
Task(subagent_type="sdlc-orchestration:research-scientist", prompt="Research technical approaches, algorithms, and implementation options for: {topic}")
Task(subagent_type="sdlc-orchestration:business-analyst", prompt="Research market context, user needs, and business requirements for: {topic}")
Task(subagent_type="sdlc-orchestration:software-architect", prompt="Research architectural patterns, technology choices, and integration approaches for: {topic}")
```

### Agents

| Agent | Focus | Outputs |
|-------|-------|---------|
| Research Scientist | Technical feasibility, algorithms, state of the art | Technical report, feasibility assessment |
| Business Analyst | User needs, market context, requirements | User stories, business context |
| Software Architect | Patterns, technologies, integration | Architecture options, technology recommendations |

---

## Workflow

### Step 1: Launch Parallel Agents

Invoke all 3 agents in ONE message:

1. **Research Scientist Agent** (`sdlc-orchestration:research-scientist`)
   - Investigate technical approaches
   - Evaluate algorithms and libraries
   - Assess implementation complexity

2. **Business Analyst Agent** (`sdlc-orchestration:business-analyst`)
   - Analyze user needs and pain points
   - Research market solutions
   - Document requirements

3. **Software Architect Agent** (`sdlc-orchestration:software-architect`)
   - Evaluate architectural patterns
   - Research technology stacks
   - Identify integration points

### Step 2: Aggregate Results

After all agents complete, create a consolidated research summary:

```markdown
# Research Summary: {topic}

## Technical Findings
[From Research Scientist]

## Business Context
[From Business Analyst]

## Architectural Recommendations
[From Software Architect]

## Synthesis
[Consolidated insights and recommendations]

## Next Steps
[Recommended actions based on findings]
```

### Step 3: Update State

Update phase state to completed:

```json
{
  "phase": "research",
  "status": "completed",
  "agents_completed": ["research-scientist", "business-analyst", "software-architect"],
  "artifacts": {
    "technical_report": "research-technical.md",
    "business_context": "research-business.md",
    "architecture_options": "research-architecture.md",
    "summary": "research-summary.md"
  }
}
```

---

## Example

```
User: /sdlc-orchestration:research "real-time collaborative editing like Google Docs"

Parallel Agents Launch:
├── Research Scientist → OT vs CRDT algorithms, Y.js, Automerge
├── Business Analyst → User needs, competitive analysis, requirements
└── Software Architect → WebSocket patterns, sync strategies, storage

Aggregated Output:
- Technical: CRDT recommended (Y.js), ~2 weeks implementation
- Business: Core need is latency <100ms, offline support desired
- Architecture: WebSocket + Redis pub/sub, Postgres for persistence

Synthesis: Use Y.js CRDT with WebSocket transport, Redis for presence
```

---

## Skill Discovery (REQUIRED)

**Before researching any technology, search the installed skills for relevant helpers.**

### Step 0: Search Skills Manifest

```bash
# Search for relevant skills in the manifest
grep -i "<keyword>" skills/ai-research-skills.manifest.json

# Or read the full manifest to find matching skills
cat skills/ai-research-skills.manifest.json | jq '.installed[] | select(.skill | test("<keyword>"; "i"))'
```

### Available Skill Categories (76 installed)

| Category | Skills | Use For |
|----------|--------|---------|
| `model-architecture` | litgpt, mamba, nanogpt, rwkv | Custom model implementation |
| `fine-tuning` | axolotl, llama-factory, peft, unsloth | Model fine-tuning |
| `inference-serving` | vllm, sglang, tensorrt-llm, llama-cpp | Model deployment |
| `agents` | autogpt, crewai, langchain, llamaindex | Agent frameworks |
| `rag` | chroma, faiss, pinecone, qdrant | Vector search/RAG |
| `optimization` | awq, bitsandbytes, flash-attention, gptq | Model optimization |
| `distributed-training` | accelerate, deepspeed, pytorch-fsdp | Large-scale training |
| `prompt-engineering` | dspy, guidance, instructor, outlines | Structured outputs |
| `observability` | langsmith, phoenix | LLM monitoring |
| `mlops` | mlflow, tensorboard, weights-and-biases | Experiment tracking |

### Skill Integration in Research

Each research agent MUST:

1. **Search skills first:**
   ```bash
   grep -i "<topic>" skills/ai-research-skills.manifest.json
   ```

2. **Read matching skill docs:**
   ```bash
   cat skills/ai-research-<category>-<skill>/SKILL.md
   ```

3. **Include skill recommendations in output:**
   ```markdown
   ## Recommended Skills
   - `ai-research-inference-serving-vllm` - For serving the model
   - `ai-research-rag-chroma` - For vector storage
   ```

---

## Integration with SDLC Phases

The research command is typically used:

1. **Before Requirements Phase** - To understand technical landscape
2. **During Design Phase** - To evaluate specific technologies
3. **Before Implementation** - To validate approach

Results feed into subsequent phase decisions.
