"""
MCP Prompt templates for Vana Personal Server.

Prompts are reusable templates for common workflows that guide the LLM
through multi-step operations.
"""


GET_MY_DATA_TEMPLATE = """I want to access my {data_type} data. Use the Vana MCP to discover and retrieve my {data_type} data, then show me what's available.

## Workflow

1. **Search for schemas**: Call `search_files_by_schema(query="{data_type}")` to find matching schemas and files

2. **Handle no results**: If no results, call `list_schemas()` and suggest similar data types to the user

3. **For each file found** (up to 3):
   - Call `get_file_metadata(file_id)` to check size and schema
   - Ask user if they want to see full content or summary
   - If user confirms, call `get_file(file_id)`
     - For large files (>10KB), first read the schema via `list_schemas()` to understand structure
     - Then use `?filter=` parameter to get specific sections (e.g., `?filter=$.messages[0:10]`)

4. **Present results**: Format content with context about the schema and what data is available

## Success Criteria

- User sees what {data_type} data they have
- User sees file count and dates
- User can access full or filtered content
- Data is presented in a readable format with schema context

## Error Handling

**If no schemas match:**
"I couldn't find any {data_type} data. You have data from: [list alternatives from list_schemas()]"

**If schemas found but no files:**
"{data_type} data exists in the network, but you haven't uploaded any yet. Would you like to learn how to upload {data_type} data to Vana?"

**If decryption fails:**
"Unable to decrypt file {{file_id}}. Please check that the personal server has permission to decrypt this file. You may need to grant access in the Vana app."

**If file is too large:**
"File {{file_id}} is very large ({{size}}KB). I recommend using a filter to get specific data. First, let me read the schema to understand the structure..."
[Then read schema and suggest filter options]

## Example Usage

User: "Using this prompt, get my chatgpt data"
"""