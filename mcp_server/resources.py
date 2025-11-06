"""
MCP Resource handlers for Vana Personal Server.

Resources provide direct data access via URIs:
- vana://files - List all accessible files
- vana://file/{id} - Get decrypted file content
- vana://file/{id}/metadata - Get file metadata
- vana://schemas - List all available schemas
- vana://schema/{id} - Get schema definition
"""

import json
import logging
from typing import Optional
from urllib.parse import parse_qs, urlparse

from web3 import AsyncWeb3
from fastmcp.resources import Resource

from services.subgraph import get_subgraph_client
from services.identity import IdentityService
from onchain.data_registry import DataRegistry
from onchain.chain import Chain, get_chain
from utils.files.decrypt import decrypt_with_private_key, decrypt_user_data
from utils.files.download import download_file
from domain.exceptions import DecryptionError
from jsonpath_ng import parse as jsonpath_parse
from settings import Settings, get_settings

logger = logging.getLogger(__name__)


class ResourceHandler:
    """
    Handler for MCP resources with initialized dependencies.
    
    This class initializes expensive objects (Web3 connection, DataRegistry,
    IdentityService, etc.) once in __init__ to avoid repeated instantiation
    on every resource request.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize resource handler with dependencies.
        
        Args:
            settings: Optional settings instance (defaults to get_settings())
        """
        self.settings = settings or get_settings()
        self.subgraph = get_subgraph_client()
        self.chain = get_chain(self.settings.chain_id)
        self.web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(self.chain.url))
        self.data_registry = DataRegistry(self.chain, self.web3)
        self.identity_service = IdentityService()


    async def read_files_resource(self, uri: str, wallet_address: str) -> str:
        """
        Read vana://files resource with optional filtering.

        URI format: vana://files?schema_ids=1,2,3&limit=10&offset=0

        Args:
            uri: The resource URI
            wallet_address: Authenticated wallet address

        Returns:
            JSON string with file list

        Raises:
            ValueError: If parameters are invalid
        """
        # Parse query parameters
        parsed = urlparse(uri)
        params = parse_qs(parsed.query)

        # Extract and validate parameters
        schema_ids = None
        if 'schema_ids' in params:
            try:
                schema_ids = [int(sid) for sid in params['schema_ids'][0].split(',')]
            except (ValueError, IndexError):
                raise ValueError("Invalid schema_ids parameter. Must be comma-separated integers.")

        limit = min(int(params.get('limit', [10])[0]), 100)
        offset = int(params.get('offset', [0])[0])

        if not wallet_address:
            raise ValueError("Authentication required. No wallet address provided.")

        # Query subgraph for files
        result = await self.subgraph.list_files(
            owner_address=wallet_address,
            schema_ids=schema_ids,
            limit=limit,
            offset=offset
        )

        return json.dumps(result, indent=2)


    async def read_file_content_resource(self, uri: str, wallet_address: str) -> str:
        """
        Read vana://file/{file_id} resource with optional JSONPath filtering.

        URI format: vana://file/123?filter=$.messages[0:10]

        Args:
            uri: The resource URI
            wallet_address: Authenticated wallet address

        Returns:
            Decrypted file content (JSON string)

        Raises:
            ValueError: If file doesn't exist, user lacks access, or filter is invalid
            DecryptionError: If file cannot be decrypted
        """
        # Parse URI
        # Handle custom vana:// scheme - urlparse treats everything after scheme as netloc
        # For vana://file/123, netloc="file", path="/123"
        # For vana://file/123/metadata, netloc="file", path="/123/metadata"
        parsed = urlparse(uri)
        
        # Reconstruct full path: netloc + path
        full_path = f"{parsed.netloc}{parsed.path}" if parsed.netloc else parsed.path
        path_parts = full_path.strip('/').split('/')

        if len(path_parts) < 2:
            raise ValueError("Invalid URI format. Expected vana://file/{file_id}")

        try:
            file_id = int(path_parts[1])
        except ValueError:
            raise ValueError(f"Invalid file_id: {path_parts[1]}")

        # Parse query parameters
        params = parse_qs(parsed.query)
        filter_expr = params.get('filter', [None])[0]

        if not wallet_address:
            raise ValueError("Authentication required. No wallet address provided.")

        # Get file metadata from subgraph
        metadata = await self.subgraph.get_file_metadata(file_id, wallet_address)

        if not metadata:
            raise ValueError(
                f"File {file_id} does not exist or you lack access. "
                "Call list_files() to see accessible files or verify file ID is correct."
            )

        # Download encrypted file
        try:
            encrypted_content = download_file(metadata['file_url'])
        except Exception as e:
            raise ValueError(f"Failed to download file: {str(e)}")

        # Decrypt file using DataRegistry
        # Follows the same pattern as operations.py:_decrypt_files_content
        try:
            # Step 1: Derive server keys for the file owner (wallet_address)
            logger.info(f"[RESOURCE] Deriving server keys for file owner: {wallet_address}")
            identity_response = self.identity_service.derive_server_identity(wallet_address)
            server_private_key = identity_response.personal_server.private_key
            server_address = identity_response.personal_server.address
            logger.info(f"[RESOURCE] Derived server address: {server_address}")

            # Step 2: Get encrypted key from blockchain via DataRegistry
            logger.info(f"[RESOURCE] Fetching encrypted key for file {file_id} from blockchain")
            
            # Fetch file metadata from blockchain (includes encrypted key)
            file_metadata = await self.data_registry.fetch_file_metadata(file_id, server_address)
            if not file_metadata:
                raise ValueError(f"File {file_id} metadata not found on blockchain or server lacks access")
            
            encrypted_key = file_metadata.encrypted_key
            if not encrypted_key:
                raise ValueError(f"No encrypted key found for file {file_id} and server {server_address}")

            # Step 3: Decrypt the encryption key with personal server's private key
            logger.info(f"[RESOURCE] Decrypting encryption key for file {file_id}")
            decrypted_encryption_key = decrypt_with_private_key(encrypted_key, server_private_key)
            
            # Step 4: Decrypt the file content with the decrypted key
            logger.info(f"[RESOURCE] Decrypting file content for file {file_id}")
            decrypted_file_content_bytes = decrypt_user_data(encrypted_content, decrypted_encryption_key)
            decrypted_content = decrypted_file_content_bytes.decode("utf-8")
            
            logger.info(f"[RESOURCE] File {file_id} decrypted successfully. Content size: {len(decrypted_content)} chars")
            
        except ValueError as e:
            # Re-raise ValueError as-is (file not found, etc.)
            raise
        except Exception as e:
            logger.error(f"[RESOURCE] Decryption failed for file {file_id}: {str(e)}")
            raise DecryptionError(
                f"Unable to decrypt file {file_id}. "
                "Verify the personal server has permission to decrypt this file. "
                f"Error: {str(e)}"
            )

        # Apply JSONPath filter if provided
        if filter_expr:
            try:
                # Parse content as JSON
                content_json = json.loads(decrypted_content)

                # Apply JSONPath filter
                jsonpath_expr = jsonpath_parse(filter_expr)
                matches = [match.value for match in jsonpath_expr.find(content_json)]

                # Return filtered results
                if len(matches) == 1:
                    filtered_content = matches[0]
                else:
                    filtered_content = matches

                return json.dumps(filtered_content, indent=2)

            except json.JSONDecodeError:
                raise ValueError("File content is not valid JSON. Cannot apply filter.")
            except Exception as e:
                raise ValueError(
                    f"Invalid JSONPath filter: {filter_expr}. "
                    f"Read schema first: vana://schema/{metadata.get('schema_id')}. "
                    "Common patterns: $.field, $[0:10], $[?(@.type=='value')]"
                )

        return decrypted_content


    async def read_file_metadata_resource(self, uri: str, wallet_address: str) -> str:
        """
        Read vana://file/{file_id}/metadata resource.

        Args:
            uri: The resource URI
            wallet_address: Authenticated wallet address

        Returns:
            JSON string with file metadata

        Raises:
            ValueError: If file doesn't exist or user lacks access
        """
        # Parse URI
        # Handle custom vana:// scheme - urlparse treats everything after scheme as netloc
        # For vana://file/123/metadata, netloc="file", path="/123/metadata"
        parsed = urlparse(uri)
        
        # Reconstruct full path: netloc + path
        full_path = f"{parsed.netloc}{parsed.path}" if parsed.netloc else parsed.path
        path_parts = full_path.strip('/').split('/')

        if len(path_parts) < 3 or path_parts[2] != 'metadata':
            raise ValueError("Invalid URI format. Expected vana://file/{file_id}/metadata")

        try:
            file_id = int(path_parts[1])
        except ValueError:
            raise ValueError(f"Invalid file_id: {path_parts[1]}")

        if not wallet_address:
            raise ValueError("Authentication required. No wallet address provided.")

        # Get file metadata from subgraph
        metadata = await self.subgraph.get_file_metadata(file_id, wallet_address)

        if not metadata:
            raise ValueError(
                f"File {file_id} does not exist or you lack access. "
                "Call list_files() to see accessible files or verify file ID is correct."
            )

        return json.dumps(metadata, indent=2)


    async def read_schemas_resource(self, uri: str, wallet_address: str) -> str:
        """
        Read vana://schemas resource with optional search.

        URI format: vana://schemas?query=chatgpt&limit=10&offset=0

        Args:
            uri: The resource URI
            wallet_address: Authenticated wallet address (not used but kept for consistency)

        Returns:
            JSON string with schema list
        """
        # Parse query parameters
        parsed = urlparse(uri)
        params = parse_qs(parsed.query)

        query = params.get('query', [None])[0]
        limit = min(int(params.get('limit', [10])[0]), 100)
        offset = int(params.get('offset', [0])[0])

        # Query subgraph for schemas
        result = await self.subgraph.list_schemas(
            query=query,
            limit=limit,
            offset=offset
        )

        return json.dumps(result, indent=2)


    async def read_schema_resource(self, uri: str, wallet_address: str) -> str:
        """
        Read vana://schema/{schema_id} resource.

        Fetches schema metadata from subgraph and schema definition from IPFS.

        Args:
            uri: The resource URI
            wallet_address: Authenticated wallet address (not used but kept for consistency)

        Returns:
            JSON string with schema definition

        Raises:
            ValueError: If schema_id is invalid or schema not found
        """
        # Parse URI
        # Handle custom vana:// scheme - urlparse treats everything after scheme as netloc
        # For vana://schema/123, netloc="schema", path="/123"
        parsed = urlparse(uri)
        
        # Reconstruct full path: netloc + path
        full_path = f"{parsed.netloc}{parsed.path}" if parsed.netloc else parsed.path
        path_parts = full_path.strip('/').split('/')

        if len(path_parts) < 2:
            raise ValueError("Invalid URI format. Expected vana://schema/{schema_id}")

        try:
            schema_id = int(path_parts[1])
        except ValueError:
            raise ValueError(f"Invalid schema_id: {path_parts[1]}")

        # Get schema from subgraph (includes IPFS fetch)
        schema = await self.subgraph.get_schema(schema_id)

        if not schema:
            raise ValueError(
                f"Schema ID {schema_id} does not exist in the network. "
                "Call list_schemas() to see available schemas."
            )

        return json.dumps(schema, indent=2)


