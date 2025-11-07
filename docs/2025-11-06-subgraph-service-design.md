# Vana Subgraph Implementation Design

## Overview
This document provides the complete design for implementing GraphQL queries in `services/subgraph.py` based on analysis of the Vana subgraph introspection and live endpoint testing.

Vana subgraph introspection is available at @docs/vana-subgraph-introspection.json
---

## Section 1: Subgraph Schema Analysis

### GraphQL Endpoint
- **URL**: `https://moksha.vanagraph.io` (for testnet, chain_id == 14800)
- **URL**: `https://vanagraph.io` (for mainnet, chain_id == 1480)
- **Method**: POST
- **Content-Type**: `application/json`

### Key Types

#### File Type
```graphql
type File {
  id: ID!                    # The unique ID (equivalent to on-chain fileId)
  owner: User!               # The owner object (contains User with id field)
  url: String!               # URL where file data is stored (IPFS, Google Drive, etc.)
  schemaId: BigInt!          # Schema ID (0 means no schema)
  addedAtTimestamp: BigInt!  # Unix timestamp when file was added
  addedAtBlock: BigInt!      # Block number when file was added
  transactionHash: Bytes!    # Transaction hash of file addition
}
```

**Key Fields**:
- `id`: String representation of the file ID (e.g., "1129387")
- `owner.id`: Ethereum address as string (e.g., "0xd867102a1955046f3190c89c48d9f0ce79d6bda7")
- `url`: File URL (can be IPFS, Google Drive, etc.)
- `schemaId`: String representation of BigInt (e.g., "25", "0" for no schema)
- `addedAtTimestamp`: String representation of Unix timestamp (e.g., "1735793142")

#### File_filter Input
Available filter operations:
- `owner`: String (full address match)
- `owner_contains_nocase`: String (case-insensitive substring)
- `schemaId`: BigInt
- `schemaId_gt`, `schemaId_lt`, `schemaId_gte`, `schemaId_lte`: BigInt comparisons
- `schemaId_in`: [BigInt!] (match any in list)
- `schemaId_not_in`: [BigInt!] (exclude any in list)
- `addedAtTimestamp`: BigInt (and comparison operators)
- `addedAtBlock`: BigInt (and comparison operators)

#### Schema Type
```graphql
type Schema {
  id: ID!                  # Schema ID as string
  name: String!            # Schema name (e.g., "Instagram User Data Schema")
  dialect: String!         # Schema dialect (typically "json")
  definitionUrl: String!   # IPFS URL (e.g., "ipfs://bafkreigq6...")
  refiners: [Refiner!]!    # Related refiners (not needed for our use case)
  createdAt: BigInt!       # Unix timestamp of creation
  createdAtBlock: BigInt!  # Block number of creation
  createdTxHash: Bytes!    # Transaction hash of creation
}
```

**Key Fields**:
- `id`: String representation of schema ID (e.g., "35")
- `name`: Human-readable name
- `dialect`: Format type (e.g., "json")
- `definitionUrl`: IPFS URL pointing to full schema definition
- `createdAt`: String representation of Unix timestamp

**Note**: There is NO `description` field in the Schema type. The description is only available in the full schema definition fetched from IPFS.

#### Schema_filter Input
Available filter operations:
- `id`, `id_in`, `id_not_in`: ID filters
- `name`: String (exact match)
- `name_contains`, `name_contains_nocase`: String substring search
- `name_starts_with`, `name_starts_with_nocase`: Prefix search
- `name_ends_with`, `name_ends_with_nocase`: Suffix search
- `dialect`: String filters (similar to name)
- `createdAt`: BigInt (and comparison operators)

### Query Root Fields

#### files
```graphql
files(
  skip: Int = 0
  first: Int = 100
  orderBy: File_orderBy
  orderDirection: OrderDirection
  where: File_filter
): [File!]!
```

#### file
```graphql
file(id: ID!): File
```

#### schemas
```graphql
schemas(
  skip: Int = 0
  first: Int = 100
  orderBy: Schema_orderBy
  orderDirection: OrderDirection
  where: Schema_filter
): [Schema!]!
```

#### schema
```graphql
schema(id: ID!): Schema
```

### Pagination & Ordering
- **skip**: Offset for pagination (default: 0)
- **first**: Limit for results (default: 100, max: 100)
- **orderBy**: Field to sort by (e.g., `addedAtTimestamp`, `createdAt`)
- **orderDirection**: `asc` or `desc`

