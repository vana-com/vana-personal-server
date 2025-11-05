"""
MCP Server implementation for the Vana Personal Server.
"""

import logging
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from mcp_server.auth_provider import SignatureAuthProvider

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "Vana Personal Server",
    auth=SignatureAuthProvider()
)


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool()
async def add_numbers(a: float, b: float) -> dict:
    """
    Add two numbers together.

    This is a simple example tool to verify MCP functionality.

    Args:
        a: First number
        b: Second number

    Returns:
        Dictionary with result and metadata
    """
    result = a + b
    logger.info(f"add_numbers called: {a} + {b} = {result}")

    return {
        "result": result,
        "message": f"Successfully added {a} + {b}",
        "operation": "addition"
    }


@mcp.tool()
async def whoami() -> dict:
    """
    Return authenticated wallet address.

    This tool tests that authentication is working correctly by
    returning the wallet address extracted from the signature.

    Returns:
        Dictionary with wallet address and auth status
    """
    access_token = get_access_token()

    if access_token is None:
        return {
            "authenticated": False,
            "wallet_address": None,
            "message": "Not authenticated (stdio mode or missing auth)"
        }

    wallet_address = access_token.claims.get("sub")
    logger.info(f"Authenticated wallet from token: {wallet_address}")

    return {
        "authenticated": True,
        "wallet_address": wallet_address,
        "message": f"Authenticated as {wallet_address}"
    }