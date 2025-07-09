import json
import os
import sys
from dotenv import load_dotenv
from eth_account.messages import encode_defunct
from web3 import Web3
from eciespy import decrypt as ecies_decrypt

from personal_server import PersonalServer
from llm import Llm

load_dotenv()

def test_ecies_decryption():
    """Test that the personal server can decrypt ECIES-encrypted symmetric keys"""
    print("Testing ECIES decryption functionality...")
    
    # Test data from our previous encryption test
    personal_server_private_key = os.getenv("PERSONAL_SERVER_PRIVATE_KEY")
    encrypted_symmetric_key_hex = "0444507cbd80da6a686ce222d31389ffc9aef17eb7c9b041271b880d6ae44f7c1138de5b19940ac86e618b559436ad1ccf92738c5d0c3a5b8fdf039e50537707bafc4f5690082cc058b88c264d4026dfbbb1c050306658dcc58f5985b646dfc206a98573d40227954d141a5b4e565a107cd78ba796c476b14c838ba579c443a0e3"
    
    try:
        # Convert hex to bytes
        encrypted_symmetric_key = bytes.fromhex(encrypted_symmetric_key_hex)
        
        # Test ECIES decryption
        decrypted_symmetric_key = ecies_decrypt(personal_server_private_key, encrypted_symmetric_key)
        print(f"✅ Successfully decrypted symmetric key: {decrypted_symmetric_key.hex()}")
        
        # Test that the personal server can use this key
        print("✅ ECIES decryption is working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ ECIES decryption failed: {e}")
        return False

def test_personal_server():
    """Test the full personal server flow with new permission_id structure"""
    print("\nTesting full personal server flow...")
    
    web3 = Web3()

    # Test data with new structure - using permission_id
    request = '{"user_address": "0xd7Ae9319049f0B6cA9AD044b165c5B4F143EF451", "permission_id": 6}'
    message_hash = encode_defunct(text=request)

    # Use a test private key for signing
    application_private_key = "bce540d49a5a7f3982f20937b2c4b9d2010dc4ba6f8a9c77ea1221366f062ab7"
    
    try:
        signature = web3.eth.account.sign_message(message_hash, private_key=application_private_key)
        print(f"✅ Message signed successfully. Signature: {signature.signature.hex()}")

        # Setup PersonalServer with mocks
        dummy_llm = Llm(client=None)
        dummy_llm.run = lambda prompt: "Processed prompt: " + prompt
        
        personal_server = PersonalServer(llm=dummy_llm)
        
        output = personal_server.execute(request, signature.signature)
        print(f"✅ Personal server executed successfully")
        print(f"Output: {output}")
        return True
        
    except Exception as e:
        print(f"❌ Personal server test failed: {e}")
        print(f"Error details: {type(e).__name__}: {str(e)}")
        return False

if __name__ == "__main__":
    # Test ECIES decryption first
    ecies_success = test_ecies_decryption()
    
    # Test full personal server flow
    if ecies_success:
        server_success = test_personal_server()
        
        if server_success:
            print("\n🎉 All tests passed! The personal server is working correctly.")
        else:
            print("\n⚠️  ECIES works but personal server has issues.")
    else:
        print("\n❌ ECIES decryption failed. Personal server cannot work without it.") 