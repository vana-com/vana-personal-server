"""
Encryption utilities compatible with existing decrypt.py functions.
Uses eccrypto-compatible format for consistency.
"""
import hashlib
import hmac
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from coincurve import PrivateKey, PublicKey


def encrypt_with_public_key(data: bytes, public_key: str) -> str:
    """
    Encrypt data with a public key using eccrypto-compatible format.
    Compatible with decrypt_with_private_key in utils/files/decrypt.py.
    
    Args:
        data: The data to encrypt (bytes)
        public_key: The public key (hex string, with or without 0x prefix)
        
    Returns:
        The encrypted data as hex string
    """
    try:
        # Remove 0x prefix if present
        if public_key.startswith('0x'):
            public_key = public_key[2:]
        
        # Convert public key to bytes, handling eth_account format
        public_key_bytes = bytes.fromhex(public_key)
        
        # eth_account produces 64-byte public keys (raw x,y coordinates)
        # coincurve needs 65-byte uncompressed format (04 prefix + x + y)
        if len(public_key_bytes) == 64:
            public_key_bytes = b'\x04' + public_key_bytes
        
        public_key_obj = PublicKey(public_key_bytes)
        
        # Generate ephemeral private key
        ephemeral_private_key = PrivateKey()
        ephemeral_public_key = ephemeral_private_key.public_key
        
        # Perform ECDH to get shared secret
        shared_point = public_key_obj.multiply(ephemeral_private_key.secret)
        shared_secret = shared_point.format(compressed=False)[1:33]  # x-coordinate
        
        # Derive encryption and MAC keys
        hash_output = hashlib.sha512(shared_secret).digest()
        enc_key = hash_output[:32]
        mac_key = hash_output[32:]
        
        # Generate random IV
        iv = os.urandom(16)
        
        # Pad and encrypt data using AES-256-CBC
        padded_data = pad(data, AES.block_size)
        cipher = AES.new(enc_key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(padded_data)
        
        # Get ephemeral public key bytes (uncompressed format)
        ephem_public_key_bytes = ephemeral_public_key.format(compressed=False)
        
        # Create MAC data: iv + ephemPublicKey + ciphertext
        mac_data = iv + ephem_public_key_bytes + ciphertext
        mac = hmac.new(mac_key, mac_data, hashlib.sha256).digest()
        
        # Combine all parts: iv(16) + ephemPublicKey(65) + ciphertext + mac(32)
        encrypted_data = iv + ephem_public_key_bytes + ciphertext + mac
        
        return encrypted_data.hex()
        
    except Exception as e:
        raise ValueError(f"Failed to encrypt with public key: {str(e)}")


def encrypt_symmetric_key_for_server(symmetric_key: bytes, server_public_key: str) -> str:
    """
    Encrypt a symmetric key using the server's public key.
    Uses eccrypto-compatible format.
    
    Args:
        symmetric_key: The Fernet key to encrypt
        server_public_key: Server's public key (hex string)
        
    Returns:
        Encrypted symmetric key as hex string
    """
    return encrypt_with_public_key(symmetric_key, server_public_key)


def decrypt_symmetric_key_with_server(encrypted_key_hex: str, server_private_key: str) -> bytes:
    """
    Decrypt a symmetric key using the server's private key.
    Uses existing decrypt_with_private_key function for consistency.
    
    Args:
        encrypted_key_hex: Encrypted key as hex string
        server_private_key: Server's private key (hex string)
        
    Returns:
        The decrypted symmetric key as bytes
    """
    # Use existing decrypt function
    decrypted_str = decrypt_with_private_key(encrypted_key_hex, server_private_key)
    return decrypted_str.encode('utf-8')  # Convert back to bytes for Fernet