---

## Section 2: GraphQL Query Definitions

### Query 1: list_files

**Method Signature**: `list_files(owner_address, schema_ids?, limit, offset)`

**GraphQL Query**:
```graphql
query ListFiles($owner: String!, $schemaIds: [BigInt!], $limit: Int!, $skip: Int!) {
  files(
    where: {
      owner: $owner
      schemaId_in: $schemaIds
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
```

**Variables**:
```json
{
  "owner": "0xd867102a1955046f3190c89c48d9f0ce79d6bda7",
  "schemaIds": ["25", "35"],  // Optional, omit if null
  "limit": 10,
  "skip": 0
}
```

**Notes**:
- Always filter `schemaId_gt: "0"` to exclude files without schemas (as per requirement)
- If `schema_ids` is provided, add `schemaId_in` to where clause
- If `schema_ids` is null/empty, omit the `schemaId_in` filter (keep only `schemaId_gt: "0"`)
- Owner should be lowercased before query
- Order by timestamp descending (newest first)

**Implementation Note**: Since The Graph doesn't provide a built-in count mechanism, we will not return total counts. Clients can determine if there are more pages by checking if `len(results) == limit`.

---

### Query 2: get_file_metadata

**Method Signature**: `get_file_metadata(file_id, owner_address)`

**GraphQL Query**:
```graphql
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
```

**Variables**:
```json
{
  "id": "1129387"
}
```

**Post-Query Validation**:
- Check if `file.owner.id.lower() == owner_address.lower()`
- Return `None` if validation fails or file not found
- Convert timestamp to ISO format: `datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()`

---

### Query 3: list_schemas

**Method Signature**: `list_schemas(query?, limit, offset)`

**GraphQL Query** (with search):
```graphql
query ListSchemas($query: String, $limit: Int!, $skip: Int!) {
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
```

**GraphQL Query** (without search):
```graphql
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
```

**Variables**:
```json
{
  "query": "uber",  // Optional
  "limit": 10,
  "skip": 0
}
```

**Notes**:
- Use `name_contains_nocase` for case-insensitive search
- If `query` is None or empty, omit the where clause entirely
- Order by creation time descending (newest first)
- No description field available in subgraph response - must fetch from IPFS

---

### Query 4: get_schema

**Method Signature**: `get_schema(schema_id)`

**Step 1: Query Subgraph**:
```graphql
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
```

**Variables**:
```json
{
  "id": "35"
}
```

**Step 2: Fetch IPFS Content**:
- Parse `definitionUrl` (e.g., "ipfs://bafkreigq6...")
- Extract CID: `bafkreigq6...`
- Fetch from IPFS gateway: `https://ipfs.io/ipfs/{CID}`
- Parse JSON response

**IPFS Schema Structure** (example):
```json
{
  "name": "Instagram User Data Schema",
  "version": "1.1.0",
  "dialect": "json",
  "description": "A schema for validating the structure of Instagram user data claims.",
  "schema": {
    "type": "object",
    "properties": { ... }
  }
}
```

**Response Mapping**:
```python
{
    "schema_id": int(schema_data["id"]),
    "name": schema_data["name"],
    "version": ipfs_data.get("version", "unknown"),
    "description": ipfs_data.get("description", ""),
    "ipfs_url": schema_data["definitionUrl"],
    "schema": ipfs_data.get("schema", {})
}
```

**Error Handling**:
- Return `None` if schema not found in subgraph
- Return partial data if IPFS fetch fails (include error in logs)
- Timeout IPFS requests after 10 seconds

---

## Section 3: Python Type Definitions

### File: `domain/subgraph_types.py`