# Singleton instance
_resource_handler: Optional[ResourceHandler] = None


def get_resource_handler() -> ResourceHandler:
    """
    Get or create the singleton resource handler instance.
    
    Returns:
        ResourceHandler instance
    """
    global _resource_handler
    if _resource_handler is None:
        _resource_handler = ResourceHandler()
    return _resource_handler


# Resource definitions for FastMCP registration
FILES_RESOURCE = Resource(
    uri="vana://files",
    name="User Files",
    description="List all accessible files for the authenticated user. Supports filtering by schema_ids, pagination with limit/offset.",
    mime_type="application/json"
)

FILE_CONTENT_RESOURCE = Resource(
    uri="vana://file/{file_id}",
    name="File Content",
    description="Get decrypted file content. Supports optional JSONPath filtering via ?filter= parameter.",
    mime_type="application/json"
)

FILE_METADATA_RESOURCE = Resource(
    uri="vana://file/{file_id}/metadata",
    name="File Metadata",
    description="Get file metadata (file_url, schema_id, date_added) without decryption.",
    mime_type="application/json"
)

SCHEMAS_RESOURCE = Resource(
    uri="vana://schemas",
    name="Available Schemas",
    description="List all available schemas in the network. Supports keyword search via ?query= parameter and pagination.",
    mime_type="application/json"
)

SCHEMA_RESOURCE = Resource(
    uri="vana://schema/{schema_id}",
    name="Schema Definition",
    description="Get schema definition from IPFS including name, version, description, and schema structure.",
    mime_type="application/json"
)
