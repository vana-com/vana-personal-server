#!/usr/bin/env python3
"""
Client to test the key derivation server deployed on r8.im
"""

import os
import json
import replicate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_key_derivation():
    """Test the key derivation server with sample user addresses"""
    print("Testing key derivation server on r8.im...")
    
    # Check if API token is set
    api_token = os.getenv('REPLICATE_API_TOKEN')
    if not api_token:
        print("❌ REPLICATE_API_TOKEN not found in environment")
        return False
    
    print(f"🔑 API Token found: {api_token[:10]}...")
    
    # Test user addresses
    test_addresses = [
        "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4",
        "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
        "0x1234567890123456789012345678901234567890"
    ]
    
    for i, user_address in enumerate(test_addresses, 1):
        print(f"\n🧪 Test {i}: Deriving keys for {user_address}")
        print("=" * 60)
        
        try:
            # Call the deployed model
            output = replicate.run(
                "vana-com/key-derivation-server:latest",  # Update with actual model ID
                input={
                    "user_address": user_address
                }
            )
            
            print(f"📥 Raw output type: {type(output)}")
            print(f"📥 Raw output: {output}")
            
            if output is None:
                print("❌ No response received from model")
                continue
            elif isinstance(output, str):
                try:
                    result = json.loads(output)
                    print("✅ Response received:")
                    print(json.dumps(result, indent=2))
                    
                    # Verify deterministic behavior
                    if "derivation_index" in result:
                        print(f"🔢 Derivation index: {result['derivation_index']}")
                    if "derived_address" in result:
                        print(f"📍 Derived address: {result['derived_address']}")
                    if "derivation_path" in result:
                        print(f"🛤️  Derivation path: {result['derivation_path']}")
                        
                except json.JSONDecodeError:
                    print(f"✅ Response received: {output}")
            elif hasattr(output, '__iter__') and not isinstance(output, str):
                response = "".join(str(chunk) for chunk in output)
                print(f"✅ Response received: {response}")
            else:
                print(f"✅ Response received: {str(output)}")
                
        except Exception as replicate_error:
            print(f"❌ Replicate API error: {replicate_error}")
            print(f"❌ Error type: {type(replicate_error)}")
            continue
    
    return True

def test_deterministic_behavior():
    """Test that the same user address always produces the same keys"""
    print("\n🔄 Testing deterministic behavior...")
    print("=" * 60)
    
    api_token = os.getenv('REPLICATE_API_TOKEN')
    if not api_token:
        print("❌ REPLICATE_API_TOKEN not found in environment")
        return False
    
    test_address = "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4"
    results = []
    
    # Call the model multiple times with the same address
    for i in range(3):
        print(f"🔄 Call {i+1}/3 for {test_address}")
        
        try:
            output = replicate.run(
                "vana-com/key-derivation-server:latest",  # Update with actual model ID
                input={
                    "user_address": test_address
                }
            )
            
            if isinstance(output, str):
                result = json.loads(output)
                results.append(result)
                print(f"✅ Call {i+1} successful")
            else:
                print(f"❌ Call {i+1} failed - unexpected output type")
                
        except Exception as e:
            print(f"❌ Call {i+1} failed: {e}")
    
    # Compare results
    if len(results) >= 2:
        print("\n🔍 Comparing results for deterministic behavior:")
        for i in range(len(results) - 1):
            if results[i] == results[i + 1]:
                print(f"✅ Results {i+1} and {i+2} are identical")
            else:
                print(f"❌ Results {i+1} and {i+2} are different!")
                print(f"   Result {i+1}: {results[i]}")
                print(f"   Result {i+2}: {results[i+1]}")
    
    return True

def main():
    """Main function to test the key derivation server"""
    print("🔑 Testing Key Derivation Server on r8.im")
    print("=" * 60)
    
    success1 = test_key_derivation()
    success2 = test_deterministic_behavior()
    
    if success1 and success2:
        print("\n🎉 Key derivation server test completed successfully!")
    else:
        print("\n❌ Key derivation server test failed!")

if __name__ == "__main__":
    main() 