"""
Subgraph service for querying blockchain data via vanagraph.io GraphQL API.

This service provides methods to:
- List files with filtering and pagination
- Get file metadata
- List and search schemas
- Get schema definitions

All methods return structured data that matches the MCP resource/tool specifications.
"""

import asyncio
import logging
from typing import Optional
import httpx
from settings import settings
from utils.ipfs import fetch_json_with_fallbacks, IPFSError
from domain.exceptions import (
    SubgraphQueryError,
    SubgraphConnectionError,
    SubgraphOwnerMismatchError,
    NotFoundError,
)
from domain.subgraph_types import (
    SubgraphFileMetadata,
    SubgraphFileListResponse,
    SubgraphSchemaInfo,
    SubgraphSchemaListResponse,
    SubgraphSchemaDefinition,
    parse_file_metadata,
    parse_schema_info,
)

logger = logging.getLogger(__name__)


class SubgraphClient:
    """Client for querying the Vana subgraph via GraphQL."""

    def __init__(self, subgraph_url: Optional[str] = None):
        """
        Initialize the subgraph client.

        Args:
            subgraph_url: GraphQL endpoint URL. Defaults to settings.subgraph_url
        """
        self.subgraph_url = subgraph_url or settings.subgraph_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def _query(self, query: str, variables: Optional[dict] = None) -> dict:
        """
        Execute a GraphQL query against the subgraph.

        Args:
            query: GraphQL query string
            variables: Optional query variables

        Returns:
            GraphQL response data

        Raises:
            SubgraphQueryError: If GraphQL errors are present in response
            SubgraphConnectionError: If connection to subgraph fails
        """
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        try:
            response = await self.client.post(
                self.subgraph_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise SubgraphConnectionError(
                f"HTTP error from subgraph: {str(e)}",
                url=self.subgraph_url
            ) from e
        except httpx.RequestError as e:
            raise SubgraphConnectionError(
                f"Failed to connect to subgraph: {str(e)}",
                url=self.subgraph_url
            ) from e
        
        data = response.json()
        
        # Check for GraphQL errors
        if "errors" in data:
            error_messages = [e.get("message", str(e)) for e in data["errors"]]
            raise SubgraphQueryError(
                f"GraphQL errors: {', '.join(error_messages)}",
                query=query,
                variables=variables
            )
        
        return data.get("data", {})

    async def list_files(
        self,
        owner_address: str,
        schema_ids: Optional[list[int]] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> SubgraphFileListResponse:
        """
        List files owned by a user with optional schema filtering.

        Args:
            owner_address: Wallet address of the file owner
            schema_ids: Optional list of schema IDs to filter by
            limit: Maximum number of results (default: 10, max: 100)
            offset: Starting position for pagination (default: 0)

        Returns:
            SubgraphFileListResponse with files, limit, and offset
        """
        # Normalize owner address
        owner_address = owner_address.lower()
        
        # Build variables for GraphQL query
        variables = {
            "owner": owner_address,
            "limit": min(limit, 100),  # Max 100 per The Graph
            "skip": offset,
        }
        
        if schema_ids and len(schema_ids) > 0:
            # Convert int list to string list for GraphQL BigInt
            variables["schemaIds"] = [str(sid) for sid in schema_ids]
        
        # Build GraphQL query - use different queries based on whether schema_ids is provided
        if schema_ids and len(schema_ids) > 0:
            query = """
            query ListFiles($owner: String!, $schemaIds: [BigInt!], $limit: Int!, $skip: Int!) {
              files(
                where: {
                  owner: $owner
                  schemaId_gt: "0"
                  schemaId_in: $schemaIds
                }
                first: $limit
                skip: $skip
                orderBy: addedAtTimestamp
                orderDirection: desc
              ) {
                id
                owner {
                  id
                }
                url
                schemaId
                addedAtTimestamp
              }
            }
            """
        else:
            query = """
            query ListFiles($owner: String!, $limit: Int!, $skip: Int!) {
              files(
                where: {
                  owner: $owner
                  schemaId_gt: "0"
                }
                first: $limit
                skip: $skip
                orderBy: addedAtTimestamp
                orderDirection: desc
              ) {
                id
                owner {
                  id
                }
                url
                schemaId
                addedAtTimestamp
              }
            }
            """
        
        try:
            data = await self._query(query, variables)
            files_data = data.get("files", [])
            
            files = [parse_file_metadata(f) for f in files_data]
            
            return SubgraphFileListResponse(
                files=files,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            logger.error(f"Error listing files for owner {owner_address}: {e}")
            raise

    async def get_file_metadata(self, file_id: int, owner_address: str) -> Optional[SubgraphFileMetadata]:
        """
        Get metadata for a specific file.

        Args:
            file_id: The file ID to retrieve
            owner_address: Wallet address of the file owner (for access validation)

        Returns:
            SubgraphFileMetadata or None if file not found or user doesn't have access

        Raises:
            SubgraphQueryError: If GraphQL query fails
            SubgraphConnectionError: If connection to subgraph fails
            SubgraphOwnerMismatchError: If file owner doesn't match requested owner
        """
        # Normalize owner address
        owner_address = owner_address.lower()
        
        query = """
        query GetFile($id: ID!) {
          file(id: $id) {
            id
            owner {
              id
            }
            url
            schemaId
            addedAtTimestamp
            addedAtBlock
            transactionHash
          }
        }
        """
        
        variables = {
            "id": str(file_id)
        }
        
        try:
            data = await self._query(query, variables)
            file_data = data.get("file")
            
            if not file_data:
                return None
            
            # Validate owner matches
            file_owner = file_data["owner"]["id"].lower()
            if file_owner != owner_address:
                raise SubgraphOwnerMismatchError(
                    file_id=file_id,
                    expected_owner=owner_address,
                    actual_owner=file_owner
                )
            
            return parse_file_metadata(file_data)
        except (SubgraphQueryError, SubgraphConnectionError, SubgraphOwnerMismatchError):
            raise
        except Exception as e:
            logger.error(f"Error getting file metadata for file {file_id}: {e}")
            return None

    async def list_schemas(
        self,
        query: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> SubgraphSchemaListResponse:
        """
        List all available schemas with optional keyword search.

        Args:
            query: Optional keyword to search in schema name and description
            limit: Maximum number of results (default: 10, max: 100)
            offset: Starting position for pagination (default: 0)

        Returns:
            SubgraphSchemaListResponse with schemas, limit, and offset
        """
        variables = {
            "limit": min(limit, 100),  # Max 100 per The Graph
            "skip": offset,
        }
        
        # Build query with or without search
        if query and query.strip():
            graphql_query = """
            query ListSchemas($query: String!, $limit: Int!, $skip: Int!) {
              schemas(
                where: { name_contains_nocase: $query }
                first: $limit
                skip: $skip
                orderBy: createdAt
                orderDirection: desc
              ) {
                id
                name
                dialect
                definitionUrl
                createdAt
              }
            }
            """
            variables["query"] = query.strip()
        else:
            graphql_query = """
            query ListSchemas($limit: Int!, $skip: Int!) {
              schemas(
                first: $limit
                skip: $skip
                orderBy: createdAt
                orderDirection: desc
              ) {
                id
                name
                dialect
                definitionUrl
                createdAt
              }
            }
            """
        
        try:
            data = await self._query(graphql_query, variables)
            schemas_data = data.get("schemas", [])
            
            schemas = [parse_schema_info(s) for s in schemas_data]
            
            return SubgraphSchemaListResponse(
                schemas=schemas,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            logger.error(f"Error listing schemas: {e}")
            raise

    async def get_schema(self, schema_id: int) -> Optional[SubgraphSchemaDefinition]:
        """
        Get schema definition by ID.

        Args:
            schema_id: The schema ID to retrieve

        Returns:
            SubgraphSchemaDefinition or None if schema not found
        """
        # Step 1: Query subgraph for schema metadata
        query = """
        query GetSchema($id: ID!) {
          schema(id: $id) {
            id
            name
            dialect
            definitionUrl
            createdAt
            createdAtBlock
            createdTxHash
          }
        }
        """
        
        variables = {
            "id": str(schema_id)
        }
        
        try:
            data = await self._query(query, variables)
            schema_data = data.get("schema")
            
            if not schema_data:
                return None
            
            # Step 2: Fetch schema definition from IPFS
            ipfs_url = schema_data["definitionUrl"]
            ipfs_data = await self._fetch_ipfs_schema(ipfs_url)
            
            if not ipfs_data:
                # Return partial data if IPFS fetch fails
                logger.warning(f"Failed to fetch IPFS schema from {ipfs_url}")
                return SubgraphSchemaDefinition(
                    schema_id=int(schema_data["id"]),
                    name=schema_data["name"],
                    version="unknown",
                    description="",
                    ipfs_url=ipfs_url,
                    schema={}
                )
            
            return SubgraphSchemaDefinition(
                schema_id=int(schema_data["id"]),
                name=schema_data["name"],
                version=ipfs_data.get("version", "unknown"),
                description=ipfs_data.get("description", ""),
                ipfs_url=ipfs_url,
                schema=ipfs_data.get("schema", {})
            )
        except Exception as e:
            logger.error(f"Error getting schema {schema_id}: {e}")
            return None
    
    async def _fetch_ipfs_schema(self, ipfs_url: str) -> Optional[dict]:
        """
        Fetch schema definition from IPFS using existing utilities.

        Args:
            ipfs_url: IPFS URL (e.g., "ipfs://bafkreigq6...")

        Returns:
            Parsed schema definition or None if fetch fails
        """
        try:
            # Run synchronous IPFS fetch in executor
            loop = asyncio.get_event_loop()
            ipfs_data = await loop.run_in_executor(
                None,
                fetch_json_with_fallbacks,
                ipfs_url,
                10  # timeout
            )
            return ipfs_data
        except IPFSError as e:
            logger.error(f"IPFS error fetching schema from {ipfs_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching IPFS schema from {ipfs_url}: {e}")
            return None


# Singleton instance
_subgraph_client: Optional[SubgraphClient] = None


def get_subgraph_client() -> SubgraphClient:
    """
    Get or create the singleton subgraph client instance.

    Returns:
        SubgraphClient instance
    """
    global _subgraph_client
    if _subgraph_client is None:
        _subgraph_client = SubgraphClient()
    return _subgraph_client
