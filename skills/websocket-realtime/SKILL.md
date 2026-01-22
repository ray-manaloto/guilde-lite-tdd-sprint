---
name: websocket-realtime
description: WebSocket implementation for real-time frontend/backend communication. Use when implementing real-time updates, streaming responses, live status updates, or bidirectional communication between Next.js and FastAPI.
---

# WebSocket Real-Time Communication

Implement real-time communication between Next.js frontend and FastAPI backend.

## Architecture Overview

```
Next.js (Frontend)          FastAPI (Backend)
     │                           │
     │  WebSocket Connection     │
     │◄─────────────────────────►│
     │                           │
     │  1. Sprint status         │
     │  2. Agent messages        │
     │  3. Build progress        │
     │  4. Live logs             │
     │                           │
```

## Backend: FastAPI WebSocket

### Connection Manager

```python
# backend/app/core/websocket.py
from fastapi import WebSocket
from typing import Dict, Set
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)

    async def broadcast(self, channel: str, message: dict):
        if channel in self.active_connections:
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except:
                    self.disconnect(connection, channel)

    async def send_personal(self, websocket: WebSocket, message: dict):
        await websocket.send_json(message)

manager = ConnectionManager()
```

### WebSocket Endpoint

```python
# backend/app/api/routes/v1/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.core.websocket import manager
from app.core.auth import get_current_user_ws

router = APIRouter()

@router.websocket("/ws/sprints/{sprint_id}")
async def sprint_websocket(
    websocket: WebSocket,
    sprint_id: str,
    user = Depends(get_current_user_ws)
):
    channel = f"sprint:{sprint_id}"
    await manager.connect(websocket, channel)

    try:
        while True:
            data = await websocket.receive_json()
            # Handle incoming messages
            if data.get("type") == "ping":
                await manager.send_personal(websocket, {"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
```

### Broadcasting from Services

```python
# backend/app/services/sprint.py
from app.core.websocket import manager

class SprintService:
    async def update_status(self, sprint_id: str, status: str):
        # Update database
        await self.repository.update_status(sprint_id, status)

        # Broadcast to connected clients
        await manager.broadcast(
            f"sprint:{sprint_id}",
            {
                "type": "status_update",
                "sprint_id": sprint_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
```

## Frontend: Next.js WebSocket Client

### WebSocket Hook

```typescript
// frontend/src/hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketMessage {
  type: string;
  [key: string]: unknown;
}

export function useWebSocket(url: string) {
  const ws = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  const connect = useCallback(() => {
    const token = localStorage.getItem('token');
    const wsUrl = `${url}?token=${token}`;

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setLastMessage(data);
    };

    ws.current.onclose = () => {
      setIsConnected(false);
      // Reconnect after delay
      setTimeout(connect, 3000);
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => ws.current?.close();
  }, [connect]);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  }, []);

  return { isConnected, lastMessage, sendMessage };
}
```

### Sprint Status Component

```typescript
// frontend/src/components/SprintStatus.tsx
'use client';

import { useWebSocket } from '@/hooks/useWebSocket';
import { useEffect, useState } from 'react';

interface SprintStatusProps {
  sprintId: string;
}

export function SprintStatus({ sprintId }: SprintStatusProps) {
  const [status, setStatus] = useState<string>('pending');
  const [logs, setLogs] = useState<string[]>([]);

  const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws/sprints/${sprintId}`;
  const { isConnected, lastMessage } = useWebSocket(wsUrl);

  useEffect(() => {
    if (!lastMessage) return;

    switch (lastMessage.type) {
      case 'status_update':
        setStatus(lastMessage.status as string);
        break;
      case 'log':
        setLogs(prev => [...prev, lastMessage.message as string]);
        break;
      case 'agent_message':
        // Handle agent output
        break;
    }
  }, [lastMessage]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
        <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
      </div>

      <div className="p-4 bg-gray-100 rounded">
        <h3 className="font-semibold">Status: {status}</h3>
      </div>

      <div className="p-4 bg-black text-green-400 font-mono text-sm max-h-96 overflow-y-auto">
        {logs.map((log, i) => (
          <div key={i}>{log}</div>
        ))}
      </div>
    </div>
  );
}
```

## Common Patterns

### Heartbeat/Ping-Pong

```typescript
// Frontend: Send ping every 30 seconds
useEffect(() => {
  const interval = setInterval(() => {
    sendMessage({ type: 'ping' });
  }, 30000);
  return () => clearInterval(interval);
}, [sendMessage]);
```

### Reconnection with Backoff

```typescript
const reconnect = useCallback(() => {
  let delay = 1000;
  const maxDelay = 30000;

  const attempt = () => {
    connect();
    delay = Math.min(delay * 2, maxDelay);
    setTimeout(attempt, delay);
  };

  attempt();
}, [connect]);
```

### Message Queue for Offline

```typescript
const [messageQueue, setMessageQueue] = useState<WebSocketMessage[]>([]);

const sendMessage = useCallback((message: WebSocketMessage) => {
  if (ws.current?.readyState === WebSocket.OPEN) {
    ws.current.send(JSON.stringify(message));
  } else {
    setMessageQueue(prev => [...prev, message]);
  }
}, []);

// Flush queue on reconnect
useEffect(() => {
  if (isConnected && messageQueue.length > 0) {
    messageQueue.forEach(msg => sendMessage(msg));
    setMessageQueue([]);
  }
}, [isConnected, messageQueue, sendMessage]);
```

## Testing WebSockets

### Backend Test

```python
# tests/integration/test_websocket.py
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.main import app

def test_websocket_connection():
    client = TestClient(app)
    with client.websocket_connect("/ws/sprints/test-sprint") as websocket:
        websocket.send_json({"type": "ping"})
        data = websocket.receive_json()
        assert data["type"] == "pong"
```

### Frontend Test

```typescript
// __tests__/useWebSocket.test.ts
import { renderHook, act } from '@testing-library/react';
import { useWebSocket } from '@/hooks/useWebSocket';
import WS from 'jest-websocket-mock';

describe('useWebSocket', () => {
  let server: WS;

  beforeEach(() => {
    server = new WS('ws://localhost:8000/ws/test');
  });

  afterEach(() => {
    WS.clean();
  });

  it('connects and receives messages', async () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost:8000/ws/test')
    );

    await server.connected;
    expect(result.current.isConnected).toBe(true);

    server.send(JSON.stringify({ type: 'test', data: 'hello' }));

    expect(result.current.lastMessage).toEqual({ type: 'test', data: 'hello' });
  });
});
```

## References

- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [React WebSocket Patterns](https://blog.logrocket.com/websocket-tutorial-react-node-js/)
