"""
Simplified cryptographic service for key derivation only.
Based on the original crypto_service.py but stripped down for the key derivation server.
"""

import hashlib
import logging
from typing import NamedTuple
from bip_utils import (
    Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes,
    Bip39MnemonicValidator, Bip39Languages
)

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


class CryptoService:
    """
    Simplified service for BIP44 key derivation only.
    """

    def __init__(self):
        """Initialize the crypto service."""
        pass

    def _get_language_enum(self, language_str: str) -> Bip39Languages:
        """
        Convert language string to Bip39Languages enum.
        
        Args:
            language_str: Language name (e.g., "english")
            
        Returns:
            Bip39Languages enum value
            
        Raises:
            KeyDerivationError: If language is not supported
        """
        try:
            return getattr(Bip39Languages, language_str.upper())
        except AttributeError:
            raise KeyDerivationError(
                f"Unsupported language: {language_str}",
                details={"supported_languages": ["english", "french", "japanese", "spanish"]}
            )

    def derive_ethereum_keys_for_dlp(self, mnemonic: str, index: int, language_str: str = "english") -> CryptoKeys:
        """
        Derive Ethereum keys for DLP using BIP44 standard.
        
        Args:
            mnemonic: BIP39 mnemonic phrase
            index: Address index to derive
            language_str: Mnemonic language
            
        Returns:
            CryptoKeys with derived keys
            
        Raises:
            KeyDerivationError: If key derivation fails
        """
        if index < 0:
            raise KeyDerivationError(
                "Address index cannot be negative",
                details={"index": index}
            )

        try:
            # Validate language
            language_enum = self._get_language_enum(language_str)
            
            # Validate mnemonic
            Bip39MnemonicValidator(language_enum).Validate(mnemonic)
            
            # Generate seed
            seed_bytes = Bip39SeedGenerator(mnemonic, language_enum).Generate("")
            logger.info("Seed bytes generated from mnemonic")
            
            # Create BIP44 object for Ethereum derivation
            bip44_mst_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM)
            
            # Derive the specific address index (m/44'/60'/0'/0/index)
            bip44_addr_ctx = bip44_mst_ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(index)
            
            # Get keys and address
            private_key_hex = bip44_addr_ctx.PrivateKey().Raw().ToHex()
            public_key_hex = bip44_addr_ctx.PublicKey().RawUncompressed().ToHex()  # Uncompressed
            address = bip44_addr_ctx.PublicKey().ToAddress()
            
            logger.info(f"Successfully derived keys for index {index}: Address={address}")
            
            return CryptoKeys(
                private_key_hex=private_key_hex,
                public_key_hex=public_key_hex,
                address=address,
                derivation_index=index
            )
            
        except Exception as e:
            raise KeyDerivationError(
                f"Failed to derive Ethereum keys: {e}",
                details={"index": index, "language": language_str, "underlying_error": str(e)}
            ) 