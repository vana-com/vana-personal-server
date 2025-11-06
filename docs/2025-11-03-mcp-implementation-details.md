# MCP - Implementation Details

## Overview

This document outlines potential tools, resources, and prompts for the Vana Personal Server MCP implementation. Focus: enable data portability and data discovery across applications (e.g., "import my ChatGPT memories into Claude").

## [Resources](https://modelcontextprotocol.io/specification/2025-06-18/server/resources)

Resources provide direct data access via URIs. Use when LLM needs to read files, schemas, or metadata without computation.

**MCP Resource Pattern:**

* `resources/list` returns base URIs: `vana://files`, `vana://schemas`  
* `resources/read` supports query parameters for filtering: `vana://files?schema_ids=1,2,3`  
* Tools construct filtered URIs dynamically based on user queries

### File Resources

* `vana://files`: List all accessible files for authenticated user (file ID, file URL, date added, and schema ID)  
  * Query params: `schema_ids` (array), `limit` (int, default 10), `offset` (int, default 0\)  
  * Example: `vana://files?schema_ids=1,2,3&limit=20&offset=0`  
  * Returns: `{files: [...], limit: 20, offset: 0}`  
  * **Important**: Filters out files without schema ID (helps keep LLM focused on files with schema context). Note: Total counts are not available from the subgraph query.  
* `vana://file/{file_id}/metadata`: Get file metadata (file URL, date added, and schema ID, if any)  
  * Returns: `{file_id, file_url, schema_id, date_added}`  
* `vana://file/{file_id}`: Get decrypted file contents  
  * Query params: `filter` (JSONPath expression, optional)  
  * Example: `vana://file/123?filter=$.messages[0:10]`  
  * Returns: Decrypted file content (full or filtered)  
  * **Filter Usage**: LLMs should first read the schema (`vana://schema/{schema_id}`) to understand the data structure before constructing filters. Filters are optional and should only be used for large files to reduce token usage.

### Schema Resources

* `vana://schemas`: List all available schemas in the network (schema ID and brief description)  
  * Query params: `query` (string), `limit` (int, default 10), `offset` (int, default 0\)  
  * Example: `vana://schemas?query=chatgpt&limit=10`  
  * Returns: `{schemas: [...], limit: 10, offset: 0}`  
  * **Note**: Total counts are not available from the subgraph query. To determine if there are more pages, check if `len(schemas) == limit`.
