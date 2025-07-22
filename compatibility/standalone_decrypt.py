#!/usr/bin/env python3
"""
Standalone decryption function for compatibility testing.
This extracts only the decrypt_with_private_key function without external dependencies.
"""

import hashlib
import hmac
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from coincurve import PublicKey


def decrypt_with_private_key(encrypted_data: str, private_key: str) -> str:
    """
    Decrypt data with a wallet private key using eccrypto-compatible format.

    Args:
        encrypted_data: The encrypted data (hex string, with or without 0x prefix)
        private_key: The wallet private key (hex string, with or without 0x prefix)

    Returns:
        The decrypted data as a string
    """
    try:
        # Convert hex strings to bytes
        private_key_bytes = bytes.fromhex(private_key.replace("0x", ""))
        encrypted_data_bytes = bytes.fromhex(encrypted_data.replace("0x", ""))

        # Parse eccrypto format: iv(16) + ephemPublicKey(65) + ciphertext + mac(32)
        iv = encrypted_data_bytes[:16]
        ephem_public_key = encrypted_data_bytes[16:81]
        ciphertext = encrypted_data_bytes[81:-32]
        mac = encrypted_data_bytes[-32:]

        # Perform ECDH to get shared secret
        shared_point = PublicKey(ephem_public_key).multiply(private_key_bytes)
        shared_secret = shared_point.format(compressed=False)[1:33]  # x-coordinate

        # Derive encryption and MAC keys
        hash_output = hashlib.sha512(shared_secret).digest()
        enc_key = hash_output[:32]
        mac_key = hash_output[32:]

        # Verify MAC
        mac_data = iv + ephem_public_key + ciphertext
        expected_mac = hmac.new(mac_key, mac_data, hashlib.sha256).digest()

        if not hmac.compare_digest(mac, expected_mac):
            raise ValueError("MAC verification failed")

        # Decrypt using AES-256-CBC
        cipher = AES.new(enc_key, AES.MODE_CBC, iv)
        decrypted_padded = cipher.decrypt(ciphertext)
        decrypted_bytes = unpad(decrypted_padded, AES.block_size)

        return decrypted_bytes.decode("utf-8")

    except Exception as e:
        raise ValueError(f"Failed to decrypt with wallet private key: {str(e)}")


if __name__ == "__main__":
    import json
    import sys
    
    # Read test data from command line argument (JSON file path)
    if len(sys.argv) != 2:
        print(json.dumps({"success": False, "error": "Usage: python3 standalone_decrypt.py <test_data_file>"}))
        sys.exit(1)
    
    try:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
        
        # Decrypt using the function
        decrypted = decrypt_with_private_key(data['encrypted_data'], data['private_key'])
        
        # Compare with original
        success = decrypted == data['original_data']
        
        result = {
            'success': success,
            'original_length': len(data['original_data']),
            'decrypted_length': len(decrypted),
            'matches': success,
            'error': None
        }
        
        print(json.dumps(result))
        
    except Exception as e:
        result = {
            'success': False,
            'error': str(e),
            'original_length': len(data.get('original_data', '')) if 'data' in locals() else 0,
            'decrypted_length': 0,
            'matches': False
        }
        print(json.dumps(result))