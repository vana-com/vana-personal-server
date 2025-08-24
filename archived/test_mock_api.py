#!/usr/bin/env python3
"""
Test script for mock API operations.
Run this after starting the Docker container with mock mode.
"""

import requests
import json
import time
import sys

API_BASE = "http://localhost:8080/api/v1"

def test_gemini_operation():
    """Test Gemini agent operation."""
    print("\n" + "="*60)
    print("Testing Gemini Agent Operation")
    print("="*60)
    
    # Create operation
    print("\n1. Creating Gemini operation (permission_id: 4096)...")
    
    response = requests.post(
        f"{API_BASE}/operations",
        json={
            "app_signature": "0x" + "0" * 130,
            "operation_request_json": json.dumps({"permission_id": 4096})
        }
    )
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 202:
        result = response.json()
        print(f"   ✓ Operation created!")
        print(f"   ID: {result.get('id')}")
        print(f"   Created: {result.get('created_at')}")
        
        operation_id = result.get('id')
        
        # Wait a bit
        print("\n2. Waiting 3 seconds for operation to process...")
        time.sleep(3)
        
        # Get status
        print(f"\n3. Getting operation status for {operation_id}...")
        status_response = requests.get(f"{API_BASE}/operations/{operation_id}")
        
        if status_response.status_code == 200:
            status = status_response.json()
            print(f"   ✓ Status retrieved!")
            print(f"   Status: {status.get('status')}")
            
            if status.get('result'):
                print(f"\n4. Operation Result:")
                try:
                    result_data = json.loads(status['result'])
                    print(json.dumps(result_data, indent=2)[:500])
                except:
                    print(status.get('result')[:500])
        else:
            print(f"   ✗ Failed to get status: {status_response.status_code}")
            print(f"   Error: {status_response.text[:200]}")
    else:
        print(f"   ✗ Failed to create operation!")
        error_text = response.text
        if "traceback" in error_text:
            # Extract just the error message
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('detail', 'Unknown error')}")
                if "ImportError" in error_text:
                    print("\n   Fix needed: Import error in mock_operations.py")
            except:
                print(f"   Error: {error_text[:200]}")
        else:
            print(f"   Error: {error_text[:500]}")

def test_qwen_operation():
    """Test Qwen agent operation."""
    print("\n" + "="*60)
    print("Testing Qwen Agent Operation")
    print("="*60)
    
    print("\n1. Creating Qwen operation (permission_id: 3072)...")
    
    response = requests.post(
        f"{API_BASE}/operations",
        json={
            "app_signature": "0x" + "0" * 130,
            "operation_request_json": json.dumps({"permission_id": 3072})
        }
    )
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 202:
        result = response.json()
        print(f"   ✓ Operation created!")
        print(f"   ID: {result.get('id')}")
        print(f"   Created: {result.get('created_at')}")
    else:
        print(f"   ✗ Failed: {response.text[:200]}")

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
        print("✗ Cannot connect to API. Is the container running?")
        print("\nTo start the container:")
        print("  make down")
        print("  make up")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("Mock API Testing Script")
    print("-" * 60)
    
    if not check_health():
        print("\nPlease ensure the container is running with mock mode enabled.")
        sys.exit(1)
    
    # Test operations
    test_gemini_operation()
    test_qwen_operation()
    
    print("\n" + "="*60)
    print("Testing Complete")
    print("="*60)
    print("\nTo view container logs:")
    print("  make logs")
    print("\nTo stop the container:")
    print("  make down")

if __name__ == "__main__":
    main()