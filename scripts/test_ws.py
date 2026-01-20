
import asyncio
import websockets
import json
import sys

async def test_ws():
    uri = "ws://localhost:8000/api/v1/ws/agent" # Check path suffix? backend/app/api/routes/v1/agent.py defines @router.websocket("/ws/agent"). API_V1_STR in config is /api/v1. So /api/v1/ws/agent.
    # Wait for server to be ready
    await asyncio.sleep(2)
    
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            msg = {"message": "Hello Agent", "history": []}
            await websocket.send(json.dumps(msg))
            print("Sent message.")
            
            while True:
                resp = await websocket.recv()
                data = json.loads(resp)
                print(f"Received: {data.get('type')}")
                if data.get('type') in ['complete', 'error']:
                    break
            print("Test passed.")
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_ws())
