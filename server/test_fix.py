#!/usr/bin/env python3
"""
Test script to verify the fix for the encrypted_key issue
"""

import os
import sys
from dotenv import load_dotenv

# Add the server directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from onchain.data_registry import DataRegistry
from identity_server import IdentityServer

load_dotenv()

def test_fix():
    """Test that the fix for the encrypted_key issue works correctly"""
    print("🧪 Testing the fix for encrypted_key issue...")
    
    # Test data from the logs
    user_address = "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4"
    file_id = 1654116
    
    try:
        # Step 1: Derive personal server address from user address
        print(f"1️⃣ Deriving personal server address for user: {user_address}")
        identity_server = IdentityServer()
        user_server_keys = identity_server.derive_user_server_address(user_address)
        
        personal_server_address = user_server_keys["address"]
        print(f"✅ Derived personal server address: {personal_server_address}")
        
        # Step 2: Test that fetch_file_metadata now uses personal_server_address
        print(f"2️⃣ Testing fetch_file_metadata with personal server address...")
        data_registry = DataRegistry()
        
        # This should now work correctly with the personal server address
        file_metadata = data_registry.fetch_file_metadata(file_id, personal_server_address)
        
        if file_metadata:
            print(f"✅ File metadata retrieved successfully")
            print(f"   File ID: {file_metadata.file_id}")
            print(f"   Owner: {file_metadata.owner_address}")
            print(f"   URL: {file_metadata.public_url}")
            print(f"   Encrypted key length: {len(file_metadata.encrypted_key)}")
            
            if file_metadata.encrypted_key:
                print(f"✅ Encrypted key is not empty: {file_metadata.encrypted_key[:50]}...")
                return True
            else:
                print(f"❌ Encrypted key is still empty")
                return False
        else:
            print(f"❌ Failed to retrieve file metadata")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fix()
    if success:
        print("\n🎉 Fix test passed! The encrypted_key issue should be resolved.")
    else:
        print("\n❌ Fix test failed. The issue may still persist.")
    sys.exit(0 if success else 1) 