```python
"""
Type definitions for Vana subgraph responses.

These types match the GraphQL schema structure from the Vana subgraph.
"""

from typing import TypedDict, Optional, List
from dataclasses import dataclass
from datetime import datetime


# Raw GraphQL types (keep as TypedDict)

class SubgraphOwner(TypedDict):
    """Owner reference from subgraph."""
    id: str  # Ethereum address


class SubgraphFile(TypedDict):
    """File entity from subgraph."""
    id: str  # File ID as string
    owner: SubgraphOwner
    url: str
    schemaId: str  # BigInt as string
    addedAtTimestamp: str  # Unix timestamp as string
    addedAtBlock: Optional[str]  # BigInt as string, optional for list queries
    transactionHash: Optional[str]  # Hex string, optional for list queries


class SubgraphSchema(TypedDict):
    """Schema entity from subgraph."""
    id: str  # Schema ID as string
    name: str
    dialect: str
    definitionUrl: str  # IPFS URL
    createdAt: str  # Unix timestamp as string
    createdAtBlock: Optional[str]  # BigInt as string, optional for list queries
    createdTxHash: Optional[str]  # Hex string, optional for list queries


class IPFSSchemaDefinition(TypedDict):
    """Schema definition fetched from IPFS."""
    name: str
    version: str
    dialect: str
    description: str
    schema: dict  # JSON Schema object


# Response types for service methods (using dataclasses)

@dataclass
class SubgraphFileMetadata:
    """Processed file metadata for API responses."""
    file_id: int
    file_url: str
    schema_id: Optional[int]  # None if schemaId is 0
    date_added: str  # ISO format datetime string


@dataclass
class SubgraphFileListResponse:
    """Response for list_files method."""
    files: List[SubgraphFileMetadata]
    limit: int
    offset: int


@dataclass
class SubgraphSchemaInfo:
    """Basic schema information for list responses."""
    schema_id: int
    name: str
    description: str  # Empty string if not available from IPFS


@dataclass
class SubgraphSchemaListResponse:
    """Response for list_schemas method."""
    schemas: List[SubgraphSchemaInfo]
    limit: int
    offset: int


@dataclass
class SubgraphSchemaDefinition:
    """Complete schema definition with IPFS data."""
    schema_id: int
    name: str
    version: str
    description: str
    ipfs_url: str
    schema: dict  # The actual JSON Schema


# Helper functions

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
        description=""  # Will be populated from IPFS if needed
    )
```

---

## Section 4: Implementation Notes

### General GraphQL Request Pattern

```python
async def _query(self, query: str, variables: Optional[dict] = None) -> dict:
    """Execute a GraphQL query against the subgraph."""
    payload = {
        "query": query,
        "variables": variables or {}
    }
    
    response = await self.client.post(
        self.subgraph_url,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    response.raise_for_status()
    
    data = response.json()
    
    # Check for GraphQL errors
    if "errors" in data:
        error_messages = [e.get("message", str(e)) for e in data["errors"]]
        raise Exception(f"GraphQL errors: {', '.join(error_messages)}")
    
    return data.get("data", {})
```

### Address Normalization

Always lowercase Ethereum addresses before querying:
```python
owner_address = owner_address.lower()
```

### Timestamp Conversion

Convert Unix timestamps to ISO format:
```python
from datetime import datetime, timezone

timestamp = int(timestamp_str)
iso_date = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
```

### Schema ID Handling

- `schemaId: "0"` means no schema assigned
- Convert to Python int: `int(schema_id_str)`
- Return `None` instead of 0 for `schema_id` field in responses

### Using Existing IPFS Utilities

Use the existing `utils/ipfs.py` module which provides robust IPFS fetching with multiple gateway fallbacks:

```python
from utils.ipfs import fetch_json_with_fallbacks, IPFSError

async def _fetch_ipfs_schema(self, ipfs_url: str) -> Optional[dict]:
    """
    Fetch schema definition from IPFS using existing utilities.

    The fetch_json_with_fallbacks function:
    - Automatically converts ipfs:// URLs to gateway URLs
    - Tries multiple IPFS gateways with automatic fallback
    - Handles timeouts and errors gracefully
    - Returns parsed JSON data

    Args:
        ipfs_url: IPFS URL (e.g., "ipfs://bafkreigq6...")

    Returns:
        Parsed schema definition or None if fetch fails
    """
    try:
        # fetch_json_with_fallbacks is synchronous, so run in executor if needed
        # For now, assuming we'll use sync version or wrap appropriately
        return fetch_json_with_fallbacks(ipfs_url, timeout=10)
    except IPFSError as e:
        logger.error(f"Failed to fetch IPFS schema from {ipfs_url}: {e}")
        return None
```

**Available IPFS Functions** (from `utils/ipfs.py`):
- `fetch_json_with_fallbacks(url, timeout=10)` - Fetch and parse JSON from IPFS
- `fetch_with_fallbacks(url, timeout=10)` - Fetch raw content from IPFS
- `extract_ipfs_hash(url)` - Extract hash from IPFS URL
- `convert_ipfs_url(url, gateway)` - Convert ipfs:// to gateway URL

