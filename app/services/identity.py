import logging
from typing import Dict, Any
from domain.value_objects import PersonalServer
from dataclasses import dataclass
from utils.derive_ethereum_keys import derive_ethereum_keys
from settings import get_settings
from domain.exceptions import ValidationError, OperationError

logger = logging.getLogger(__name__)

@dataclass
class IdentityResponse:
    user_address: str
    personal_server: PersonalServer

class IdentityService:
    """
    Server for deterministically deriving keys for user servers based on user identity.
    Uses the existing crypto_service.py for BIP44 key derivation.
    """

    def derive_server_identity(self, user_address: str) -> IdentityResponse:
        """
        Derive the deterministic address and public key for a user's server based on their address.
        This is the address that will be stored in the smart contract.

        Args:
            user_address: User's Ethereum address

        Returns:
            IdentityResponse containing the derived address and public key for the user's server
        """
        try:
            # Validate inputs
            if not user_address or not user_address.startswith("0x"):
                raise ValidationError("Invalid user address format", "user_address")

            # Convert user address to deterministic index
            derivation_index = self._user_identity_to_index(user_address)
            logger.info(f"Derived index {derivation_index} (type: {type(derivation_index)}) for user {user_address}")

            # Use the existing method to derive keys
            settings = get_settings()
            crypto_keys = derive_ethereum_keys(
                settings.wallet_mnemonic, derivation_index, settings.mnemonic_language
            )

            logger.info(
                f"Successfully derived address for user {user_address}: {crypto_keys.address}"
            )

            personal_server = PersonalServer(
                address=crypto_keys.address,
                public_key=crypto_keys.public_key_hex
            )

            return IdentityResponse(
                user_address=user_address,
                personal_server=personal_server
            )

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to derive address for user {user_address}: {e}")
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"Exception args: {e.args}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise OperationError(f"Address derivation failed: {str(e)}")

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
        return int.from_bytes(digest[:4], "big") % (2**31)