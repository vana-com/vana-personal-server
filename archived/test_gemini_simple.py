#!/usr/bin/env python3
"""
Test Gemini CLI directly without the full server stack.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# Add the workspace to Python path
sys.path.insert(0, '/workspace')

def test_gemini_cli():
    """Test Gemini CLI directly."""
    
    try:
        from compute.gemini_agent import GeminiAgentProvider
        from domain.entities import GrantFile
        
        print("Testing Gemini CLI directly...")
        
        # Create a simple grant file
        grant_file = GrantFile(
            grantee="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            operation="prompt_gemini_agent",
            parameters={
                "goal": "Say hello and list the numbers 1, 2, 3"
            }
        )
        
        # Create simple test data
        files_content = ["This is a simple test file with some text."]
        
        # Initialize Gemini agent
        agent = GeminiAgentProvider()
        
        print(f"Agent initialized with timeout: {agent.timeout_sec}s")
        print(f"Using API auth: {agent.use_api_auth}")
        print(f"CLI command: {agent.get_cli_command()}")
        
        # Execute the task
        print("Executing task...")
        result = agent.execute(grant_file, files_content)
        
        print(f"Task completed with ID: {result.id}")
        
        # Get the result
        print("Getting result...")
        get_result = agent.get(result.id)
        
        print(f"Status: {get_result.status}")
        print(f"Result preview: {get_result.result[:500]}...")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gemini_cli()