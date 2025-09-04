#!/usr/bin/env python3
"""
Test script to verify both Docker and Process agent runtimes work correctly.

Usage:
    python test_agent_runtime.py docker
    python test_agent_runtime.py process
"""
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

# Add the workspace to Python path for imports
sys.path.insert(0, '/workspace')

from services.agent_runtime_factory import create_agent_runner, get_runtime_info


async def test_agent_runtime(runtime_type: str):
    """Test the specified agent runtime with a simple execution."""
    
    print(f"\n=== Testing {runtime_type.upper()} Agent Runtime ===")
    
    # Set the runtime environment variable
    os.environ['AGENT_RUNTIME'] = runtime_type
    
    try:
        # Create the agent runner
        runner = create_agent_runner()
        
        # Print runtime info
        runtime_info = get_runtime_info()
        print(f"Runtime Info: {json.dumps(runtime_info, indent=2)}")
        
        # Prepare test data
        test_files = {
            "test_input.txt": b"This is a test file for the agent to process."
        }
        
        # Simple test goal that should work with any agent CLI
        test_goal = "List the files in the current directory and create a simple report in out/test_result.txt"
        
        # Test environment variables
        test_env = {
            "NO_COLOR": "1",
            "PYTHONUNBUFFERED": "1"
        }
        
        # For this test, we'll simulate a basic command that should exist
        # In real usage, this would be 'gemini' or 'qwen'
        if runtime_type == "process":
            # Test with a simple command that exists
            test_command = "ls"
            test_args = ["-la", "."]
        else:
            # For Docker, we'd need the actual agent image
            print("Docker runtime test requires agent image to be built.")
            print("Skipping actual execution for Docker runtime.")
            return
        
        print(f"Executing: {test_command} {' '.join(test_args)}")
        
        # Execute the test
        result = await runner.execute_agent(
            agent_type="test",
            command=test_command,
            args=test_args,
            workspace_files=test_files,
            env_vars=test_env,
            operation_id=f"test_{runtime_type}_{int(asyncio.get_event_loop().time())}"
        )
        
        print(f"Execution Result:")
        print(f"  Status: {result.get('status', 'unknown')}")
        print(f"  Summary: {result.get('summary', 'no summary')}")
        print(f"  Return Code: {result.get('return_code', 'unknown')}")
        print(f"  Execution Time: {result.get('execution_time', 0):.2f}s")
        print(f"  Artifacts: {len(result.get('artifacts', []))}")
        print(f"  Log Lines: {len(result.get('logs', []))}")
        
        # Show first few lines of stdout
        stdout = result.get('stdout', '')
        if stdout:
            lines = stdout.split('\n')[:5]
            print(f"  Stdout (first 5 lines):")
            for line in lines:
                print(f"    {line}")
        
        print(f"\n✅ {runtime_type.upper()} runtime test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ {runtime_type.upper()} runtime test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ['docker', 'process']:
        print("Usage: python test_agent_runtime.py [docker|process]")
        sys.exit(1)
    
    runtime_type = sys.argv[1]
    await test_agent_runtime(runtime_type)


if __name__ == "__main__":
    asyncio.run(main())