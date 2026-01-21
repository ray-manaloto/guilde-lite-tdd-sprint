"""WebSocket routes."""

from fastapi import APIRouter, WebSocket

router = APIRouter()


class ConnectionManager:
    """WebSocket connection manager with room support."""

    def __init__(self):
        # Room name -> list of WebSockets
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str = "global") -> None:
        """Accept and store a new WebSocket connection in a room."""
        await websocket.accept()
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(websocket)

    def disconnect(self, websocket: WebSocket, room: str = "global") -> None:
        """Remove a WebSocket connection from a room."""
        if room in self.rooms:
            self.rooms[room].remove(websocket)
            if not self.rooms[room]:
                del self.rooms[room]

    async def broadcast_to_room(self, room: str, message: str) -> None:
        """Broadcast a message to all connected WebSockets in a specific room."""
        if room in self.rooms:
            for connection in self.rooms[room]:
                await connection.send_text(message)

    async def broadcast(self, message: str) -> None:
        """Broadcast a message to all connected WebSockets in all rooms."""
        for room_connections in self.rooms.values():
            for connection in room_connections:
                await connection.send_text(message)


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
