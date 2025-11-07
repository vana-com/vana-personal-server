"""
MCP Server implementation for the Vana Personal Server.

This module wires up all MCP components:
- Resources: Direct data access via URIs (files, schemas)
- Tools: Functions for search, filtering, aggregation
- Prompts: Reusable workflow templates
"""

import logging
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from mcp_server.auth_provider import SignatureAuthProvider
from mcp_server import prompts
from mcp_server.resources import get_resource_handler
from mcp_server.tools import get_tool_handler

logger = logging.getLogger(__name__)

# Initialize handlers once at module level
_resource_handler = get_resource_handler()
_tool_handler = get_tool_handler()

mcp = FastMCP(
    "Vana Personal Server",
    auth=SignatureAuthProvider()
)


def _get_wallet_address() -> str:
    """
    Extract wallet address from access token.
    
    Returns:
        Wallet address string
        
    Raises:
        ValueError: If not authenticated or wallet address not found
    """
    access_token = get_access_token()
    if access_token is None:
        raise ValueError("Authentication required. No access token found.")
    
    wallet_address = access_token.claims.get("sub")
    if not wallet_address:
        raise ValueError("Authentication required. No wallet address found in token.")
    
    return wallet_address


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool()
async def list_files(
    schema_ids: list[int] | None = None,
    limit: int = 10,
    offset: int = 0
) -> dict:
    """
    List user's files with optional schema filtering and pagination.

    Args:
        schema_ids: Optional list of schema IDs to filter by
        limit: Number of results per page (default: 10, max: 100)
        offset: Starting position (default: 0)

    Returns:
        Dictionary with files list and pagination info (limit, offset)
    """
    wallet_address = _get_wallet_address()
    return await _tool_handler.list_files(wallet_address, schema_ids, limit, offset)


@mcp.tool()
async def search_files_by_schema(
    query: str,
    limit: int = 10,
    offset: int = 0
) -> dict:
    """
    Discover files by searching schema names/descriptions.

    Args:
        query: Keyword to search in schema title and description (e.g., "chatgpt", "linkedin")
        limit: Number of results (default: 10)
        offset: Starting position (default: 0)

    Returns:
        Dictionary with matching schemas and their associated files
    """
    wallet_address = _get_wallet_address()
    return await _tool_handler.search_files_by_schema(wallet_address, query, limit, offset)


@mcp.tool()
async def get_file(
    file_id: int,
    filter: str | None = None
) -> dict:
    """
    Retrieve decrypted file content with optional filtering.

    LLMs should first read the schema to understand the data structure
    before constructing filters. Filters are optional and should only
    be used for large files to reduce token usage.

    Args:
        file_id: The file ID to retrieve
        filter: Optional JSONPath expression to extract specific data
                Examples: $.messages[0:10], $.data.conversations

    Returns:
        Dictionary with file content, metadata, and filter status
    """
    wallet_address = _get_wallet_address()
    return await _tool_handler.get_file(wallet_address, file_id, filter)


@mcp.tool()
async def get_file_metadata(file_id: int) -> dict:
    """
    Get file metadata without decryption.

    Args:
        file_id: The file ID

    Returns:
        Dictionary with file_id, file_url, schema_id, and date_added
    """
    wallet_address = _get_wallet_address()
    return await _tool_handler.get_file_metadata(wallet_address, file_id)


@mcp.tool()
async def list_schemas(
    query: str | None = None,
    limit: int = 10,
    offset: int = 0
) -> dict:
    """
    List all available schemas with optional keyword search.

    Args:
        query: Optional keyword to filter schemas
        limit: Number of results (default: 10)
        offset: Starting position (default: 0)

    Returns:
        Dictionary with schemas list and pagination info (limit, offset)
    """
    return await _tool_handler.list_schemas(query, limit, offset)


@mcp.tool()
async def get_schema(schema_id: int) -> dict:
    """
    Get schema definition details including name, version, description, and schema structure.

    Args:
        schema_id: The schema ID to retrieve

    Returns:
        Dictionary with schema_id, name, version, description, ipfs_url, and schema structure
    """
    return await _tool_handler.get_schema(schema_id)


# ============================================================================
# MCP Resources
# ============================================================================
# Note: FastMCP resources with parameters only. For list operations (files, schemas),
# use the tools above instead.

@mcp.resource("vana://file/{file_id}")
async def read_file_content(file_id: int) -> str:
    """
    Read file content resource.

    Args:
        file_id: The file ID to retrieve

    Returns:
        Decrypted file content as JSON string
    """
    wallet_address = _get_wallet_address()
    uri = f"vana://file/{file_id}"
    return await _resource_handler.read_file_content_resource(uri, wallet_address)


@mcp.resource("vana://file/{file_id}/metadata")
async def read_file_metadata_resource(file_id: int) -> str:
    """
    Read file metadata resource.

    Args:
        file_id: The file ID

    Returns:
        File metadata as JSON string
    """
    wallet_address = _get_wallet_address()
    uri = f"vana://file/{file_id}/metadata"
    return await _resource_handler.read_file_metadata_resource(uri, wallet_address)


@mcp.resource("vana://schema/{schema_id}")
async def read_schema_resource(schema_id: int) -> str:
    """
    Read schema definition resource.

    Args:
        schema_id: The schema ID

    Returns:
        Schema definition as JSON string
    """
    uri = f"vana://schema/{schema_id}"
    return await _resource_handler.read_schema_resource(uri)


# ============================================================================
# MCP Prompts
# ============================================================================

@mcp.prompt()
async def get_my_data(data_type: str) -> str:
    """
    Get user's data from a specific application or data type.

    Args:
        data_type: Application name or data type (e.g., 'chatgpt', 'linkedin', 'twitter')

    Returns:
        Formatted prompt template for the workflow
    """
    return prompts.GET_MY_DATA_TEMPLATE.format(data_type=data_type)