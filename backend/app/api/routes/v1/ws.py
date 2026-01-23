"""WebSocket routes."""

import asyncio
import json
import logging
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Cookie, Query, WebSocket, WebSocketDisconnect

from app.core.security import verify_token
from app.db.session import get_db_context
from app.services.user import UserService

if TYPE_CHECKING:
    from app.core.websocket_events import SprintEvent

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket connection manager with room support and event broadcasting.

    Supports both raw string messages (legacy) and typed event objects
    for granular sprint updates.
    """

    def __init__(self):
        # Room name -> list of WebSockets
        self.rooms: dict[str, list[WebSocket]] = {}
        # Room name -> sequence counter for event ordering
        self._sequences: dict[str, int] = {}
        # Lock to prevent race conditions during broadcast
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, room: str = "global") -> None:
        """Accept and store a new WebSocket connection in a room."""
        await websocket.accept()
        async with self._lock:
            if room not in self.rooms:
                self.rooms[room] = []
                self._sequences[room] = 0
            self.rooms[room].append(websocket)
            count = len(self.rooms[room])
        logger.debug(f"WebSocket connected to room '{room}'. Total in room: {count}")

    async def disconnect(self, websocket: WebSocket, room: str = "global") -> None:
        """Remove a WebSocket connection from a room."""
        async with self._lock:
            if room in self.rooms:
                if websocket in self.rooms[room]:
                    self.rooms[room].remove(websocket)
                if not self.rooms[room]:
                    del self.rooms[room]
                    self._sequences.pop(room, None)
        logger.debug(f"WebSocket disconnected from room '{room}'.")

    def get_next_sequence(self, room: str) -> int:
        """Get and increment the sequence number for a room."""
        if room not in self._sequences:
            self._sequences[room] = 0
        seq = self._sequences[room]
        self._sequences[room] += 1
        return seq

    async def broadcast_to_room(self, room: str, message: str) -> None:
        """Broadcast a raw string message to all connected WebSockets in a room.

        This is the legacy method for backwards compatibility.
        Uses a lock and list copy to prevent race conditions during iteration.
        """
        async with self._lock:
            if room not in self.rooms:
                return
            # Copy list to avoid mutation during iteration
            connections = list(self.rooms[room])

        disconnected = []
        for connection in connections:
            try:
                await connection.send_text(message)
            except (WebSocketDisconnect, RuntimeError) as e:
                logger.debug(f"Failed to send to WebSocket in room '{room}': {e}")
                disconnected.append(connection)

        # Clean up disconnected clients under lock
        if disconnected:
            async with self._lock:
                for conn in disconnected:
                    if room in self.rooms and conn in self.rooms[room]:
                        self.rooms[room].remove(conn)

    async def broadcast_event(self, room: str, event: "SprintEvent") -> None:
        """Broadcast a typed event to all connected WebSockets in a room.

        The event will be serialized to JSON with proper timestamp formatting.
        Uses a lock and list copy to prevent race conditions during iteration.
        """
        async with self._lock:
            if room not in self.rooms:
                return
            # Set sequence number on the event (under lock for thread safety)
            event.sequence = self.get_next_sequence(room)
            # Copy list to avoid mutation during iteration
            connections = list(self.rooms[room])

        # Serialize to JSON
        message = event.model_dump_json()

        disconnected = []
        for connection in connections:
            try:
                await connection.send_text(message)
            except (WebSocketDisconnect, RuntimeError) as e:
                logger.debug(f"Failed to send event to WebSocket in room '{room}': {e}")
                disconnected.append(connection)

        # Clean up disconnected clients under lock
        if disconnected:
            async with self._lock:
                for conn in disconnected:
                    if room in self.rooms and conn in self.rooms[room]:
                        self.rooms[room].remove(conn)

    async def broadcast_legacy_status(
        self,
        room: str,
        status: str,
        phase: str | None = None,
        details: str | None = None,
    ) -> None:
        """Broadcast a legacy sprint_update event for backwards compatibility.

        This sends the original message format that existing clients expect.
        """
        message = json.dumps(
            {
                "type": "sprint_update",
                "sprint_id": room,
                "status": status,
                "phase": phase,
                "details": details,
            }
        )
        await self.broadcast_to_room(room, message)

    async def broadcast(self, message: str) -> None:
        """Broadcast a message to all connected WebSockets in all rooms."""
        for room_name in list(self.rooms.keys()):
            await self.broadcast_to_room(room_name, message)

    def get_room_count(self, room: str) -> int:
        """Get the number of connections in a room."""
        return len(self.rooms.get(room, []))

    def get_all_rooms(self) -> list[str]:
        """Get list of all active room names."""
        return list(self.rooms.keys())


manager = ConnectionManager()


@router.websocket("/ws/sprint/{sprint_id}")
async def sprint_websocket_endpoint(
    websocket: WebSocket,
    sprint_id: str,
):
    """Public WebSocket endpoint for sprint real-time updates.

    This endpoint does NOT require authentication, consistent with the
    public sprint REST API. Clients can only receive updates, not send.

    The sprint_id is used as the room name for broadcasting.
    """
    await manager.connect(websocket, sprint_id)
    try:
        # Read-only: just keep connection alive, ignore any messages
        async for _ in websocket.iter_text():
            pass  # Ignore client messages (read-only connection)
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, sprint_id)


@router.websocket("/ws")
@router.websocket("/ws/{room}")
async def websocket_endpoint(
    websocket: WebSocket,
    room: str = "global",
    token: str | None = Query(None, alias="token"),
    access_token: str | None = Cookie(None),
):
    """WebSocket endpoint for real-time communication.

    Requires authentication via:
    - Query parameter: ws://...?token=<jwt>
    - Cookie: access_token cookie (set by HTTP login)

    Unauthenticated connections are rejected with close code 4001.
    """
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

    await manager.connect(websocket, room)
    try:
        async for data in websocket.iter_text():
            # If we receive data, we can broadcast it to the same room or global
            await manager.broadcast_to_room(room, f"Room {room}: {data}")
    finally:
        await manager.disconnect(websocket, room)
