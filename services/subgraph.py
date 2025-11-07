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
from graphql_query import Operation, Query, Argument, Variable, Field
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
        owner_address = owner_address.lower()
        
        limit_val = min(limit, 100)  # Max 100 per The Graph
        
        owner_var = Variable(name="owner", type="String!")
        limit_var = Variable(name="limit", type="Int!")
        skip_var = Variable(name="skip", type="Int!")
        
        variables_list = [owner_var, limit_var, skip_var]
        variables_dict = {
            "owner": owner_address,
            "limit": limit_val,
            "skip": offset,
        }
        
        # Build where clause as GraphQL object literal
        where_clause_parts = [
            "owner: $owner",
            'schemaId_gt: "0"',
        ]
        
        if schema_ids and len(schema_ids) > 0:
            schema_ids_var = Variable(name="schemaIds", type="[BigInt!]")
            variables_list.append(schema_ids_var)
            variables_dict["schemaIds"] = [str(sid) for sid in schema_ids]
            where_clause_parts.append("schemaId_in: $schemaIds")
        
        where_clause = "{" + ", ".join(where_clause_parts) + "}"
        
        files_args = [
            Argument(name="where", value=where_clause),
            Argument(name="first", value="$limit"),
            Argument(name="skip", value="$skip"),
            Argument(name="orderBy", value="addedAtTimestamp"),
            Argument(name="orderDirection", value="desc"),
        ]
        
        owner_field = Field(name="owner", fields=["id"])
        files_fields = [
            "id",
            owner_field,
            "url",
            "schemaId",
            "addedAtTimestamp",
        ]
        
        files_query = Query(
            name="files",
            arguments=files_args,
            fields=files_fields
        )
        
        operation = Operation(
            type="query",
            name="ListFiles",
            variables=variables_list,
            queries=[files_query]
        )
        
        query = operation.render()
        
        try:
            data = await self._query(query, variables_dict)
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
        owner_address = owner_address.lower()
        
        id_var = Variable(name="id", type="ID!")
        variables_list = [id_var]
        variables_dict = {
            "id": str(file_id)
        }
        
        file_args = [
            Argument(name="id", value="$id")
        ]
        
        owner_field = Field(name="owner", fields=["id"])
        file_fields = [
            "id",
            owner_field,
            "url",
            "schemaId",
            "addedAtTimestamp",
            "addedAtBlock",
            "transactionHash",
        ]
        
        file_query = Query(
            name="file",
            arguments=file_args,
            fields=file_fields
        )
        
        operation = Operation(
            type="query",
            name="GetFile",
            variables=variables_list,
            queries=[file_query]
        )
        
        query = operation.render()
        
        try:
            data = await self._query(query, variables_dict)
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
        dialect: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> SubgraphSchemaListResponse:
        """
        List all available schemas with optional keyword search and dialect filtering.

        Args:
            query: Optional keyword to search in schema name and description
            dialect: Optional dialect filter (e.g., "json")
            limit: Maximum number of results (default: 10, max: 100)
            offset: Starting position for pagination (default: 0)

        Returns:
            SubgraphSchemaListResponse with schemas, limit, and offset
        """
        limit_val = min(limit, 100)  # Max 100 per The Graph
        
        limit_var = Variable(name="limit", type="Int!")
        skip_var = Variable(name="skip", type="Int!")
        variables_list = [limit_var, skip_var]
        variables_dict = {
            "limit": limit_val,
            "skip": offset,
        }
        
        where_clause_parts = []
        if query and query.strip():
            query_var = Variable(name="query", type="String!")
            variables_list.append(query_var)
            variables_dict["query"] = query.strip()
            where_clause_parts.append("name_contains_nocase: $query")
        
        if dialect:
            dialect_var = Variable(name="dialect", type="String!")
            variables_list.append(dialect_var)
            variables_dict["dialect"] = dialect
            where_clause_parts.append("dialect: $dialect")
        
        schemas_args = []
        if where_clause_parts:
            where_clause = "{" + ", ".join(where_clause_parts) + "}"
            schemas_args.append(Argument(name="where", value=where_clause))
        
        schemas_args.extend([
            Argument(name="first", value="$limit"),
            Argument(name="skip", value="$skip"),
            Argument(name="orderBy", value="createdAt"),
            Argument(name="orderDirection", value="desc"),
        ])
        
        schema_fields = [
            "id",
            "name",
            "dialect",
            "definitionUrl",
            "createdAt",
        ]
        
        schemas_query = Query(
            name="schemas",
            arguments=schemas_args,
            fields=schema_fields
        )
        
        operation = Operation(
            type="query",
            name="ListSchemas",
            variables=variables_list,
            queries=[schemas_query]
        )
        
        graphql_query = operation.render()
        
        try:
            data = await self._query(graphql_query, variables_dict)
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
        id_var = Variable(name="id", type="ID!")
        variables_list = [id_var]
        variables_dict = {
            "id": str(schema_id)
        }
        
        schema_args = [
            Argument(name="id", value="$id")
        ]
        
        schema_fields = [
            "id",
            "name",
            "dialect",
            "definitionUrl",
            "createdAt",
            "createdAtBlock",
            "createdTxHash",
        ]
        
        schema_query = Query(
            name="schema",
            arguments=schema_args,
            fields=schema_fields
        )
        
        operation = Operation(
            type="query",
            name="GetSchema",
            variables=variables_list,
            queries=[schema_query]
        )
        
        query = operation.render()
        
        try:
            data = await self._query(query, variables_dict)
            schema_data = data.get("schema")
            
            if not schema_data:
                return None
            
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