**Exception Types**:
- `IPFSError` - Base exception for IPFS errors
- `IPFSTimeoutError` - Request timeout
- `IPFSNotFoundError` - Content not found
- `IPFSRateLimitError` - Gateway rate limit exceeded

### Error Handling

1. **GraphQL Errors**: Check for `errors` field in response and raise exception
2. **HTTP Errors**: Let httpx raise HTTPError for 4xx/5xx responses
3. **Not Found**: Return `None` for single-item queries (file, schema)
4. **IPFS Failures**: Log error and return partial data without IPFS content
5. **Validation Failures**: Return `None` for `get_file_metadata` if owner doesn't match

### Pagination Strategy

Since The Graph doesn't provide a total count mechanism:

1. **For list_files and list_schemas**:
   - Do NOT return a `total` field
   - Clients can determine if more pages exist by checking: `len(results) == limit`
   - If result count equals the limit, there might be more pages

2. **Example**:
```python
results = await self._query(query, {"limit": limit, "skip": offset, ...})
files = results["files"]

return SubgraphFileListResponse(
    files=[parse_file_metadata(f) for f in files],
    limit=limit,
    offset=offset
)
```

---

## Section 5: Test Commands

### Prerequisites
```bash
export SUBGRAPH_URL="https://moksha.vanagraph.io"
export TEST_WALLET="0xd867102a1955046f3190c89c48d9f0ce79d6bda7"
```

### Test 1: List Files (Basic)
```bash
curl -X POST $SUBGRAPH_URL \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ files(first: 2, where: {owner: \"'$TEST_WALLET'\"}) { id owner { id } url schemaId addedAtTimestamp } }"
  }'
```

**Expected Response**:
```json
{
  "data": {
    "files": [
      {
        "id": "1129387",
        "owner": { "id": "0xd867102a1955046f3190c89c48d9f0ce79d6bda7" },
        "url": "https://drive.google.com/uc?export=download&id=1na-0aRrdIWaYMSo8Sbj2stWUFZsS7KSR",
        "schemaId": "0",
        "addedAtTimestamp": "1735793142"
      },
      { ... }
    ]
  }
}
```

### Test 2: List Files with Schema Filter
```bash
curl -X POST $SUBGRAPH_URL \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ files(first: 3, where: {owner: \"'$TEST_WALLET'\", schemaId_gt: \"0\"}, orderBy: addedAtTimestamp, orderDirection: desc) { id url schemaId addedAtTimestamp } }"
  }'
```

**Expected Response**:
```json
{
  "data": {
    "files": [
      {
        "id": "1760803",
        "url": "https://drive.google.com/uc?id=18YjAwrXhFyircud9nJv6imzIf-iOvkCn&export=download",
        "schemaId": "25",
        "addedAtTimestamp": "1757793576"
      },
      { ... }
    ]
  }
}
```

### Test 3: Get Single File
```bash
curl -X POST $SUBGRAPH_URL \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ file(id: \"1129387\") { id owner { id } url schemaId addedAtTimestamp addedAtBlock transactionHash } }"
  }'
```

**Expected Response**:
```json
{
  "data": {
    "file": {
      "id": "1129387",
      "owner": { "id": "0xd867102a1955046f3190c89c48d9f0ce79d6bda7" },
      "url": "https://drive.google.com/uc?export=download&id=1na-0aRrdIWaYMSo8Sbj2stWUFZsS7KSR",
      "schemaId": "0",
      "addedAtTimestamp": "1735793142",
      "addedAtBlock": "1044850",
      "transactionHash": "0xf241fc69abbf2709c2765ed8071b49267d0312de0ba47b1bfda6dd3e2e22f901"
    }
  }
}
```

### Test 4: List Schemas (All)
```bash
curl -X POST $SUBGRAPH_URL \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ schemas(first: 3, orderBy: createdAt, orderDirection: desc) { id name dialect definitionUrl createdAt } }"
  }'
```

**Expected Response**:
```json
{
  "data": {
    "schemas": [
      {
        "id": "35",
        "name": "Instagram User Data Schema",
        "dialect": "json",
        "definitionUrl": "ipfs://bafkreigq6aqyp2rtdq2p5seqbvxteohgdtn46pdli2syt4bw67dyypvsre",
        "createdAt": "1759164810"
      },
      { ... }
    ]
  }
}
```

