#!/usr/bin/env python3
"""
Test script for personal data agent operations with rich mock data.
"""

import requests
import json
import time
import sys
import random

API_BASE = "http://localhost:8080/api/v1"

# Different permission IDs for testing
TEST_SCENARIOS = [
    {
        "permission_id": 4001,  # Use specific ID to ensure privacy goal
        "name": "Gemini Privacy Audit", 
        "description": "Analyze personal data for privacy and security concerns"
    },
    {
        "permission_id": 4002,
        "name": "Gemini Data Audit",
        "description": "Comprehensive audit of what companies can infer from your data"
    },
    {
        "permission_id": 3001,
        "name": "Qwen Knowledge Base",
        "description": "Build a personal knowledge base from your ChatGPT conversations"
    },
    {
        "permission_id": 3002,
        "name": "Qwen Music Engine",
        "description": "Create a music recommendation engine from Spotify data"
    },
]

def test_operation(permission_id, name, description):
    """Test a single operation with personal data."""
    print(f"\n{'='*60}")
    print(f"{name}")
    print(f"{description}")
    print(f"{'='*60}")
    
    # Create operation
    print(f"\n1. Creating operation (permission_id: {permission_id})...")
    
    response = requests.post(
        f"{API_BASE}/operations",
        json={
            "app_signature": "0x" + "0" * 130,
            "operation_request_json": json.dumps({"permission_id": permission_id})
        }
    )
    
    if response.status_code == 202:
        result = response.json()
        operation_id = result.get('id')
        print(f"   ✓ Operation created: {operation_id}")
        
        # Wait for processing
        print(f"\n2. Processing personal data...")
        
        # Poll for completion (max 30 seconds)
        max_attempts = 10
        for attempt in range(max_attempts):
            time.sleep(3)
            
            status_response = requests.get(f"{API_BASE}/operations/{operation_id}")
            
            if status_response.status_code == 200:
                status = status_response.json()
                op_status = status.get('status')
                print(f"   Status: {op_status}")
                
                if op_status in ['succeeded', 'failed']:
                    if op_status == 'succeeded':
                        print(f"\n3. ✓ Operation completed successfully!")
                        
                        # Show result preview
                        if status.get('result'):
                            try:
                                result_data = json.loads(status['result'])
                                print(f"\n   Result Summary:")
                                print(f"   - Status: {result_data.get('status', 'N/A')}")
                                print(f"   - Summary: {result_data.get('summary', 'N/A')}")
                                
                                # Show artifacts if any
                                artifacts = result_data.get('artifacts', [])
                                if artifacts:
                                    print(f"   - Artifacts generated: {len(artifacts)}")
                                    for artifact in artifacts[:3]:  # Show first 3
                                        if isinstance(artifact, dict):
                                            print(f"     • {artifact.get('name', 'unknown')}")
                                        else:
                                            print(f"     • {artifact}")
                                
                                # Show logs excerpt
                                logs = result_data.get('logs', [])
                                if logs:
                                    print(f"   - Processing logs: {logs[0]}")
                                    
                            except:
                                # Just show raw result preview
                                result_preview = status.get('result', '')[:300]
                                print(f"   Result preview: {result_preview}...")
                    else:
                        print(f"\n3. ✗ Operation failed")
                        print(f"   Result: {status.get('result', 'No details')[:500]}")
                    break
            else:
                print(f"   Waiting... (attempt {attempt+1}/{max_attempts})")
        else:
            print(f"\n3. ⚠ Operation timed out after {max_attempts*3} seconds")
    else:
        print(f"   ✗ Failed to create operation: {response.status_code}")
        if response.text:
            try:
                error = response.json()
                print(f"   Error: {error.get('detail', 'Unknown error')}")
            except:
                print(f"   Error: {response.text[:200]}")

def check_health():
    """Check if API is healthy."""
    print("\nChecking API health...")
    try:
        response = requests.get(
            f"{API_BASE}/identity",
            params={"address": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"}
        )
        if response.status_code == 200:
            print("✓ API is healthy")
            return True
        else:
            print(f"✗ API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to API")
        print("\nTo start the container:")
        print("  make down")
        print("  make build")
        print("  make up")
        return False

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║          Personal Data Agent Testing Suite                   ║
║                                                              ║
║  Testing agents with rich mock personal data including:      ║
║  • ChatGPT conversation history                             ║
║  • Spotify listening data                                   ║
║  • LinkedIn profile information                             ║
║  • Fitness and health metrics                               ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    if not check_health():
        print("\nPlease ensure the container is running with mock mode enabled.")
        sys.exit(1)
    
    # Let user choose or run all
    print("\nAvailable test scenarios:")
    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        print(f"  {i}. {scenario['name']}: {scenario['description']}")
    print(f"  {len(TEST_SCENARIOS)+1}. Run all scenarios")
    print(f"  0. Exit")
    
    try:
        choice = input("\nSelect scenario (1-5, or 0 to exit): ").strip()
        
        if choice == '0':
            print("Exiting...")
            sys.exit(0)
        elif choice == str(len(TEST_SCENARIOS)+1):
            # Run all
            for scenario in TEST_SCENARIOS:
                test_operation(**scenario)
                time.sleep(2)  # Brief pause between tests
        else:
            # Run selected
            idx = int(choice) - 1
            if 0 <= idx < len(TEST_SCENARIOS):
                test_operation(**TEST_SCENARIOS[idx])
            else:
                print("Invalid choice")
    except (ValueError, KeyboardInterrupt):
        print("\nExiting...")
        sys.exit(0)
    
    print("\n" + "="*60)
    print("Testing Complete!")
    print("="*60)
    print("\nThe agents are processing your mock personal data to:")
    print("• Generate personalized code and tools")
    print("• Analyze privacy and security implications")
    print("• Identify patterns and insights")
    print("• Create actionable recommendations")
    print("\nTo view full logs: make logs")
    print("To stop container: make down")

if __name__ == "__main__":
    main()