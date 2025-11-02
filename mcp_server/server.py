"""
MCP Server implementation for the Vana Personal Server.
"""

import logging
from fastmcp import FastMCP, Context
from fastapi import Request
from eth_account import Account
from eth_account.messages import encode_defunct

logger = logging.getLogger(__name__)

mcp = FastMCP("Vana Personal Server")

# Static authentication message
AUTH_MESSAGE = "Vana Personal Server Auth Key"


# ============================================================================
# Authentication Middleware (for HTTP mode only)
# ============================================================================

async def mcp_auth_middleware(request: Request, call_next):
    """
    Authentication middleware for HTTP transport.

    For stdio mode, this middleware is not used (stdio is trusted local process).
    For HTTP mode (streamable HTTP transport), validates EIP-191 signatures.

    Expected headers:
    - X-Signature: Ethereum signature (0x-prefixed hex) for AUTH_MESSAGE

    The wallet address is derived from the signature, not provided by the client.
    """
    signature = request.headers.get("X-Signature")
    request.state.authenticated = False
    request.state.wallet_address = None

    if signature:
        try:
            encoded_message = encode_defunct(text=AUTH_MESSAGE)
            recovered_address = Account.recover_message(
                encoded_message,
                signature=signature
            )
            request.state.authenticated = True
            request.state.wallet_address = recovered_address.lower()
            logger.info(f"Authenticated wallet: {recovered_address}")

        except Exception as e:
            logger.error(f"Authentication error: {e}")

    response = await call_next(request)
    return response


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


# ============================================================================
# Transport Functions
# ============================================================================

def run_stdio():
    """
    Run MCP server in stdio mode (blocking).

    Used for local MCP access.
    """
    mcp.run(transport="stdio")


def run_http(port: int = 3000):
    """
    Run MCP server in Streamable HTTP mode (blocking).

    This runs the MCP server on a separate port from the REST API.
    For Cloud Run deployment, this should run in a separate container/service
    or on a different port.

    Args:
        port: Port to run MCP HTTP server on (default 3000)
    """
    mcp.run(transport="http", host="0.0.0.0", port=port)
