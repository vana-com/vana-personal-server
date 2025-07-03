import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3
from eth_account.messages import encode_defunct
from server.entities import PersonalServerRequest
from dotenv import load_dotenv
from server.personal_server import PersonalServer
from server.llm import Llm

load_dotenv()

MOCK_REQUEST = PersonalServerRequest(
    user_address=os.getenv("USER_ADDRESS"),
    file_ids=[12],
    operation="llm_inference",
    parameters={"prompt": "Summarise the content of: {{data}}"},
)

def __main__():
    web3 = Web3()

    # Prepare test data
    request = MOCK_REQUEST

    # ------------------------------------------------------------
    # Inputs to PersonalServer which will be prepared on the frontend
    request = '{"user_address": "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4", "file_ids": [999], "operation": "llm_inference", "parameters": {"prompt": "Analyze personality: {{data}}"}}'
    message_hash = encode_defunct(text=request)

    app_address = os.getenv("TEST_APP_ADDRESS")
    signature = web3.eth.account.sign_message(message_hash, private_key=os.getenv("TEST_APP_PRIVATE_KEY"))
    print(f"App {app_address} signed the message")

    # ------------------------------------------------------------
    # Setting up PersonalServer with mocks
    dummy_llm = Llm(client=None)
    dummy_llm.run = lambda prompt: "Processed prompt: " + prompt

    personal_server = PersonalServer(llm=dummy_llm, web3=web3)
    output = personal_server.execute(request, signature.signature)
    print(f"Output: {output}")

    # Test file encryption
    # print("\n--- Testing File Encryption ---")
    
    # # Import encryption functions
    # from server.encrypt import encrypt_file, decrypt_file
    
    # # Define test file path and encryption key
    # test_file_path = "/Users/maciejwitowski/Documents/vana/data-portability-testing/personal_information.json"
    # encryption_key = "test_encryption_key_123"
    
    # # Check if file exists
    # if os.path.exists(test_file_path):
    #     print(f"Found test file: {test_file_path}")
        
    #     # Encrypt the file
    #     encrypted_path = encrypt_file(encryption_key, test_file_path)
    #     print(f"File encrypted to: {encrypted_path}")
        
    #     # Decrypt the file to verify
    #     decrypted_path = decrypt_file(encryption_key, encrypted_path)
    #     print(f"File decrypted to: {decrypted_path}")
        
    #     # Verify the decrypted content matches original
    #     with open(test_file_path, 'r') as f:
    #         original_content = f.read()
    #     with open(decrypted_path, 'r') as f:
    #         decrypted_content = f.read()
        
    #     if original_content == decrypted_content:
    #         print("✓ Encryption/decryption test passed - content matches")
    #     else:
    #         print("✗ Encryption/decryption test failed - content mismatch")
    # else:
    #     print(f"Test file not found: {test_file_path}")


if __name__ == "__main__":
    __main__()

