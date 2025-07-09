import logging
import os
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)

TEST_MNEMONIC = "shoe pass menu sniff phrase despair corn phone then rotate sheriff drop"

class IdentityServer:
    """
    Server for deterministically deriving keys for user servers based on user identity.
    Uses the existing crypto_service.py for BIP44 key derivation.
    """
    
    def __init__(self):
        self.mnemonic = os.getenv("VANA_MNEMONIC", TEST_MNEMONIC)
        self.language = os.getenv("MNEMONIC_LANGUAGE", "english")
    
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
        digest = hashlib.sha256(user_address.lower().encode()).digest()
        return int.from_bytes(digest[:4], 'big') % (2**31)
    

    
    def derive_user_server_address(self, user_address: str) -> Dict[str, Any]:
        """
        Derive the deterministic address and public key for a user's server based on their address.
        This is the address that will be stored in the smart contract.
        
        Args:
            user_address: User's Ethereum address
            
        Returns:
            Dictionary containing the derived address and public key for the user's server
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
            crypto_keys = crypto_service.derive_ethereum_keys(
                self.mnemonic, derivation_index, self.language
            )
            
            logger.info(f"Successfully derived address for user {user_address}: {crypto_keys.address}")
            
            return {
                "address": crypto_keys.address,
                "public_key": crypto_keys.public_key_hex
            }
            
        except Exception as e:
            logger.error(f"Failed to derive address for user {user_address}: {e}")
            raise ValueError(f"Address derivation failed: {str(e)}") 