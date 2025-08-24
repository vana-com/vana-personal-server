#!/usr/bin/env python3
"""
Check what CLI options are actually available for both tools.
"""

import subprocess
import requests
import json

def check_cli_in_container():
    """Check CLI help output via container exec."""
    
    print("Checking CLI help options...")
    
    # Test basic gemini help
    test_data = {
        "app_signature": "0x" + "0" * 130,
        "operation_request_json": json.dumps({"permission_id": 8888})  # Trigger mock but simple
    }
    
    # First let's create a simple test that should show us what happens
    response = requests.post("http://localhost:8080/api/v1/operations", json=test_data)
    print(f"Response: {response.status_code}")
    
    if response.status_code == 202:
        result = response.json()
        operation_id = result['id']
        print(f"Created operation: {operation_id}")
        
        # Wait and check what actually happened
        import time
        time.sleep(10)
        
        status_resp = requests.get(f"http://localhost:8080/api/v1/operations/{operation_id}")
        if status_resp.status_code == 200:
            data = status_resp.json()
            result_data = json.loads(data['result'])
            print(f"\nOperation result:")
            print(f"Status: {result_data['status']}")
            print(f"Summary: {result_data['summary']}")
            print(f"Stdout: {repr(result_data.get('stdout', ''))}")
            print(f"Logs: {result_data.get('logs', [])}")

if __name__ == "__main__":
    check_cli_in_container()