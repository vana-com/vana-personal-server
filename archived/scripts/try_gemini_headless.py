"""
Quick local smoke test for GeminiAgentProvider.

This script tests the headless Gemini CLI integration by creating
a simple agentic task and verifying the execution contract works.

Usage:
    python -m scripts.try_gemini_headless

Prerequisites:
    1. gemini CLI installed globally
    2. Environment variables configured (GEMINI_API_KEY or OAuth)
    3. pexpect dependency installed
"""

import base64
import json
import os
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from compute.gemini_agent import GeminiAgentProvider
    from domain.entities import GrantFile
    from settings import get_settings
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure to run from project root: python -m scripts.try_gemini_headless")
    sys.exit(1)


def create_mock_grant_file(goal: str) -> GrantFile:
    """Create a mock grant file for testing."""
    return GrantFile(
        grantee="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
        operation="prompt_gemini_agent",
        parameters={"goal": goal},
        expires=None
    )


def main():
    """Run the smoke test."""
    print("=== Gemini CLI Headless Smoke Test ===\n")

    # Check configuration
    settings = get_settings()
    print("Configuration check:")
    
    # Check if we have API credentials or using OAuth
    has_api_key = bool(settings.gemini_api_key)
    
    if has_api_key:
        print("  Mode: API key (production)")
        print(f"  GEMINI_API_KEY: ✓")
        print(f"  GEMINI_USE_VERTEX_AI: {settings.gemini_use_vertex_ai}")
    else:
        print("  Mode: Google OAuth/cached credentials (development)")
        print("  Using locally authenticated gemini CLI")
    
    print(f"  GEMINI_CLI_PATH: {settings.gemini_cli_path or 'gemini (default)'}")
    print()
    
    # Quick test to see if gemini CLI is working
    import subprocess
    try:
        result = subprocess.run(
            ["gemini", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✓ Gemini CLI is installed (version: {result.stdout.strip()})")
        else:
            print("❌ Gemini CLI not working properly")
            return 1
    except Exception as e:
        print(f"❌ Failed to run Gemini CLI: {e}")
        return 1
    
    print()

    # Test goal and input files
    goal = "List all files in this workspace and create a summary in ./out/file_summary.md"
    
    # Create some test input files
    test_files = [
        "This is a dummy README file for testing the Gemini headless integration.",
        """def hello_world():
    \"\"\"A simple test function.\"\"\"
    print("Hello from Gemini test!")
    return "success"

if __name__ == "__main__":
    hello_world()""",
        '{"test": true, "purpose": "gemini smoke test", "agent": "gemini"}'
    ]

    print(f"Test goal: {goal}")
    print(f"Test files: {len(test_files)} files")
    print()

    try:
        print("Initializing GeminiAgentProvider...")
        provider = GeminiAgentProvider()
        print("✓ Provider initialized successfully")
        
        print("\nCreating mock grant file...")
        grant_file = create_mock_grant_file(goal)
        
        print("✓ Grant file and test data prepared")
        
        print(f"\nExecuting agentic task (timeout: {settings.gemini_timeout_sec}s)...")
        print("This may take a while as Gemini processes the request...")
        
        # Execute the task
        execute_result = provider.execute(grant_file, test_files)
        print(f"✓ Task submitted successfully")
        print(f"  Operation ID: {execute_result.id}")
        print(f"  Created at: {execute_result.created_at}")
        
        print("\nRetrieving results...")
        get_result = provider.get(execute_result.id)
        print(f"✓ Results retrieved")
        print(f"  Status: {get_result.status}")
        
        # Parse and display the results
        if get_result.result:
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
                    
                    # Show content of small text files
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
                for log in logs:
                    print(f"  - {log}")
                    
                # Show stdout for debugging
                stdout = result_data.get('stdout', '')
                if stdout:
                    print(f"\nRaw stdout (first 1000 chars):")
                    print("=" * 50)
                    print(stdout[:1000])
                    if len(stdout) > 1000:
                        print("... (truncated)")
                    print("=" * 50)
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse result JSON: {e}")
                print("Raw result:", get_result.result[:500])
        else:
            print("❌ No result data returned")
            
        print(f"\n=== Test Summary ===")
        if get_result.status == "succeeded":
            print("✅ Smoke test PASSED - Gemini CLI headless integration is working!")
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