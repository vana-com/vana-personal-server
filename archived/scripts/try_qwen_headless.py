"""
Quick local smoke test for QwenCodeAgentProvider.

This script tests the headless qwen-code integration by creating
a simple agentic task and verifying the execution contract works.

Usage:
    python -m scripts.try_qwen_headless

Prerequisites:
    1. qwen-code CLI installed globally or QWEN_CLI_PATH set
    2. Environment variables configured:
       - QWEN_API_URL
       - QWEN_MODEL_NAME  
       - QWEN_API_KEY
    3. pexpect dependency installed
"""

import base64
import os
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from compute.qwen_agent import QwenCodeAgentProvider
    from compute.gemini_agent import GeminiAgentProvider
    from domain.entities import GrantFile
    from settings import get_settings
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure to run from project root: python -m scripts.try_qwen_headless")
    sys.exit(1)


def create_mock_grant_file(goal: str, operation: str = "prompt_qwen_agent") -> GrantFile:
    """Create a mock grant file for testing."""
    return GrantFile(
        grantee="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
        operation=operation,
        parameters={"goal": goal},
        expires=None
    )


def main():
    """Run the smoke test."""
    print("=== Qwen Code Headless Smoke Test ===\n")

    # Check configuration
    settings = get_settings()
    print("Configuration check:")
    
    # Check if we have API credentials or using OAuth
    has_api_creds = all([settings.qwen_api_url, settings.qwen_model_name, settings.qwen_api_key])
    
    if has_api_creds:
        print("  Mode: API credentials (production)")
        print(f"  QWEN_API_URL: ✓")
        print(f"  QWEN_MODEL_NAME: ✓")
        print(f"  QWEN_API_KEY: ✓")
    else:
        print("  Mode: OAuth/cached credentials (development)")
        print("  Using locally authenticated qwen-code CLI")
    
    print(f"  QWEN_CLI_PATH: {settings.qwen_cli_path or 'qwen (default)'}")
    print()
    
    # Quick test to see if qwen CLI is working
    import subprocess
    try:
        result = subprocess.run(
            ["qwen", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✓ qwen-code CLI is installed (version: {result.stdout.strip()})")
        else:
            print("❌ qwen-code CLI not working properly")
            return 1
    except Exception as e:
        print(f"❌ Failed to run qwen-code CLI: {e}")
        return 1
    
    print()

    # Test goal and input files
    goal = "List all files in this workspace and create a summary in ./out/file_summary.md"
    
    # Create some test input files
    test_files = {
        "README.txt": b"This is a dummy README file for testing the qwen headless integration.",
        "sample.py": b"""
def hello_world():
    \"\"\"A simple test function.\"\"\"
    print("Hello from the test file!")
    return "success"

if __name__ == "__main__":
    hello_world()
""".strip(),
        "data.json": b'{"test": true, "purpose": "smoke test", "files": ["README.txt", "sample.py"]}'
    }

    print(f"Test goal: {goal}")
    print(f"Test files: {list(test_files.keys())}")
    print()

    try:
        print("Initializing QwenCodeAgentProvider...")
        provider = QwenCodeAgentProvider()
        print("✓ Provider initialized successfully")
        
        print("\nCreating mock grant file...")
        grant_file = create_mock_grant_file(goal)
        
        # Convert to files_content format expected by provider
        files_content = [content.decode('utf-8') for content in test_files.values()]
        
        print("✓ Grant file and test data prepared")
        
        print(f"\nExecuting agentic task (timeout: {settings.qwen_timeout_sec}s)...")
        print("This may take a while as qwen processes the request...")
        
        # Execute the task
        execute_result = provider.execute(grant_file, files_content)
        print(f"✓ Task submitted successfully")
        print(f"  Operation ID: {execute_result.id}")
        print(f"  Created at: {execute_result.created_at}")
        
        print("\nRetrieving results...")
        get_result = provider.get(execute_result.id)
        print(f"✓ Results retrieved")
        print(f"  Status: {get_result.status}")
        
        # Parse and display the results
        if get_result.result:
            import json
            try:
                result_data = json.loads(get_result.result)
                print(f"\n=== Execution Results ===")
                print(f"Status: {result_data.get('status', 'unknown')}")
                print(f"Summary: {result_data.get('summary', 'no summary')}")
                
                # Show artifacts
                artifacts = result_data.get('artifacts', [])
                print(f"\nArtifacts ({len(artifacts)}):")
                for artifact in artifacts:
                    name = artifact.get('name', 'unnamed')
                    size = artifact.get('size', 0)
                    print(f"  - {name}: {size} bytes")
                    
                    # Optionally show content of small text files
                    if name.endswith('.md') and size < 1000:
                        try:
                            content_b64 = artifact.get('content_base64', '')
                            content = base64.b64decode(content_b64).decode('utf-8')
                            print(f"    Content preview:")
                            for line in content.split('\n')[:5]:
                                print(f"    | {line}")
                            if len(content.split('\n')) > 5:
                                print(f"    | ... (truncated)")
                        except Exception as e:
                            print(f"    | (error reading content: {e})")
                
                # Show logs 
                logs = result_data.get('logs', [])
                print(f"\nExecution logs ({len(logs)}):")
                for log in logs:  # Show all logs for debugging
                    print(f"  - {log}")
                    
                # Show stdout for debugging
                stdout = result_data.get('stdout', '')
                if stdout:
                    print(f"\nRaw stdout (first 1000 chars):")
                    print("=" * 50)
                    print(stdout[:1000])
                    print("=" * 50)
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse result JSON: {e}")
                print("Raw result:", get_result.result[:500], "..." if len(get_result.result) > 500 else "")
        else:
            print("❌ No result data returned")
            
        print(f"\n=== Test Summary ===")
        if get_result.status == "succeeded":
            print("✅ Smoke test PASSED - qwen-code headless integration is working!")
        else:
            print("⚠️  Smoke test completed but with errors - check logs above")
            
    except Exception as e:
        print(f"❌ Smoke test FAILED: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())