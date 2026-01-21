# Specification: Implement the Core "Sprint" Trigger and Agentic Loop

## Overview
This track focuses on the foundational mechanism of the Guilde Lite platform: the ability for a user to trigger a "sprint" (a software development task) and have an autonomous AI agent (using PydanticAI) execute the task through an iterative agentic loop.

## Functional Requirements
1. **Sprint Trigger API:** A POST endpoint `/api/v1/sprints` that accepts a task description.
2. **Agentic Loop:** An asynchronous background process initiated by the trigger.
3. **PydanticAI Integration:** Use PydanticAI to define an agent capable of basic code manipulation and validation.
4. **Real-time Status updates:** WebSocket notifications (via existing `/ws` infrastructure) to inform the frontend of the agent's progress (e.g., "Thinking", "Writing Code", "Running Tests", "Validated").
5. **Persistence:** Store the sprint status and final artifacts in the database.

## Technical Requirements
- **Backend:** FastAPI, PydanticAI, SQLAlchemy.
- **Real-time:** WebSockets for status streaming.
- **Workflow:** The agent must attempt to validate its own code before considering a task complete.

## Acceptance Criteria
- A user can send a POST request with a task.
- A background worker starts the agentic process.
- The frontend receives status updates via WebSockets.
- The process completes with a "Validated" state if successful.