* `vana://schema/{schema_id}`: Get schema definition (name, version, dialect, description, and the schema itself)  
  * Example response: Entire contents of a schema file [https://ipfs.io/ipfs/bafkreig5vccfw2helr3g6zyzzo7lo4up2nzpgvfkx6a4noascjoe22w7de](https://ipfs.io/ipfs/bafkreig5vccfw2helr3g6zyzzo7lo4up2nzpgvfkx6a4noascjoe22w7de)

## [Tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)

Tools provide functions for search, filtering, and aggregation. Use when LLM needs to query, filter, or combine data from multiple resources.

**Pagination defaults:** `limit=10`, `offset=0`. Note: Total counts are not available from the subgraph query. To determine if there are more pages, check if `len(results) == limit`.

### `list_files(schema_ids?: array, limit?: int, offset?: int)`

**Purpose:** List user's files with optional schema filtering and pagination

**Arguments:**

* `schema_ids` (optional): Array of schema IDs to filter by  
* `limit` (optional): Number of results per page (default: 10, max: 100\)  
* `offset` (optional): Starting position (default: 0\)

**Returns:**

```json
{
  "files": [
    {"file_id": 123, "schema_id": 5, "date_added": "2024-01-15", "file_url": "https://drive.google.com/?id=1234..."}
  ],
  "limit": 10,
  "offset": 0
}
```

**Implementation:** Reads resource `vana://files?schema_ids={...}&limit={...}&offset={...}`

**Errors:**

* `invalid_schema_id`: Schema ID doesn't exist  
* `empty_result`: No files found for criteria

**Fallback:** If no files match, suggest calling `list_schemas()` to discover available data types

### `search_files_by_schema(query: string, limit?: int, offset?: int)`

**Purpose:** Discover files by searching schema names/descriptions (e.g., "chatgpt", "linkedin")

**Arguments:**

* `query` (required): Keyword to search in schema title and description  
* `limit` (optional): Number of results (default: 10\)  
* `offset` (optional): Starting position (default: 0\)

**Returns:**

```json
{
  "schemas": [{"schema_id": 5, "name": "ChatGPT Conversations", "description": "..."}],
  "files": [
    {"file_id": 123, "schema_id": 5, "date_added": "2024-01-15"}
  ]
}
```

**Implementation:**

1. Read resource: `vana://schemas?query={query}`  
2. Extract schema IDs from results  
3. Read resource: `vana://files?schema_ids={...}&limit={...}&offset={...}`  
4. Combine and return

### `get_file(file_id: string, filter?: string)`

**Purpose:** Retrieve decrypted file content with optional filtering

**Arguments:**

- `file_id` (required): The file ID to retrieve  
- `filter` (optional): JSONPath expression to extract specific data

**Returns:**

```json
{
  "content": "...",  // Full or filtered file content
  "file_id": 123,
  "schema_id": 5,
  "filtered": false  // true if filter was applied
}
```

**Implementation:** Reads resource `vana://file/{file_id}?filter={filter}`

**Errors:**

- `file_not_found`: File ID doesn't exist  
- `decryption_failed`: Unable to decrypt file  
- `invalid_filter`: JSONPath expression is invalid

**Fallback:** If filter fails, return full content with warning

**Filter Guidance:**

1. Always inspect schema first: read `vana://schema/{schema_id}`  
2. Understand data structure before constructing filter  
3. Use filters only for large files (\>10KB)  
4. Common patterns:  
   - `$.messages[0:10]` \- First 10 messages  
   - `$.data.conversations` \- Specific nested field  
   - `$[?(@.type=='important')]` \- Conditional filtering

### `get_file_metadata(file_id: string)`

**Purpose:** Get file metadata without decryption

**Arguments:**

- `file_id` (required): The file ID

**Returns:**

```json
{
  "file_id": 123,
  "file_url": "https://drive.google.com/?id=...",
  "schema_id": 5,
  "date_added": "2024-01-15"
}
```

**Implementation:** Reads resource `vana://file/{file_id}/metadata`

**Errors:**

- `file_not_found`: File ID doesn't exist or doesn’t belong to the authenticated user

**Fallback:** None needed

`list_schemas(query?: string, limit?: int, offset?: int)`  
**Purpose:** List all available schemas with optional keyword search

**Arguments:**

* `query` (optional): Keyword to filter schemas  
* `limit` (optional): Number of results (default: 10\)  
* `offset` (optional): Starting position (default: 0\)

**Returns:**

```json
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
```

**Implementation:** Reads resource `vana://schemas?query={...}&limit={...}&offset={...}`

## [Prompts](https://modelcontextprotocol.io/specification/2025-06-18/server/prompts)

Prompts are reusable templates for common workflows, used to provide natural language entry points that guide the LLM through multi-step operations.

### `get_my_data(data_type: string)`

**Description:** Get user's data from a specific application or data type

**Arguments:**

* `data_type` (required): Application name or data type (e.g., "chatgpt", "linkedin", "twitter")

**Template:**

```
I want to access my {data_type} data. Use the Vana MCP to discover and retrieve my {data_type} data, then show me what's available.

Workflow:

Call search_files_by_schema(query=data_type) to find matching schemas and files
If no results, call list_schemas() and suggest similar data types
For each file found (up to 3):
Read resource vana://file/{file_id}/metadata to check size/schema
Ask user if they want to see full content or summary
If user confirms, read resource vana://file/{file_id} (use ?filter= for large files)
Present formatted content with context about schema

Success Criteria:

User sees what {data_type} data they have
User sees file count and dates
User can access full or filtered content

Error Handling:

If no schemas match: "I couldn't find any {data_type} data. You have data from: [list alternatives]"
If schemas found but no files: "{data_type} data exists in the network, but you haven't uploaded any yet"
If decryption fails: "Unable to decrypt file {file_id}. Please check permissions"
```

## Example User Flows

### Flow 1: Get ChatGPT Data

```
User: "Using the Vana MCP, get my ChatGPT data"

MCP Actions:
1. Tool: search_files_by_schema(query="chatgpt", limit=10)
   → Reads resource: vana://schemas?query=chatgpt
   → Finds schema_id=5 ("ChatGPT Conversations")
   → Reads resource: vana://files?schema_ids=5&limit=10
   → Returns: {files: [3 files], schemas: [...]}

2. For each file (file_id=123, 124, 125):
   → Tool: get_file_metadata(file_id=123)
   → Check file size and schema details

3. Tool: get_file(file_id=123) (most recent)
   → Reads resource: vana://file/123
   → Decrypt and return content
   → Present to user

4. Ask user if they want to see other files
```

### Flow 2: Discover Available Data

```
User: "What data do I have in Vana?"

MCP Actions:
1. Tool: list_schemas(limit=50)
   → Reads resource: vana://schemas?limit=50
   → Returns: {schemas: [25 schemas], limit: 50, offset: 0}

2. For top 10 schemas (parallel requests):
   → Tool: list_files(schema_ids=[schema_id], limit=1)
   → Reads resource: vana://files?schema_ids={schema_id}&limit=1
   → Checks if files array has items to determine if user has files for that schema

3. Present organized list:
   Your Data:
   * ChatGPT (schema_id=5): 3 files, most recent 2024-01-15
   * LinkedIn (schema_id=12): 1 file, most recent 2024-01-10
   * Twitter (schema_id=8): 5 files, most recent 2024-01-20
```

### Flow 3: Get Specific File with Schema Context

```
User: "Show me file 12345 and explain what it contains"

MCP Actions:
1. Tool: get_file_metadata(file_id=12345)
   → Reads resource: vana://file/12345/metadata
   → Returns: {file_id: 12345, schema_id: 5, date_added: "2024-01-15", file_url: "..."}

2. Read resource: vana://schema/5
   → Returns: {name: "ChatGPT Conversations", description: "...", structure: {...}}

3. Tool: get_file(file_id=12345)
   → Reads resource: vana://file/12345
   → Decrypts and returns content

4. Present to user:
   "This is your ChatGPT Conversations file from January 15, 2024.
    The schema defines: [explain structure]
    Here's the content: [show content]"
```

## Implementation Notes

### Resource vs Tool Decision

* **Use Resources** for direct data access (files, schemas, metadata)  
  * Individual files: `vana://file/{id}`  
  * File metadata: `vana://file/{id}/metadata`  
  * Schema definitions: `vana://schema/{id}`  
* **Use Tools** when computation/aggregation is needed  
  * Searching across schemas: `search_files_by_schema()`  
  * Listing with filters: `list_files()`, `list_schemas()`  
  * Counting/grouping: Tools combine multiple resources  
* **Use Prompts** to provide natural language entry points for common workflows  
  * Multi-step operations: `get_my_data()`

### MCP Resource Discovery

**`resources/list` returns (base URIs only):**

- `vana://files` (list of all files)  
- `vana://schemas` (list of all schemas)

**Individual resources (discovered dynamically):**

Via `vana://files`:

- `vana://file/{id}` \- Individual file content  
- `vana://file/{id}/metadata` \- Individual file metadata

Via `vana://schemas`:

- `vana://schema/{id}` \- Individual schema definition

**`resources/read` supports:**

- **Static URIs**: `vana://file/123`, `vana://schema/5`  
- **List URIs with query params**: `vana://files?schema_ids=1,2,3`, `vana://schemas?query=chatgpt`  
- Tools construct filtered URIs dynamically based on user queries

### Pagination Contract

All list operations use consistent pagination:

* **Default**: `limit=10`, `offset=0`  
* **Maximum**: `limit=100`  
* **Response format**: `{items: [...], limit: L, offset: O}`  
* **Strategy**: Offset-based (not cursor-based)
* **Note**: Total counts are not available from the subgraph query. To determine if there are more pages, check if `len(results) == limit` (if fewer results than limit, you've reached the end).

### File Structure

```
vana-personal-server/
├── mcp_server/
│   ├── __init__.py       # Package initialization
│   ├── server.py         # FastMCP instance, imports resources/tools/prompts
│   ├── auth_provider.py  # SignatureAuthProvider (FastMCP TokenVerifier)
│   ├── resources.py      # MCP resource handlers
│   ├── tools.py          # MCP tool handlers
│   └── prompts.py        # MCP prompt templates
├── app.py                 # Unified FastAPI app with MCP mounted
```

### Error Handling

**Error Response Format:**

All errors follow this structure:

```json
{
  "error": "error_code",
  "message": "Human-readable error description",
  "suggestions": ["Action user can take", "Alternative approach"]
}
```

**Common Errors:**

**`invalid_schema_id`**

```json
{
  "error": "invalid_schema_id",
  "message": "Schema ID 999 does not exist in the network",
  "suggestions": ["Call list_schemas() to see available schemas"]
}
```

**`decryption_failed`**

```json
{
  "error": "decryption_failed",
  "message": "Unable to decrypt file 123. Check permissions.",
  "suggestions": [
    "Verify the personal server has permission to decrypt this file",
    "Check file metadata for schema and permission details"
  ]
}
```

**`file_too_large`**

```json
{
  "error": "file_too_large",
  "message": "File 123 is 500KB, exceeds token limit",
  "suggestions": [
    "Use filter parameter: get_file(file_id=123, filter='$.messages[0:10]')",
    "Request specific sections of the file"
  ]
}
```

**`invalid_filter`**

```json
{
  "error": "invalid_filter",
  "message": "JSONPath expression '$.invalid..syntax' is malformed",
  "suggestions": [
    "Read schema first: vana://schema/{schema_id}",
    "Common patterns: $.field, $[0:10], $[?(@.type=='value')]"
  ]
}
```

**`invalid_signature`**

```json
{
  "error": "invalid_signature",
  "message": "Unable to verify wallet signature from Authorization header",
  "suggestions": [
    "Check Authorization header contains valid EIP-191 signature",
    "Verify signature message is 'Vana Personal Server Auth Key'"
  ]
}
```

**`file_not_found`**

```json
{
  "error": "file_not_found",
  "message": "File 123 does not exist or you lack access",
  "suggestions": [
    "Call list_files() to see accessible files",
    "Verify file ID is correct"
  ]
}
```

### Performance Considerations

* File listing uses blockchain queries only (no decryption)  
* Schema definitions cached (rarely change)  
* File content decrypted on-demand only  
* Use `?filter={json_path}` to reduce token usage for large files  
* Pagination prevents large response sizes

### Security

* Only show files the user owns  
* File contents can only be decrypted with the personal server permissions, therefore this only works on files uploaded through the Vana App (for now)  
* MCP Authentication via signature verification, user signs a static message
