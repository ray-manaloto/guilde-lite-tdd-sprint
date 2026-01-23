"""AI Agent WebSocket routes with streaming support (PydanticAI)."""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Cookie, Query, WebSocket, WebSocketDisconnect
from pydantic_ai import (
    Agent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ToolCallPartDelta,
)
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)

from app.agents.assistant import get_agent
from app.agents.deps import Deps
from app.core.config import settings
from app.core.logfire_links import build_logfire_payload
from app.core.security import verify_token
from app.core.telemetry import get_trace_context
from app.db.session import get_db_context
from app.schemas.agent_tdd import AgentTddJudgeConfig, AgentTddRunCreate, AgentTddSubagentConfig
from app.services.agent_tdd import AgentTddService
from app.services.user import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentConnectionManager:
    """WebSocket connection manager for AI agent."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Agent WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(
            f"Agent WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

    async def send_event(self, websocket: WebSocket, event_type: str, data: Any) -> bool:
        """Send a JSON event to a specific WebSocket client.

        Returns True if sent successfully, False if connection is closed.
        """
        try:
            await websocket.send_json({"type": event_type, "data": data})
            return True
        except (WebSocketDisconnect, RuntimeError):
            # Connection already closed
            return False


manager = AgentConnectionManager()


def build_message_history(history: list[dict[str, str]]) -> list[ModelRequest | ModelResponse]:
    """Convert conversation history to PydanticAI message format."""
    model_history: list[ModelRequest | ModelResponse] = []

    for msg in history:
        if msg["role"] == "user":
            model_history.append(ModelRequest(parts=[UserPromptPart(content=msg["content"])]))
        elif msg["role"] == "assistant":
            model_history.append(ModelResponse(parts=[TextPart(content=msg["content"])]))
        elif msg["role"] == "system":
            model_history.append(ModelRequest(parts=[SystemPromptPart(content=msg["content"])]))

    return model_history


def resolve_logfire_payload(
    trace_id: str | None,
) -> dict[str, str] | None:
    return build_logfire_payload(trace_id)


def resolve_candidate_trace_id(candidate) -> str | None:
    if not candidate:
        return None
    metrics = candidate.metrics or {}
    if isinstance(metrics, dict):
        trace_id = metrics.get("trace_id")
        if isinstance(trace_id, str):
            return trace_id
    return None


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
    token: str | None = Query(None, alias="token"),
    access_token: str | None = Cookie(None),
) -> None:
    """WebSocket endpoint for AI agent with full event streaming.

    Requires authentication via:
    - Query parameter: ws://...?token=<jwt>
    - Cookie: access_token cookie (set by HTTP login)

    Uses PydanticAI iter() to stream all agent events including:
    - user_prompt: When user input is received
    - model_request_start: When model request begins
    - text_delta: Streaming text from the model
    - tool_call_delta: Streaming tool call arguments
    - tool_call: When a tool is called (with full args)
    - tool_result: When a tool returns a result
    - final_result: When the final result is ready
    - complete: When processing is complete
    - error: When an error occurs

    Expected input message format:
    {
        "message": "user message here",
        "history": [{"role": "user|assistant|system", "content": "..."}]
    }
    """
    from uuid import UUID

    # Authenticate the WebSocket connection
    auth_token = token or access_token

    if not auth_token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    payload = verify_token(auth_token)
    if payload is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    if payload.get("type") != "access":
        await websocket.close(code=4001, reason="Invalid token type")
        return

    user_id = payload.get("sub")
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    # Validate user exists and is active
    try:
        async with get_db_context() as db:
            user_service = UserService(db)
            user = await user_service.get_by_id(UUID(user_id))
            if not user.is_active:
                await websocket.close(code=4001, reason="User account is disabled")
                return
    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    await manager.connect(websocket)

    # Conversation state per connection
    conversation_history: list[dict[str, str]] = []
    deps = Deps()

    # Initialize session-scoped artifact directory if configured
    if settings.AUTOCODE_ARTIFACTS_DIR and deps.session_dir is None:
        timestamp = datetime.now().strftime("%Y-%m-%dT%H%M%S.%f")
        session_path = settings.AUTOCODE_ARTIFACTS_DIR / timestamp
        try:
            session_path.mkdir(parents=True, exist_ok=True)
            deps.session_dir = session_path
            logger.info(f"Created session artifact directory: {session_path}")
        except Exception as e:
            logger.error(f"Failed to create session artifact directory: {e}")

    try:
        while True:
            # Receive user message
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            # Optionally accept history from client (or use server-side tracking)
            if "history" in data:
                conversation_history = data["history"]

            if not user_message:
                await manager.send_event(websocket, "error", {"message": "Empty message"})
                continue

            await manager.send_event(websocket, "user_prompt", {"content": user_message})

            try:
                chosen_output: str | None = None

                if settings.DUAL_SUBAGENT_ENABLED:
                    await manager.send_event(websocket, "crew_started", {"mode": "dual_subagent"})

                    async with get_db_context() as db:
                        service = AgentTddService(db)
                        payload = AgentTddRunCreate(
                            message=user_message,
                            history=conversation_history,
                            subagents=[
                                AgentTddSubagentConfig(name="openai", provider="openai"),
                                AgentTddSubagentConfig(name="anthropic", provider="anthropic"),
                            ],
                            judge=AgentTddJudgeConfig(
                                provider="openai",
                                model_name=settings.JUDGE_LLM_MODEL,
                            ),
                            metadata={"source": "ws"},
                        )
                        result = await service.execute(payload, user_id=None)

                    chosen_output = None
                    selected_candidate = None
                    for candidate in result.candidates:
                        await manager.send_event(
                            websocket,
                            "agent_started",
                            {"agent": candidate.agent_name, "task": "candidate"},
                        )
                        await manager.send_event(
                            websocket,
                            "agent_completed",
                            {"agent": candidate.agent_name, "output": candidate.output or ""},
                        )

                    if result.decision and result.decision.candidate_id:
                        for candidate in result.candidates:
                            if candidate.id == result.decision.candidate_id:
                                chosen_output = candidate.output
                                selected_candidate = candidate
                                break

                    if not chosen_output and result.candidates:
                        chosen_output = result.candidates[0].output
                        selected_candidate = result.candidates[0]

                    selected_meta = None
                    if selected_candidate:
                        selected_meta = {
                            "agent_name": selected_candidate.agent_name,
                            "provider": selected_candidate.provider,
                            "model_name": selected_candidate.model_name,
                            "candidate_id": str(selected_candidate.id),
                        }

                    selected_trace_id = resolve_candidate_trace_id(selected_candidate)
                    if not selected_trace_id and result.decision:
                        selected_trace_id = result.decision.trace_id
                    if not selected_trace_id:
                        selected_trace_id = result.run.trace_id
                    logfire_payload = resolve_logfire_payload(selected_trace_id)

                    if not chosen_output:
                        await manager.send_event(
                            websocket,
                            "error",
                            {"message": "No candidate output produced by subagents."},
                        )
                    else:
                        await manager.send_event(websocket, "model_request_start", {})
                        await manager.send_event(
                            websocket,
                            "final_result",
                            {
                                "output": chosen_output,
                                "decision": result.decision.model_dump(mode="json")
                                if result.decision
                                else None,
                                "selected_candidate": selected_meta,
                                "logfire": logfire_payload,
                            },
                        )
                else:
                    assistant = get_agent()
                    model_history = build_message_history(conversation_history)

                    # Use iter() on the underlying PydanticAI agent to stream all events
                    async with assistant.agent.iter(
                        user_message,
                        deps=deps,
                        message_history=model_history,
                    ) as agent_run:
                        async for node in agent_run:
                            if Agent.is_user_prompt_node(node):
                                await manager.send_event(
                                    websocket,
                                    "user_prompt_processed",
                                    {"prompt": node.user_prompt},
                                )

                            elif Agent.is_model_request_node(node):
                                await manager.send_event(websocket, "model_request_start", {})

                                async with node.stream(agent_run.ctx) as request_stream:
                                    async for event in request_stream:
                                        if isinstance(event, PartStartEvent):
                                            await manager.send_event(
                                                websocket,
                                                "part_start",
                                                {
                                                    "index": event.index,
                                                    "part_type": type(event.part).__name__,
                                                },
                                            )
                                            # Send initial content from TextPart if present
                                            if (
                                                isinstance(event.part, TextPart)
                                                and event.part.content
                                            ):
                                                await manager.send_event(
                                                    websocket,
                                                    "text_delta",
                                                    {
                                                        "index": event.index,
                                                        "content": event.part.content,
                                                    },
                                                )

                                        elif isinstance(event, PartDeltaEvent):
                                            if isinstance(event.delta, TextPartDelta):
                                                await manager.send_event(
                                                    websocket,
                                                    "text_delta",
                                                    {
                                                        "index": event.index,
                                                        "content": event.delta.content_delta,
                                                    },
                                                )
                                            elif isinstance(event.delta, ToolCallPartDelta):
                                                await manager.send_event(
                                                    websocket,
                                                    "tool_call_delta",
                                                    {
                                                        "index": event.index,
                                                        "args_delta": event.delta.args_delta,
                                                    },
                                                )

                                        elif isinstance(event, FinalResultEvent):
                                            await manager.send_event(
                                                websocket,
                                                "final_result_start",
                                                {"tool_name": event.tool_name},
                                            )

                            elif Agent.is_call_tools_node(node):
                                await manager.send_event(websocket, "call_tools_start", {})

                                async with node.stream(agent_run.ctx) as handle_stream:
                                    async for tool_event in handle_stream:
                                        if isinstance(tool_event, FunctionToolCallEvent):
                                            await manager.send_event(
                                                websocket,
                                                "tool_call",
                                                {
                                                    "tool_name": tool_event.part.tool_name,
                                                    "args": tool_event.part.args,
                                                    "tool_call_id": tool_event.part.tool_call_id,
                                                },
                                            )

                                        elif isinstance(tool_event, FunctionToolResultEvent):
                                            await manager.send_event(
                                                websocket,
                                                "tool_result",
                                                {
                                                    "tool_call_id": tool_event.tool_call_id,
                                                    "content": str(tool_event.result.content),
                                                },
                                            )

                            elif Agent.is_end_node(node) and agent_run.result is not None:
                                trace_id, _ = get_trace_context()
                                logfire_payload = resolve_logfire_payload(trace_id)
                                await manager.send_event(
                                    websocket,
                                    "final_result",
                                    {
                                        "output": agent_run.result.output,
                                        "logfire": logfire_payload,
                                    },
                                )

                    if agent_run.result:
                        chosen_output = agent_run.result.output

                # Update conversation history with judge-selected output
                conversation_history.append({"role": "user", "content": user_message})
                if chosen_output:
                    conversation_history.append({"role": "assistant", "content": chosen_output})

                await manager.send_event(websocket, "complete", {})

            except WebSocketDisconnect:
                # Client disconnected during processing - this is normal
                logger.info("Client disconnected during agent processing")
                break
            except Exception as e:
                logger.exception(f"Error processing agent request: {e}")
                # Try to send error, but don't fail if connection is closed
                await manager.send_event(websocket, "error", {"message": str(e)})

    except WebSocketDisconnect:
        pass  # Normal disconnect
    finally:
        manager.disconnect(websocket)
