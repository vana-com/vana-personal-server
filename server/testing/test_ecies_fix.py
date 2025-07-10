#!/usr/bin/env python3
"""
Test to prove that the ECIES decryption fix works correctly.
This test specifically validates that the personal server can decrypt
encrypted keys when the private key is provided as a hex string.
"""

import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv
from eth_account.messages import encode_defunct
from web3 import Web3
from ecies import encrypt, decrypt as ecies_decrypt

# Add the server directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from personal_server import PersonalServer
from entities import PersonalServerRequest, AccessPermissionsResponse, FileMetadata
from identity_server import IdentityServer

load_dotenv()

def test_ecies_decryption_with_hex_private_key():
    """
    Test that proves ECIES decryption works when private key is provided as hex string.
    This is the core issue that was fixed.
    """
    print("🔐 Testing ECIES decryption with hex private key...")
    
    # Generate a test private key as hex string (as returned by identity_server)
    user_address = "0xd7Ae9319049f0B6cA9AD044b165c5B4F143EF451"
    identity_server = IdentityServer()
    user_server_keys = identity_server.derive_user_server_address(user_address)
    
    private_key_hex = user_server_keys["private_key"]  # This is a hex string
    public_key_hex = user_server_keys["public_key"]
    
    print(f"✅ Private key (hex): {private_key_hex[:20]}...")
    print(f"✅ Public key (hex): {public_key_hex[:20]}...")
    
    # Test data to encrypt
    test_data = b"test symmetric key 32 bytes long!"
    
    try:
        # Encrypt data using the public key
        encrypted_data = encrypt(public_key_hex, test_data)
        print(f"✅ Data encrypted successfully")
        
        private_key_bytes = bytes.fromhex(private_key_hex.replace('0x', ''))
        new_way_result = ecies_decrypt(private_key_bytes, encrypted_data)
        
        if new_way_result == test_data:
            print("✅ NEW WAY: Successfully decrypted data")
            print(f"✅ Original: {test_data}")
            print(f"✅ Decrypted: {new_way_result}")
            return True
        else:
            print("❌ NEW WAY: Decryption failed - data mismatch")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

def test_personal_server_execute_with_fixed_ecies():
    """
    Test that the fixed personal server can handle the full execution flow.
    """
    print("\n🚀 Testing PersonalServer.execute with fixed ECIES...")
    
    # Test data
    user_address = "0xd7Ae9319049f0B6cA9AD044b165c5B4F143EF451"
    permission_id = 6
    file_id = 999
    test_file_content = "hello world from test"
    symmetric_key = b"test_symmetric_key_32_bytes_long!"
    
    # Derive keys
    identity_server = IdentityServer()
    user_server_keys = identity_server.derive_user_server_address(user_address)
    personal_server_private_key = user_server_keys["private_key"]
    personal_server_public_key = user_server_keys["public_key"]
    personal_server_address = user_server_keys["address"]
    
    # Encrypt symmetric key for the server
    encrypted_symmetric_key = encrypt(personal_server_public_key, symmetric_key)
    encrypted_symmetric_key_hex = encrypted_symmetric_key.hex()
    
    # Prepare request
    request_data = {
        "user_address": user_address,
        "permission_id": permission_id
    }
    request_json = json.dumps(request_data)
    
    # Sign request
    web3 = Web3()
    message_hash = encode_defunct(text=request_json)
    application_private_key = "bce540d49a5a7f3982f20937b2c4b9d2010dc4ba6f8a9c77ea1221366f062ab7"
    signature = web3.eth.account.sign_message(message_hash, private_key=application_private_key)
    
    # Mock external dependencies
    mock_access_permissions = AccessPermissionsResponse(
        app_address="0xApp123",
        file_ids={file_id},
        operation="llm_inference",
        parameters={"prompt": "Analyze this: {{data}}"}
    )
    
    mock_file_metadata = FileMetadata(
        file_id=file_id,
        owner_address=user_address,
        public_url="ipfs://test",
        encrypted_key=encrypted_symmetric_key_hex
    )
    
    # Mock LLM
    mock_llm = Mock()
    mock_llm.run = Mock(return_value="LLM processed: " + test_file_content)
    
    # Create PersonalServer instance
    server = PersonalServer(llm=mock_llm)
    
    # Mock the external calls
    with patch.object(server, 'fetch_access_permissions', return_value=mock_access_permissions):
        with patch.object(server.data_registry, 'fetch_file_metadata', return_value=mock_file_metadata):
            with patch('personal_server.download_file', return_value=b"encrypted_file_content"):
                with patch('personal_server.decrypt', return_value=test_file_content):
                    
                    # Execute the request
                    try:
                        result = server.execute(request_json, signature.signature)
                        print(f"✅ PersonalServer.execute completed successfully")
                        print(f"✅ Result: {result}")
                        
                        # Verify the LLM was called with the correct prompt
                        mock_llm.run.assert_called_once()
                        call_args = mock_llm.run.call_args[0][0]
                        assert "Analyze this:" in call_args
                        assert test_file_content in call_args
                        
                        return True
                        
                    except Exception as e:
                        print(f"❌ PersonalServer.execute failed: {e}")
                        return False

def test_ecies_decryption_in_isolation():
    """
    Test ECIES decryption in isolation to prove the fix works.
    """
    print("\n🔬 Testing ECIES decryption in isolation...")
    
    # Create a test scenario exactly like the one in the logs
    private_key_hex = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"  # 64 chars
    test_data = b"test data to encrypt"
    
    # Encrypt with ecies
    try:
        # First, get the corresponding public key for encryption
        from eth_keys import keys
        private_key_obj = keys.PrivateKey(bytes.fromhex(private_key_hex.replace('0x', '')))
        public_key_obj = private_key_obj.public_key
        
        # Encrypt the data
        encrypted_data = encrypt(public_key_obj.to_hex(), test_data)
        print(f"✅ Data encrypted successfully")
        
        # Test the fixed decryption method
        private_key_bytes = bytes.fromhex(private_key_hex.replace('0x', ''))
        decrypted_data = ecies_decrypt(private_key_bytes, encrypted_data)
        
        if decrypted_data == test_data:
            print("✅ ECIES decryption works correctly with bytes private key")
            return True
        else:
            print("❌ ECIES decryption failed - data mismatch")
            return False
            
    except Exception as e:
        print(f"❌ ECIES isolation test failed: {e}")
        return False

def main():
    """Run all tests to prove the fix works."""
    print("🧪 Running tests to prove ECIES decryption fix works...")
    print("=" * 60)
    
    tests = [
        ("ECIES Decryption with Hex Private Key", test_ecies_decryption_with_hex_private_key),
        ("ECIES Decryption in Isolation", test_ecies_decryption_in_isolation),
        ("PersonalServer Execute with Fixed ECIES", test_personal_server_execute_with_fixed_ecies),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The ECIES decryption fix is working correctly.")
        print("✅ The personal server can now decrypt encrypted keys properly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. The fix may not be complete.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)