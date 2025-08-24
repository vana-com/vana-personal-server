#!/usr/bin/env python3
"""
View detailed results from an operation.
"""

import requests
import json
import sys
import base64

API_BASE = "http://localhost:8080/api/v1"

def view_operation_result(operation_id):
    """Fetch and display detailed operation results."""
    
    print(f"\n{'='*70}")
    print(f"Operation Result Viewer")
    print(f"Operation ID: {operation_id}")
    print(f"{'='*70}")
    
    response = requests.get(f"{API_BASE}/operations/{operation_id}")
    
    if response.status_code != 200:
        print(f"Error fetching operation: {response.status_code}")
        print(response.text[:500])
        return
    
    data = response.json()
    
    # Basic info
    print(f"\nStatus: {data.get('status')}")
    print(f"Started: {data.get('started_at', 'N/A')}")
    print(f"Finished: {data.get('finished_at', 'N/A')}")
    
    # Parse result
    if data.get('result'):
        try:
            result = json.loads(data['result'])
            
            print(f"\n{'='*70}")
            print("EXECUTION SUMMARY")
            print(f"{'='*70}")
            print(f"Status: {result.get('status', 'N/A')}")
            print(f"Summary: {result.get('summary', 'N/A')}")
            
            # Show notes if present
            notes = result.get('result', {}).get('notes')
            if notes:
                print(f"\nNotes: {notes}")
            
            # Show logs
            logs = result.get('logs', [])
            if logs:
                print(f"\n{'='*70}")
                print("EXECUTION LOGS")
                print(f"{'='*70}")
                for log in logs:
                    print(f"• {log}")
            
            # Show stdout output (agent's actual work)
            stdout = result.get('stdout', '')
            if stdout:
                print(f"\n{'='*70}")
                print("AGENT OUTPUT")
                print(f"{'='*70}")
                # Limit to reasonable length for display
                if len(stdout) > 3000:
                    print(stdout[:3000])
                    print(f"\n... (truncated, showing first 3000 of {len(stdout)} chars)")
                else:
                    print(stdout)
            
            # Show artifacts
            artifacts = result.get('artifacts', [])
            if artifacts:
                print(f"\n{'='*70}")
                print("GENERATED ARTIFACTS")
                print(f"{'='*70}")
                
                for i, artifact in enumerate(artifacts, 1):
                    if isinstance(artifact, dict):
                        print(f"\n{i}. {artifact.get('name', 'Unknown')}")
                        
                        # Try to decode and show content
                        content_b64 = artifact.get('content_base64')
                        if content_b64:
                            try:
                                content = base64.b64decode(content_b64).decode('utf-8')
                                print(f"   Size: {artifact.get('size', 0)} bytes")
                                print(f"   Content preview:")
                                print("-" * 50)
                                preview = content[:500]
                                print(preview)
                                if len(content) > 500:
                                    print(f"... (showing first 500 of {len(content)} chars)")
                                print("-" * 50)
                            except:
                                print(f"   (Binary content, {artifact.get('size', 0)} bytes)")
                    else:
                        print(f"{i}. {artifact}")
            
            # Show the actual result if complex
            actual_result = result.get('result', {})
            if actual_result and isinstance(actual_result, dict):
                artifacts_list = actual_result.get('artifacts', [])
                if artifacts_list:
                    print(f"\n{'='*70}")
                    print("DECLARED ARTIFACTS")
                    print(f"{'='*70}")
                    for artifact_path in artifacts_list:
                        print(f"• {artifact_path}")
            
        except json.JSONDecodeError:
            print("\nRaw result (not JSON):")
            print(data['result'][:1000])
    else:
        print("\nNo result data available")

def main():
    if len(sys.argv) < 2:
        # Try to get the last operation from logs
        print("Usage: python3 view_result.py <operation_id>")
        print("\nExample:")
        print("  python3 view_result.py gemini_1755985390841")
        print("\nTo find operation IDs, check the test output or logs:")
        print("  make logs | grep 'Operation created'")
        sys.exit(1)
    
    operation_id = sys.argv[1]
    view_operation_result(operation_id)

if __name__ == "__main__":
    main()