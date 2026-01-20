
import sys
import subprocess
import time
from pathlib import Path

def run_cli_validation():
    print("--- CLI Agent Test Start ---")
    
    project_root = Path(__file__).parent.parent
    frontend_dir = project_root / "frontend"
    
    # Run Playwright Test
    cmd = [
        "npm", "run", "test:e2e", "--", 
        "--config=playwright.simple.config.ts", 
        "cli-agent.spec.ts"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=frontend_dir, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("ERRORS:")
        print(result.stderr)
        
    if result.returncode == 0:
        print("Playwright Test: PASSED ✅")
        sys.exit(0)
    else:
        print("Playwright Test: FAILED ❌")
        sys.exit(1)

if __name__ == "__main__":
    run_cli_validation()
