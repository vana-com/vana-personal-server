"""
FastMCP authentication provider for EIP-191 signature validation.

This provider validates Ethereum signatures from the Authorization header
and extracts the wallet address for use in MCP tools and resources.
"""

import logging
from fastmcp.server.auth import TokenVerifier, AccessToken
from eth_account import Account
from eth_account.messages import encode_defunct

logger = logging.getLogger(__name__)

AUTH_MESSAGE = "Vana Personal Server Auth Key"


class SignatureAuthProvider(TokenVerifier):
    """
    FastMCP auth provider for EIP-191 signature validation.

    Inherits from TokenVerifier (recommended by FastMCP for simple token validation).
    FastMCP automatically extracts token from "Authorization: Bearer <token>" header
    and passes it to verify_token() WITHOUT the "Bearer " prefix.

    Supports HTTP mode authentication. Stdio mode does not invoke auth provider.
    """


    async def verify_token(self, token: str) -> AccessToken | None:
        """
        Verify EIP-191 signature and return AccessToken.

        Args:
            token: Signature string (0x-prefixed hex) from Authorization header.
                   FastMCP extracts this from "Authorization: Bearer <token>"
                   and passes it WITHOUT the "Bearer " prefix.

        Returns:
            AccessToken with wallet address in claims, or None if invalid.
        """
        try:
            # Token is already extracted by FastMCP (no "Bearer " prefix)
            # Validate signature cryptographically using EIP-191
            encoded_message = encode_defunct(text=AUTH_MESSAGE)
            recovered_address = Account.recover_message(
                encoded_message,
                signature=token
            )

            wallet_address = recovered_address.lower()
            logger.info(f"Authenticated wallet: {wallet_address}")

            # Return AccessToken with all required fields
            return AccessToken(
                token=token,                    # Original signature
                client_id=wallet_address,       # Use wallet as client ID
                scopes=["read", "write"],       # Grant all scopes for authenticated users
                expires_at=None,                # Signatures don't expire (static message)
                resource=None,                  # Optional RFC 8707 resource indicator
                claims={"sub": wallet_address}  # Standard "subject" claim with wallet
            )

        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return None

