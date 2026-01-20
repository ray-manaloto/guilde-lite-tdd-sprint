
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.agents.tools.agent_integration import run_claude_agent

# Mock context
class MockContext:
    pass

try:
    print("Testing run_claude_agent with live CLI...")
    result = run_claude_agent(MockContext(), "Say integration_test_success")
    print(f"Result: {result}")
    
    if "integration_test_success" in result:
        print("✅ SUCCESS: Claude CLI integration working.")
        sys.exit(0)
    else:
        print("❌ FAILURE: Unexpected output.")
        sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)
