import httpx
import asyncio
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Auth
        email = f"automator-{datetime.now().timestamp()}@test.com"
        password = "password123"
        
        print(f"Registering {email}...")
        resp = await client.post("/auth/register", json={
            "email": email,
            "password": password,
            "full_name": "Automator"
        })
        
        print("Logging in...")
        resp = await client.post("/auth/login", data={
            "username": email,
            "password": password
        })
        if resp.status_code != 200:
            print(f"Login failed: {resp.text}")
            return

        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create Sprint
        print("Creating Sprint...")
        start = datetime.now()
        end = start + timedelta(days=7)
        
        sprint_data = {
            "name": f"Auto Build Sprint {int(start.timestamp())}",
            "goal": "Verify Phase Runner Trigger. Create a file called 'phase_runner_verified.txt'.",
            "start_date": start.date().isoformat(),
            "end_date": end.date().isoformat(),
            "status": "planned"
        }
        
        resp = await client.post("/sprints", json=sprint_data, headers=headers)
        if resp.status_code != 201:
            print(f"Failed to create sprint: {resp.text}")
            return
            
        sprint = resp.json()
        print(f"Sprint Created: ID={sprint['id']}, Name='{sprint['name']}'")
        print("Check backend logs for 'Starting PhaseRunner'...")

if __name__ == "__main__":
    asyncio.run(main())
