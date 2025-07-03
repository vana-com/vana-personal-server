import logging
import os
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)

class KeyDerivationServer:
    """
    Server for deterministically deriving keys for user servers based on user identity.
    Uses the existing crypto_service.py for BIP44 key derivation.
    """
    
    def __init__(self):
        self.mnemonic = os.getenv("VANA_MNEMONIC")
        self.language = os.getenv("MNEMONIC_LANGUAGE", "english")
        
        if not self.mnemonic:
            raise ValueError("VANA_MNEMONIC environment variable must be set")
    
    def _user_identity_to_index(self, user_address: str) -> int:
        """
        Convert user address to deterministic index for key derivation.
        Uses the same logic as crypto_service.py dlp_identity_to_index method.
        
        Args:
            user_address: User's Ethereum address
            
        Returns:
            Deterministic index for the user
        """
        import hashlib
        if not isinstance(user_address, str):
            user_address = str(user_address)
        digest = hashlib.sha256(user_address.lower().encode()).digest()
        return int.from_bytes(digest[:4], 'big') % (2**31)
    
    def derive_user_server_keys(self, user_address: str) -> Dict[str, Any]:
        """
        Derive deterministic keys for a user's server based on their address.
        Uses the existing crypto_service.py derive_ethereum_keys_for_dlp method.
        
        Args:
            user_address: User's Ethereum address
            
        Returns:
            Dictionary containing derived keys and metadata
        """
        try:
            # Validate inputs
            if not user_address or not user_address.startswith('0x'):
                raise ValueError("Invalid user address format")
            
            # Convert user address to deterministic index
            derivation_index = self._user_identity_to_index(user_address)
            logger.info(f"Derived index {derivation_index} for user {user_address}")
            
            # Import and use the existing crypto service
            from crypto_service import CryptoService
            crypto_service = CryptoService()
            
            # Use the existing method to derive keys
            crypto_keys = crypto_service.derive_ethereum_keys_for_dlp(
                self.mnemonic, derivation_index, self.language
            )
            
            logger.info(f"Successfully derived keys for user {user_address}: Address={crypto_keys.address}")
            
            return {
                "user_address": user_address,
                "derivation_index": derivation_index,
                "private_key_hex": crypto_keys.private_key_hex,
                "public_key_hex": crypto_keys.public_key_hex,
                "derived_address": crypto_keys.address,
                "derivation_path": f"m/44'/60'/0'/0/{derivation_index}",
                "mnemonic_language": self.language
            }
            
        except Exception as e:
            logger.error(f"Failed to derive keys for user {user_address}: {e}")
            raise ValueError(f"Key derivation failed: {str(e)}") 