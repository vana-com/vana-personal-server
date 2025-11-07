"""
Type definitions for Vana subgraph responses.

These types match the GraphQL schema structure from the Vana subgraph.
All response types use TypedDict for JSON serialization compatibility.
"""

from typing import TypedDict, Optional, List
from datetime import datetime, timezone


class SubgraphOwner(TypedDict):
    """Owner reference from subgraph."""
    id: str


class SubgraphFile(TypedDict):
    """File entity from subgraph."""
    id: str
    owner: SubgraphOwner
    url: str
    schemaId: str
    addedAtTimestamp: str
    addedAtBlock: Optional[str]
    transactionHash: Optional[str]


class SubgraphSchema(TypedDict):
    """Schema entity from subgraph."""
    id: str
    name: str
    dialect: str
    definitionUrl: str
    createdAt: str
    createdAtBlock: Optional[str]
    createdTxHash: Optional[str]


class IPFSSchemaDefinition(TypedDict):
    """Schema definition fetched from IPFS."""
    name: str
    version: str
    dialect: str
    description: str
    schema: dict


class SubgraphFileMetadata(TypedDict):
    """Processed file metadata for API responses."""
    file_id: int
    file_url: str
    schema_id: Optional[int]
    date_added: str


class SubgraphFileListResponse(TypedDict):
    """Response for list_files method."""
    files: List[SubgraphFileMetadata]
    limit: int
    offset: int


class SubgraphSchemaInfo(TypedDict):
    """Basic schema information for list responses."""
    schema_id: int
    name: str
    description: str


class SubgraphSchemaListResponse(TypedDict):
    """Response for list_schemas method."""
    schemas: List[SubgraphSchemaInfo]
    limit: int
    offset: int


class SubgraphSchemaDefinition(TypedDict):
    """Complete schema definition with IPFS data."""
    schema_id: int
    name: str
    version: str
    description: str
    ipfs_url: str
    schema: dict


def parse_file_metadata(subgraph_file: SubgraphFile) -> SubgraphFileMetadata:
    """Convert subgraph file to API response format."""
    schema_id = int(subgraph_file["schemaId"])
    timestamp = int(subgraph_file["addedAtTimestamp"])

    return SubgraphFileMetadata(
        file_id=int(subgraph_file["id"]),
        file_url=subgraph_file["url"],
        schema_id=schema_id if schema_id > 0 else None,
        date_added=datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    )


def parse_schema_info(subgraph_schema: SubgraphSchema) -> SubgraphSchemaInfo:
    """Convert subgraph schema to basic info format."""
    return SubgraphSchemaInfo(
        schema_id=int(subgraph_schema["id"]),
        name=subgraph_schema["name"],
        description=""
    )

