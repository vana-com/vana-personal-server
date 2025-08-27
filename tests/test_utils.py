"""
Test utilities for creating valid test data using real blockchain information.
"""

import json
from eth_account import Account
from eth_account.messages import encode_defunct

# Real blockchain data from Moksha testnet
REAL_PERMISSION_ID = 8
REAL_GRANTEE_ADDRESS = "0x2AC93684679a5bdA03C6160def908CdB8D46792f"
REAL_GRANTEE_PRIVATE_KEY = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"  # Placeholder - you need the real private key

def create_real_test_signature(message: str, private_key: str = None) -> str:
    """
    Create a valid test signature for a given message.
    
    Args:
        message: The message to sign
        private_key: Private key to use (generates one if not provided)
        
    Returns:
        Valid signature string
    """
    if private_key is None:
        # Generate a test private key
        account = Account.create()
        private_key = account.key.hex()
    
    # Create the message hash
    message_hash = encode_defunct(text=message)
    
    # Sign the message
    signed_message = Account.from_key(private_key).sign_message(message_hash)
    
    return signed_message.signature.hex()

def create_real_operation_request(permission_id: int = REAL_PERMISSION_ID) -> dict:
    """
    Create a valid test operation request with proper signature.
    
    Args:
        permission_id: The permission ID to use (defaults to real permission 8)
        
    Returns:
        Dict with app_signature and operation_request_json
    """
    # Create the operation request JSON
    operation_json = json.dumps({"permission_id": permission_id})
    
    # Create a valid signature for this JSON
    signature = create_real_test_signature(operation_json)
    
    return {
        "app_signature": signature,
        "operation_request_json": operation_json
    }

def create_real_operation_request_with_real_key(permission_id: int = REAL_PERMISSION_ID) -> dict:
    """
    Create a test operation request using the real grantee's private key.
    NOTE: This requires the actual private key for address 0x2AC93684679a5bdA03C6160def908CdB8D46792f
    
    Args:
        permission_id: The permission ID to use (defaults to real permission 8)
        
    Returns:
        Dict with app_signature and operation_request_json
    """
    # Create the operation request JSON
    operation_json = json.dumps({"permission_id": permission_id})
    
    # Use the real grantee's private key if available
    if REAL_GRANTEE_PRIVATE_KEY.startswith("0x1234567890abcdef"):
        print("⚠️  WARNING: Using placeholder private key. Replace REAL_GRANTEE_PRIVATE_KEY with actual key.")
        print(f"   Expected address: {REAL_GRANTEE_ADDRESS}")
        print("   Get the private key from the wallet that controls this address.")
    
    # Create a valid signature for this JSON
    signature = create_real_test_signature(operation_json, REAL_GRANTEE_PRIVATE_KEY)
    
    return {
        "app_signature": signature,
        "operation_request_json": operation_json
    }

def get_test_private_key() -> str:
    """Get a consistent test private key for testing."""
    # Use a deterministic test key
    return "0x" + "1" * 64  # 32 bytes of 1s

def get_test_address() -> str:
    """Get the address corresponding to the test private key."""
    account = Account.from_key(get_test_private_key())
    return account.address

def get_real_blockchain_data() -> dict:
    """
    Get real blockchain data for testing.
    
    Returns:
        Dict containing real permission and grantee information
    """
    return {
        "permission_id": REAL_PERMISSION_ID,
        "grantee_address": REAL_GRANTEE_ADDRESS,
        "grantor_address": "0xD867102a1955046F3190c89c48D9f0CE79D6Bda7",
        "grant_url": "https://grantUrl.xyz",  # From permission 7
        "file_ids": [1654817],  # From permission 8
        "chain_id": 14800,  # Moksha testnet
        "rpc_url": "https://rpc.moksha.vana.org"
    }
