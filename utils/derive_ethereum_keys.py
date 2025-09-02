"""
Simplified cryptographic service for key derivation only.
Based on the original crypto_service.py but stripped down for the key derivation server.
"""

import logging
from typing import NamedTuple
from eth_account import Account

logger = logging.getLogger(__name__)


class CryptoKeys(NamedTuple):
    """Simple container for derived cryptographic keys."""

    private_key_hex: str
    public_key_hex: str
    address: str
    derivation_index: int


class KeyDerivationError(Exception):
    """Exception raised when key derivation fails."""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


def derive_ethereum_keys(
    mnemonic: str, index: int, language_str: str = "english"
) -> CryptoKeys:
    """
    Derive Ethereum keys for DLP using BIP44 standard.
    
    Returns public key in SEC1 uncompressed format (65 bytes with 0x04 prefix)
    for compatibility with Vana SDK.

    Args:
        mnemonic: BIP39 mnemonic phrase
        index: Address index to derive
        language_str: Mnemonic language (not used with hdwallet)

    Returns:
        CryptoKeys with derived keys

    Raises:
        KeyDerivationError: If key derivation fails
    """
    if index < 0:
        raise KeyDerivationError(
            "Address index cannot be negative", details={"index": index}
        )

    try:
        # Enable HD wallet features in eth-account
        Account.enable_unaudited_hdwallet_features()

        # Derivation path for Ethereum (BIP44)
        derivation_path = f"m/44'/60'/0'/0/{index}"

        # Generate account from mnemonic and derivation path
        acct = Account.from_mnemonic(mnemonic, account_path=derivation_path)

        # Ensure private key has 0x prefix for consistency
        private_key_hex = "0x" + acct.key.hex()
        
        # Get uncompressed SEC1 format (65 bytes with 0x04 prefix)
        # This is what Vana SDK expects
        public_key_raw = acct._key_obj.public_key.to_bytes()
        public_key_hex = "0x04" + public_key_raw.hex()
        
        address = acct.address

        return CryptoKeys(
            private_key_hex=private_key_hex,
            public_key_hex=public_key_hex,
            address=address,
            derivation_index=index,
        )
    except Exception as e:
        raise KeyDerivationError(
            f"Failed to derive Ethereum keys: {e}",
            details={
                "index": index,
                "language": language_str,
                "underlying_error": str(e),
            },
        )
