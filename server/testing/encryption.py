import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from server.llm import Llm
import pgpy
from coincurve import PrivateKey, PublicKey
from eth_keys import keys

# from server.entities import PersonalServerRequest
from dotenv import load_dotenv
from ecies import decrypt, encrypt
from eth_account.messages import encode_defunct
from pgpy.constants import CompressionAlgorithm, HashAlgorithm, SymmetricKeyAlgorithm
from web3 import Web3

load_dotenv()

def __main__():
    print("\n--- Testing File Encryption ---")
    
    
    # # # Define test file path and encryption key
    test_file_path = os.getenv("TEST_FILE_PATH")
    personal_server_address = os.getenv("PERSONAL_SERVER_ADDRESS")
    personal_server_private_key = os.getenv("PERSONAL_SERVER_PRIVATE_KEY")

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