### Test 5: List Schemas (Search)
```bash
curl -X POST $SUBGRAPH_URL \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ schemas(first: 5, where: {name_contains_nocase: \"uber\"}) { id name dialect definitionUrl } }"
  }'
```

**Expected Response**:
```json
{
  "data": {
    "schemas": [
      {
        "id": "33",
        "name": "Uber Ride History Schema",
        "dialect": "json",
        "definitionUrl": "ipfs://bafkreiefjxlav52y3r7a7ehcjc6cdm63pyvjc4tpe4oycg7ulqqq5trc5e"
      },
      {
        "id": "34",
        "name": "Uber Eats Order History Schema",
        "dialect": "json",
        "definitionUrl": "ipfs://bafkreiazmmuuhypt2p2ryn2fndxplqpa5olu3qcjmjqk7vbxgo5642olfq"
      }
    ]
  }
}
```

### Test 6: Get Single Schema
```bash
curl -X POST $SUBGRAPH_URL \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ schema(id: \"35\") { id name dialect definitionUrl createdAt createdAtBlock createdTxHash } }"
  }'
```

**Expected Response**:
```json
{
  "data": {
    "schema": {
      "id": "35",
      "name": "Instagram User Data Schema",
      "dialect": "json",
      "definitionUrl": "ipfs://bafkreigq6aqyp2rtdq2p5seqbvxteohgdtn46pdli2syt4bw67dyypvsre",
      "createdAt": "1759164810",
      "createdAtBlock": "4481386",
      "createdTxHash": "0x3d3e0086da6112aa79231224ac7576b0d333095b477addb35ae4947219738efe"
    }
  }
}
```

### Test 7: Fetch IPFS Schema
```bash
curl -s "https://ipfs.io/ipfs/bafkreigq6aqyp2rtdq2p5seqbvxteohgdtn46pdli2syt4bw67dyypvsre"
```

**Expected Response** (truncated):
```json
{
  "name": "Instagram User Data Schema",
  "version": "1.1.0",
  "dialect": "json",
  "description": "A schema for validating the structure of Instagram user data claims.",
  "schema": {
    "type": "object",
    "properties": { ... }
  }
}
```

### Test 8: Pagination
```bash
# First page
curl -X POST $SUBGRAPH_URL \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ files(first: 2, skip: 0, where: {owner: \"'$TEST_WALLET'\"}, orderBy: addedAtTimestamp, orderDirection: desc) { id url schemaId } }"
  }'

# Second page
curl -X POST $SUBGRAPH_URL \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ files(first: 2, skip: 2, where: {owner: \"'$TEST_WALLET'\"}, orderBy: addedAtTimestamp, orderDirection: desc) { id url schemaId } }"
  }'
```

---

## Implementation Checklist

- [ ] Create `domain/subgraph_types.py` with type definitions
- [ ] Implement `_query()` method in `SubgraphClient`
- [ ] Implement `list_files()` with proper filtering and pagination
- [ ] Implement `get_file_metadata()` with owner validation
- [ ] Implement `list_schemas()` with optional search
- [ ] Implement `get_schema()` with two-step IPFS fetch
- [ ] Add IPFS helper functions for URL parsing and fetching
- [ ] Add comprehensive error handling for all methods
- [ ] Write unit tests for each method
- [ ] Write integration tests against live subgraph
- [ ] Update MCP resource/tool implementations to use new subgraph client
- [ ] Add logging for debugging GraphQL queries and IPFS fetches

---

## Future Considerations

1. **Caching**: Consider caching schema definitions from IPFS (they rarely change)
2. **Total Count**: If The Graph adds aggregation support, update pagination strategy
3. **Alternative IPFS Gateways**: Add fallback gateways if ipfs.io is slow/unavailable
4. **Description Caching**: For `list_schemas`, consider fetching descriptions lazily or caching them
5. **Rate Limiting**: Add rate limiting for IPFS requests to avoid gateway throttling
6. **Batch Operations**: Consider batching multiple schema IPFS fetches in parallel

---

## References

- Vana Subgraph Introspection: `@docs/vana-subgraph-introspection.json`
- Live Endpoint: `https://moksha.vanagraph.io`
- IPFS Gateway: `https://ipfs.io/ipfs/`
- Service Implementation: `@services/subgraph.py`
