# Spike: Chat Code Persistence & Execution

## Goal
Explore and design mechanisms to extract code generated in the chat (by the agent or user) and persist it to the filesystem so it can be:
1.  Compiled (if necessary).
2.  Executed (e.g., tests, scripts).
3.  Integrated into the project (e.g., new features).

## Context
The current agent can generate code snippets in the chat, but there is no direct "Apply" button or automatic persistence. We want to bridge this gap to enable true TDD and autonomous coding flows.

## Potential Approaches

### 1. Tool-Based Extraction (Active)
The agent explicitly calls a tool to write code.
*   **Mechanism:** Agent uses `write_to_file` (already exists for me, but maybe needs to be exposed to the internal `AssistantAgent`).
*   **Pros:** Explicit intent, control over file paths.
*   **Cons:** Model might hallucinate paths or misuse the tool.

### 2. Regex/Parser-Based Extraction (Passive)
A middleware or "sidecar" listens to the chat stream, identifies code blocks (e.g., ` ```python ... ``` `), and presents them as "Artifacts" that the user can approve to save.
*   **Mechanism:**
    *   Parse Markdown code blocks.
    *   Look for metadata headers (e.g., `### [FILE] path/to/file.py`).
    *   UI displays "Save to Disk" button.
*   **Pros:** Safe (user approval), works with any model.
*   **Cons:** Requires strict formatting conventions (e.g., "Always put the filename in a comment").

### 3. "Spec-to-Code" TDD Workflow (Agentic)
Specifically `agent_tdd.py` usage.
*   **Mechanism:**
    *   User provides a spec/prompt.
    *   Agent generates a candidate solution.
    *   System automatically saves candidate to a sandbox/temp dir.
    *   System runs tests against the candidate.
*   **Pros:** Automated verification.
*   **Cons:** Complex orchestration, sandboxing security.

## Proposed Experiment: The "Applier" Utility

We can create a specialized tool or command available in the chat loop (e.g., via `agent_browser` or a new `agent_fs` tool) that targets specific files.

### Strategy for this Branch
1.  **Expose `fs` tools to the Agent:** Ensure `AssistantAgent` has access to a safe subset of filesystem tools (`read_file`, `write_file`, `list_dir`).
2.  **Define a Convention:** Instruct the agent to structure code responses in a specific way (e.g., XML tags `<file path="...">... </file>`) to make extraction robust and unambiguous.
3.  **Implement a "Save" Action:** In the frontend or via a CLI command that parses the last message and applies changes.

## Security Considerations
*   **Path Traversal:** Prevent writing to `../` or `/etc/`.
*   **Overwrite Protection:** Require confirmation before overwriting existing files (or use a `.new` extension).
*   **Execution Safety:** Don't auto-run code; just auto-save. Execution should be a separate, explicit step.

## Tool Ecosystem Research

### PydanticAI Built-in Tools
*   **Status:** `pydantic-ai` is a **framework** for defining tools, not a library of pre-built tools.
*   **Verification:** Introspection of the library (`v1.44.0`) shows no standard tool modules (like `pydantic_ai.tools`).
*   **Implication:** We must build or wrap our own tools (as we did with `agent-browser` and `http_fetch`).

### Available External Tool Sources
Since we cannot import "standard" tools, we should look to these sources:

1.  **LangChain Community Tools:**
    *   Rich ecosystem (Wikipedia, DuckDuckGo, Shell, etc.).
    *   **Integration:** Can be wrapped easily. PydanticAI's `@agent.tool` can simply call `langchain_tool.run()`.
    *   [LangChain Tools Docs](https://python.langchain.com/docs/modules/agents/tools/)

2.  **Model Context Protocol (MCP):**
    *   Emerging standard for exposing tools to agents.
    *   **Relevance:** We already use `logfire-mcp` and `grafana-mcp`.
    *   **Potential:** Access local resources (Filesystem, Git) via MCP servers.
    *   [Model Context Protocol](https://modelcontextprotocol.io/introduction)

3.  **Vercel AI SDK / Agent Browser:**
    *   We currently use `agent-browser` (headless Chromium).
    *   Source: [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser)

### Recommended "FS" Tool Implementation
For this feature branch, implementing a **native Python tool** (Source #1 approach, but custom) is simplest and most secure.
*   **Path:** `backend/app/agents/tools/fs.py`
*   **Functions:** `read_file`, `write_file`, `list_dir`
*   **Security:** Strict path validation (must be within `WORKSPACE_ROOT`).
