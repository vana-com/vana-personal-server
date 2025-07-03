import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3
from eth_account.messages import encode_defunct
# from server.entities import PersonalServerRequest
from dotenv import load_dotenv
# from server.personal_server import PersonalServer
# from server.llm import Llm
import pgpy
from pgpy.constants import SymmetricKeyAlgorithm, HashAlgorithm, CompressionAlgorithm
from eth_account import Account
from coincurve import PrivateKey, PublicKey
from ecies import encrypt, decrypt
from ecies.utils import generate_eth_key, generate_key
from eth_keys import keys

load_dotenv()

# MOCK_REQUEST = PersonalServerRequest(
#     user_address=os.getenv("USER_ADDRESS"),
#     file_ids=[12],
#     operation="llm_inference",
#     parameters={"prompt": "Summarise the content of: {{data}}"},
# )

def __main__():
    web3 = Web3()

    # Prepare test data
    # request = MOCK_REQUEST

    # ------------------------------------------------------------
    # Inputs to PersonalServer which will be prepared on the frontend
    # request = '{"user_address": "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4", "file_ids": [999], "operation": "llm_inference", "parameters": {"prompt": "Analyze personality: {{data}}"}}'
    # message_hash = encode_defunct(text=request)

    # app_address = os.getenv("TEST_APP_ADDRESS")
    # signature = web3.eth.account.sign_message(message_hash, private_key=os.getenv("TEST_APP_PRIVATE_KEY"))
    # print(f"App {app_address} signed the message")

    # # ------------------------------------------------------------
    # # Setting up PersonalServer with mocks
    # dummy_llm = Llm(client=None)
    # dummy_llm.run = lambda prompt: "Processed prompt: " + prompt

    # personal_server = PersonalServer(llm=dummy_llm, web3=web3)
    # output = personal_server.execute(request, signature.signature)
    # print(f"Output: {output}")

    # Test file encryption
    print("\n--- Testing File Encryption ---")
    
    
    # # # Define test file path and encryption key
    test_file_path = "/Users/maciejwitowski/Documents/vana/data-portability-testing/personal_information.json"
    personal_server_address = "0xd390Bf493Afec7590f34d6907862f5ecbF5aEA30"
    personal_server_private_key = "987840ffce35689b179f1ac6cfaa8c04fdbf246dd91ea99e8bfb1a824a67d108"

    # 1. Generate symmetric GPG encryption key. Print the key in logs.
    symmetric_key = SymmetricKeyAlgorithm.AES256.gen_key()
    print(f"Generated symmetric key: {symmetric_key.hex()}")
    
    # 2. Encrypt the file with the symmetric key and store it under the same folder with .pgp extension
    with open(test_file_path, 'rb') as f:
        file_content = f.read()
    
    message = pgpy.PGPMessage.new(file_content, compression=CompressionAlgorithm.ZLIB)
    encrypted_message = message.encrypt(
        passphrase=symmetric_key.hex(),
        sessionkey=symmetric_key,
        cipher=SymmetricKeyAlgorithm.AES256,
        hash=HashAlgorithm.SHA256
    )
    
    encrypted_file_path = f"{test_file_path}.pgp"
    with open(encrypted_file_path, 'wb') as f:
        f.write(str(encrypted_message).encode())
    
    print(f"File encrypted and saved to: {encrypted_file_path}")
    
    # 3. Encrypt the symmetric key with the personal server's public key using ECIES
    # Create a private key object from the existing private key
    personal_server_private_key_bytes = bytes.fromhex(personal_server_private_key)
    
    # Create the key object properly
    personal_server_eth_key = keys.PrivateKey(personal_server_private_key_bytes)
    
    # Get the public key for encryption
    personal_server_public_key = personal_server_eth_key.public_key
    
    # Encrypt the symmetric key using ECIES
    encrypted_symmetric_key = encrypt(personal_server_public_key.to_hex(), symmetric_key)
    
    # Save the encrypted symmetric key
    encrypted_key_path = f"{test_file_path}.key.ecies"
    with open(encrypted_key_path, 'wb') as f:
        f.write(encrypted_symmetric_key)
    
    print(f"Encrypted symmetric key saved to: {encrypted_key_path}")
    print(f"Personal server address: {personal_server_address}")
    print(f"Personal server public key: {personal_server_public_key.to_hex()}")
    print(f"Encrypted symmetric key (hex): {encrypted_symmetric_key.hex()}")
    
    # Verify that only the personal server can decrypt the key
    try:
        decrypted_symmetric_key = decrypt(personal_server_private_key, encrypted_symmetric_key)
        print(f"Successfully decrypted symmetric key: {decrypted_symmetric_key.hex()}")
        print(f"Keys match: {decrypted_symmetric_key == symmetric_key}")
    except Exception as e:
        print(f"Decryption failed: {e}")
    
if __name__ == "__main__":
    __main__()

