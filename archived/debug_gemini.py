#!/usr/bin/env python3
"""
Debug Gemini CLI issues.
"""

import requests
import json

def test_simple_gemini():
    """Test a very simple Gemini operation."""
    
    print("Testing simple Gemini operation...")
    
    response = requests.post(
        "http://localhost:8080/api/v1/operations",
        json={
            "app_signature": "0x" + "0" * 130,
            "operation_request_json": json.dumps({"permission_id": 9999})  # Will get simple goal
        }
    )
    
    if response.status_code == 202:
        result = response.json()
        operation_id = result['id']
        print(f"Simple operation created: {operation_id}")
        
        # Check result
        import time
        time.sleep(30)  # Wait 30 seconds
        
        status_response = requests.get(f"http://localhost:8080/api/v1/operations/{operation_id}")
        if status_response.status_code == 200:
            data = status_response.json()
            result_data = json.loads(data['result'])
            print(f"Status: {result_data['status']}")
            print(f"Stdout: {repr(result_data.get('stdout', ''))}")
    else:
        print(f"Failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_simple_gemini()