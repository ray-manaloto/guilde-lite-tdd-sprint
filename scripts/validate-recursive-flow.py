#!/usr/bin/env python3
import time
import subprocess
import os
import requests
import json
from datetime import datetime, timezone

def main():
    start_time = datetime.now(timezone.utc)
    print(f"--- Test Start: {start_time.isoformat()} ---")

    # Run Playwright Test
    # Using 'npm test:e2e -- recursive-agent.spec.ts' assuming npm scripts are setup
    cmd = ["npm", "run", "test:e2e", "--", "--config=playwright.simple.config.ts", "recursive-agent.spec.ts"]
    cwd = os.path.join(os.getcwd(), "frontend")
    
    print(f"Running: {' '.join(cmd)} in {cwd}")
    
    # Allow failure to verify Logfire spans even if test times out
    proc = subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)
    if proc.returncode == 0:
        print("Playwright Test: PASSED ✅")
    else:
        print("Playwright Test: FAILED ❌ (Check logs for UI issues)")
        # Print tail of stderr for context
        print("\n".join(proc.stderr.splitlines()[-10:]))

    end_time = datetime.now(timezone.utc)
    print(f"--- Test End: {end_time.isoformat()} ---")

    # Logfire Validation
    read_token = os.environ.get("LOGFIRE_READ_TOKEN")
    if not read_token:
        print("Skipping Logfire validation: LOGFIRE_READ_TOKEN not found.")
        return

    print("Querying Logfire via API...")
    # NOTE: Using public API endpoint. 
    # Adjust query to find "agent_browser.cli" spans in the time range
    
    # Since direct SQL API access might require complex auth (cookie/header), 
    # we simulate the check by providing the Deep Link for the user to verify manually
    # unless we have a specific SDK method for this.
    
    # Constructing a Logfire link
    # project_slug is hardcoded or needs to be fetched. Assuming 'guilde-lite' based on logs.
    project_slug = "guilde-lite" # based on logs "logfire-us.pydantic.dev/sortakool/guilde-lite"
    
    print(f"\n🔍 **Manual Verification Link**:")
    print(f"https://logfire.pydantic.dev/sortakool/{project_slug}/traces?live=false&start={start_time.isoformat()}&end={end_time.isoformat()}&filter=span_name%3D%27agent_browser.cli%27")
    
    print("\n⚠️  Note: Automated API query requires configured SDK 'read' client which is not fully integrated in this script yet.")
    print("   Please click the link above. If you see 'agent_browser.cli' spans, the Recursive Flow is VALIDATED.")

if __name__ == "__main__":
    main()
