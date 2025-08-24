"""
Shared authentication utilities for API endpoints.
"""
import json
import logging
from typing import Dict, Any
from web3 import Web3
from eth_account.messages import encode_defunct
from domain.exceptions import AuthenticationError, ValidationError

logger = logging.getLogger(__name__)


class SignatureAuth:
    """Handles Ethereum signature-based authentication."""
    
    def __init__(self):
        self.web3 = Web3()
    
    def verify_signature(self, request_data: str, signature: str) -> str:
        """
        Verify Ethereum signature and recover signer address.
        
        Args:
            request_data: The signed request data (JSON string)
            signature: The Ethereum signature
            
        Returns:
            The recovered Ethereum address
            
        Raises:
            AuthenticationError: If signature is invalid
            ValidationError: If request data is invalid JSON
        """
        try:
            # Validate JSON format
            json.loads(request_data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"[AUTH] JSON parsing failed: {str(e)}")
            raise ValidationError(
                "Invalid JSON format in request data", "request_data"
            )
        
        try:
            # Recover address from signature
            message = encode_defunct(text=request_data)
            recovered_address = self.web3.eth.account.recover_message(
                message, signature=signature
            )
            
            logger.info(f"[AUTH] Signature verified, recovered address: {recovered_address}")
            return recovered_address
            
        except Exception as e:
            logger.error(f"[AUTH] Signature recovery failed: {str(e)}")
            raise AuthenticationError(
                "Invalid signature or unable to recover address"
            )
    
    def verify_grantee_access(self, recovered_address: str, expected_grantee: str) -> bool:
        """
        Verify that the recovered address matches the expected grantee.
        
        Args:
            recovered_address: Address recovered from signature
            expected_grantee: The expected grantee address
            
        Returns:
            True if addresses match, False otherwise
        """
        if recovered_address.lower() != expected_grantee.lower():
            logger.error(f"[AUTH] Address mismatch: recovered {recovered_address}, expected {expected_grantee}")
            return False
        
        logger.info(f"[AUTH] Grantee access verified: {recovered_address}")
        return True


class MockModeAuth:
    """Authentication handler that respects mock mode settings."""
    
    def __init__(self):
        self.signature_auth = SignatureAuth()
        self._settings = None
    
    @property
    def settings(self):
        """Lazy load settings to avoid circular imports."""
        if self._settings is None:
            from settings import get_settings
            self._settings = get_settings()
        return self._settings
    
    def verify_signature_with_mock(self, request_data: str, signature: str) -> str:
        """
        Verify signature in production, return mock address in mock mode.
        
        Args:
            request_data: The signed request data (JSON string)
            signature: The Ethereum signature
            
        Returns:
            The recovered or mock Ethereum address
        """
        if self.settings.mock_mode:
            logger.info("[AUTH] Mock mode: bypassing signature verification")
            return "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"  # Mock address
        
        return self.signature_auth.verify_signature(request_data, signature)
    
    def require_production_mode(self) -> None:
        """
        Raise an error if not in production mode.
        
        Raises:
            AuthenticationError: If in mock mode
        """
        if self.settings.mock_mode:
            raise AuthenticationError(
                "This endpoint requires production mode. Set MOCK_MODE=false."
            )
    
    def is_mock_mode(self) -> bool:
        """Check if running in mock mode."""
        return self.settings.mock_mode


# Shared instances
signature_auth = SignatureAuth()
mock_mode_auth = MockModeAuth()