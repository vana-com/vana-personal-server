"""
MCP Tool handlers for Vana Personal Server.

Tools provide functions for search, filtering, and aggregation:
- list_files: List user's files with optional schema filtering
- search_files_by_schema: Discover files by searching schema names
- get_file: Retrieve decrypted file content with optional filtering
- get_file_metadata: Get file metadata without decryption
- list_schemas: List all available schemas with optional search
- get_schema: Get schema definition details by schema ID
"""

import json
import logging
from typing import Optional

from mcp_server.resources import get_resource_handler

logger = logging.getLogger(__name__)

class ToolHandler:
    """
    Handler for MCP tools with initialized resource handler.
    
    This class uses the singleton ResourceHandler instance to avoid
    repeated initialization of expensive dependencies.
    """
    
    def __init__(self):
        """Initialize tool handler with resource handler."""
        self.resource_handler = get_resource_handler()
    
    async def list_files(
        self,
        wallet_address: str,
        schema_ids: Optional[list[int]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> dict:
        """
        List user's files with optional schema filtering and pagination.

        Args:
            wallet_address: Authenticated wallet address
            schema_ids: Optional list of schema IDs to filter by
            limit: Number of results per page (default: 10, max: 100)
            offset: Starting position (default: 0)

        Returns:
            {
                "files": [
                    {"file_id": 123, "schema_id": 5, "date_added": "2024-01-15", "file_url": "..."}
                ],
                "limit": 10,
                "offset": 0
            }

        Raises:
            ValueError: If schema_id is invalid or parameters are out of range
        """
        # Validate parameters
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        # Build resource URI with parameters
        params = []
        if schema_ids:
            schema_ids_str = ','.join(str(sid) for sid in schema_ids)
            params.append(f"schema_ids={schema_ids_str}")
        params.append(f"limit={limit}")
        params.append(f"offset={offset}")

        uri = f"vana://files?{'&'.join(params)}"
        logger.info(f"[LIST_FILES] uri: {uri}")

        # Read resource
        result_json = await self.resource_handler.read_files_resource(uri, wallet_address)
        result = json.loads(result_json)

        # If no files found, provide helpful error
        if len(result.get('files', [])) == 0 and schema_ids:
            return {
                "error": "empty_result",
                "message": "No files found matching the specified criteria",
                "suggestions": [
                    "Call list_schemas() to discover available data types",
                    "Try searching without schema_ids filter"
                ],
                "files": [],
                "limit": limit,
                "offset": offset
            }

        return result

    async def search_files_by_schema(
        self,
        wallet_address: str,
        query: str,
        limit: int = 10,
        offset: int = 0
    ) -> dict:
        """
        Discover files by searching schema names/descriptions.

        Args:
            wallet_address: Authenticated wallet address
            query: Keyword to search in schema title and description (e.g., "chatgpt", "linkedin")
            limit: Number of results (default: 10)
            offset: Starting position (default: 0)

        Returns:
            {
                "schemas": [{"schema_id": 5, "name": "ChatGPT Conversations", "description": "..."}],
                "files": [{"file_id": 123, "schema_id": 5, "date_added": "2024-01-15"}]
            }

        Raises:
            ValueError: If query is empty or parameters are invalid
        """
        if not query or not query.strip():
            raise ValueError("query parameter is required and cannot be empty")

        # Validate parameters
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        # Step 1: Search schemas (schemas are public, no auth required)
        schemas_uri = f"vana://schemas?query={query}&limit={limit}&offset={offset}"
        schemas_result_json = await self.resource_handler.read_schemas_resource(schemas_uri)
        schemas_result = json.loads(schemas_result_json)

        if len(schemas_result.get('schemas', [])) == 0:
            return {
                "error": "empty_result",
                "message": f"No schemas found matching query: '{query}'",
                "suggestions": [
                    "Call list_schemas() to see all available schemas",
                    "Try a different search term"
                ],
                "schemas": [],
                "files": []
            }

        # Step 2: Get schema IDs
        schema_ids = [schema['schema_id'] for schema in schemas_result['schemas']]

        # Step 3: List files for those schemas
        files_result = await self.list_files(wallet_address, schema_ids=schema_ids, limit=limit, offset=offset)

        # Combine results
        return {
            "schemas": schemas_result['schemas'],
            "files": files_result.get('files', [])
        }

    async def get_file(
        self,
        wallet_address: str,
        file_id: int,
        filter: Optional[str] = None
    ) -> dict:
        """
        Retrieve decrypted file content with optional filtering.

        LLMs should first read the schema (vana://schema/{schema_id}) to understand
        the data structure before constructing filters. Filters are optional and should
        only be used for large files to reduce token usage.

        Args:
            wallet_address: Authenticated wallet address
            file_id: The file ID to retrieve
            filter: Optional JSONPath expression to extract specific data

        Returns:
            {
                "content": "...",  # Full or filtered file content
                "file_id": 123,
                "schema_id": 5,
                "filtered": false  # true if filter was applied
            }

        Raises:
            FileNotFoundError: If file doesn't exist or user lacks access
            DecryptionError: If unable to decrypt file
            ValueError: If JSONPath filter is invalid

        Filter Examples:
            - $.messages[0:10] - First 10 messages
            - $.data.conversations - Specific nested field
            - $[?(@.type=='important')] - Conditional filtering
        """
        # Build resource URI
        uri = f"vana://file/{file_id}"
        if filter:
            uri += f"?filter={filter}"

        logger.info(f"[GET_FILE] uri: {uri}")

        # Read resource
        try:
            content = await self.resource_handler.read_file_content_resource(uri, wallet_address)

            # Get file metadata to include in response
            metadata_uri = f"vana://file/{file_id}/metadata"
            metadata_json = await self.resource_handler.read_file_metadata_resource(metadata_uri, wallet_address)
            metadata = json.loads(metadata_json)

            return {
                "content": content,
                "file_id": file_id,
                "schema_id": metadata.get('schema_id'),
                "filtered": filter is not None
            }

        except Exception as e:
            # Re-raise with context
            raise

    async def get_file_metadata(
        self,
        wallet_address: str,
        file_id: int
    ) -> dict:
        """
        Get file metadata without decryption.

        Args:
            wallet_address: Authenticated wallet address
            file_id: The file ID

        Returns:
            {
                "file_id": 123,
                "file_url": "https://drive.google.com/?id=...",
                "schema_id": 5,
                "date_added": "2024-01-15"
            }

        Raises:
            FileNotFoundError: If file doesn't exist or user lacks access
        """
        # Build resource URI
        uri = f"vana://file/{file_id}/metadata"

        logger.info(f"[GET_FILE_METADATA] uri: {uri}")

        # Read resource
        metadata_json = await self.resource_handler.read_file_metadata_resource(uri, wallet_address)
        return json.loads(metadata_json)

    async def list_schemas(
        self,
        query: Optional[str] = None,
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
            {
                "schemas": [
                    {
                        "schema_id": 5,
                        "name": "ChatGPT Conversations",
                        "description": "Chat history and memories from ChatGPT"
                    }
                ],
                "limit": 10,
                "offset": 0
            }

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate parameters
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        # Build resource URI
        params = []
        if query:
            params.append(f"query={query}")
        params.append(f"limit={limit}")
        params.append(f"offset={offset}")

        uri = f"vana://schemas?{'&'.join(params)}"
        logger.info(f"[LIST_SCHEMAS] uri: {uri}")

        # Read resource (schemas are public, no auth required)
        result_json = await self.resource_handler.read_schemas_resource(uri)
        return json.loads(result_json)

    async def get_schema(
        self,
        schema_id: int
    ) -> dict:
        """
        Get schema definition details including name, version, description, and schema structure.

        Args:
            schema_id: The schema ID to retrieve

        Returns:
            {
                "schema_id": 5,
                "name": "ChatGPT Conversations",
                "version": "1.0.0",
                "description": "Chat history and memories from ChatGPT",
                "ipfs_url": "ipfs://...",
                "schema": {
                    "type": "object",
                    "properties": {...}
                }
            }

        Raises:
            ValueError: If schema_id is invalid or schema not found
        """
        # Build resource URI
        uri = f"vana://schema/{schema_id}"
        logger.info(f"[GET_SCHEMA] uri: {uri}")

        # Read resource (schemas are public, no auth required)
        result_json = await self.resource_handler.read_schema_resource(uri)
        return json.loads(result_json)


# Singleton instance
_tool_handler: Optional[ToolHandler] = None


def get_tool_handler() -> ToolHandler:
    """
    Get or create the singleton tool handler instance.
    
    Returns:
        ToolHandler instance
    """
    global _tool_handler
    if _tool_handler is None:
        _tool_handler = ToolHandler()
    return _tool_handler
