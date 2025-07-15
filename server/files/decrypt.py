import gnupg
import hashlib
import hmac
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from coincurve import PublicKey


def decrypt(encryption_key: str, content: str) -> str:
    """
    Decrypt file content using the encryption key (user's signature).
    
    Args:
        encryption_key: The user's signature that was used as the encryption password
        content: The encrypted file content as a string
        
    Returns:
        The decrypted file content as a string
    """
    try:
        gpg = gnupg.GPG()
        decrypted_data = gpg.decrypt(content, passphrase=encryption_key)
        
        if not decrypted_data.ok:
            raise ValueError(f"Decryption failed: {decrypted_data.status}")
        
        return str(decrypted_data)
        
    except Exception as e:
        raise ValueError(f"Failed to decrypt file content: {str(e)}")


def decrypt_with_wallet_private_key(encrypted_data: str, private_key: str) -> str:
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
        private_key_bytes = bytes.fromhex(private_key.replace('0x', ''))
        encrypted_data_bytes = bytes.fromhex(encrypted_data.replace('0x', ''))
        
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
        
        return decrypted_bytes.decode('utf-8')
        
    except Exception as e:
        raise ValueError(f"Failed to decrypt with wallet private key: {str(e)}")


def decrypt_user_data(encrypted_data: bytes, encryption_key: str) -> bytes:
    """
    Decrypt user data using OpenPGP with the encryption key as password.
    
    Args:
        encrypted_data: The encrypted data as bytes
        encryption_key: The encryption key to use as password
        
    Returns:
        The decrypted data as bytes
    """
    try:
        gpg = gnupg.GPG()
        decrypted_data = gpg.decrypt(encrypted_data, passphrase=encryption_key)
        
        if not decrypted_data.ok:
            raise ValueError(f"Decryption failed: {decrypted_data.status}")
        
        return decrypted_data.data
        
    except Exception as e:
        raise ValueError(f"Failed to decrypt user data: {str(e)}")
