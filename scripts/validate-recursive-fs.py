#!/usr/bin/env python3
import time
import subprocess
import os
import glob
from pathlib import Path
from datetime import datetime, timezone

# Must match .env value
ARTIFACTS_DIR = os.environ.get("AUTOCODE_ARTIFACTS_DIR", "/Users/ray.manaloto.guilde/dev/tmp/guilde-lite-tdd-sprint-filesystem")

def main():
    print(f"--- FS Test Start ---")
    print(f"Artifacts Dir: {ARTIFACTS_DIR}")

    # 1. Run Playwright Test
    # Using 'npm test:e2e -- --config=playwright.simple.config.ts recursive-fs.spec.ts'
    cmd = ["npm", "run", "test:e2e", "--", "--config=playwright.simple.config.ts", "recursive-fs.spec.ts"]
    cwd = os.path.join(os.getcwd(), "frontend")
    
    print(f"Running: {' '.join(cmd)}")
    
    # Allow failure to check disk even if UI times out
    proc = subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)
    
    if proc.returncode == 0:
        print("Playwright Test: PASSED ✅")
    else:
        print("Playwright Test: FAILED ❌ (Check logs)")
        print("--- STDOUT (Tail) ---")
        print("\n".join(proc.stdout.splitlines()[-200:]))
        print("--- STDERR (Tail) ---")
        print("\n".join(proc.stderr.splitlines()[-200:]))

    # 2. Check for File Creation
    # Find the most recent subdirectory in ARTIFACTS_DIR
    try:
        subdirs = sorted(
            [d for d in Path(ARTIFACTS_DIR).iterdir() if d.is_dir()],
            key=os.path.getmtime,
            reverse=True
        )
        
        if not subdirs:
            print(f"❌ Verification Failed: No subdirectories found in {ARTIFACTS_DIR}")
            return

        latest_dir = subdirs[0]
        print(f"Checking latest session dir: {latest_dir}")
        
        # Look for the test file
        files = list(latest_dir.glob("test_file_*.txt"))
        if files:
            print(f"✅ Found created file: {files[0].name}")
            content = files[0].read_text()
            print(f"   Content: '{content}'")
            if "Hello from recursive verification!" in content:
                print("✅ Content verified!")
            else:
                print("❌ Content mismatch!")
        else:
            print("❌ No test file found in latest session directory.")
            print(f"   Contents: {[f.name for f in latest_dir.iterdir()]}")

    except Exception as e:
        print(f"❌ Verification Error: {e}")

if __name__ == "__main__":
    main()
