"""WebSocket routes."""

import json
import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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

    async def connect(self, websocket: WebSocket, room: str = "global") -> None:
        """Accept and store a new WebSocket connection in a room."""
        await websocket.accept()
        if room not in self.rooms:
            self.rooms[room] = []
            self._sequences[room] = 0
        self.rooms[room].append(websocket)
        logger.debug(
            f"WebSocket connected to room '{room}'. Total in room: {len(self.rooms[room])}"
        )

    def disconnect(self, websocket: WebSocket, room: str = "global") -> None:
        """Remove a WebSocket connection from a room."""
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
        """
        if room not in self.rooms:
            return
        disconnected = []
        for connection in self.rooms[room]:
            try:
                await connection.send_text(message)
            except (WebSocketDisconnect, RuntimeError) as e:
                logger.debug(f"Failed to send to WebSocket in room '{room}': {e}")
                disconnected.append(connection)
        # Clean up disconnected clients
        for conn in disconnected:
            if conn in self.rooms.get(room, []):
                self.rooms[room].remove(conn)

    async def broadcast_event(self, room: str, event: "SprintEvent") -> None:
        """Broadcast a typed event to all connected WebSockets in a room.

        The event will be serialized to JSON with proper timestamp formatting.
        """
        if room not in self.rooms:
            return

        # Set sequence number on the event
        event.sequence = self.get_next_sequence(room)

        # Serialize to JSON
        message = event.model_dump_json()

        disconnected = []
        for connection in self.rooms[room]:
            try:
                await connection.send_text(message)
            except (WebSocketDisconnect, RuntimeError) as e:
                logger.debug(f"Failed to send event to WebSocket in room '{room}': {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            if conn in self.rooms.get(room, []):
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


@router.websocket("/ws")
@router.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str = "global"):
    """WebSocket endpoint for real-time communication."""
    await manager.connect(websocket, room)
    try:
        async for data in websocket.iter_text():
            # If we receive data, we can broadcast it to the same room or global
            await manager.broadcast_to_room(room, f"Room {room}: {data}")
    finally:
        manager.disconnect(websocket, room)
