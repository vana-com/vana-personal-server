# Agent Integration Summary

## Question Answered

**Q: Will API requests with these permission grants properly route to gemini and/or qwen? Do we need to update Dockerfile or anything?**

**A: Yes, API requests will properly route to the correct agents. The Dockerfile has been updated to include the necessary CLI tools.**

## Routing Implementation

### 1. Operation Routing (services/operations.py)
The routing logic in `services/operations.py` correctly handles all agent operations:

```python
# Lines 173-188: Route based on operation type from grant file
if grant_file.operation == "prompt_qwen_agent":
    from compute.qwen_agent import QwenCodeAgentProvider
    agent_provider = QwenCodeAgentProvider()
elif grant_file.operation == "prompt_gemini_agent":
    from compute.gemini_agent import GeminiAgentProvider
    agent_provider = GeminiAgentProvider()
elif grant_file.operation == "agentic_task":
    # Backward compatibility for legacy operations
    from compute.qwen_agent import QwenCodeAgentProvider
    agent_provider = QwenCodeAgentProvider()
```

### 2. GET Request Routing
Operation status requests route based on the operation ID prefix:

```python
# Lines 204-213: Route GET requests by operation ID prefix
if operation_id.startswith("qwen_"):
    from compute.qwen_agent import QwenCodeAgentProvider
    agent_provider = QwenCodeAgentProvider()
elif operation_id.startswith("gemini_"):
    from compute.gemini_agent import GeminiAgentProvider
    agent_provider = GeminiAgentProvider()
```

## Dockerfile Updates

The Dockerfile has been updated to include:

1. **Node.js Runtime**: Required for both CLI tools
2. **Qwen Code CLI**: `@qwen-chat/qwen-code` package
3. **Gemini CLI**: `@google/gemini-cli` package

```dockerfile
# Install system dependencies and Node.js for agent CLIs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg \
    curl \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install agent CLI tools globally
RUN npm install -g @qwen-chat/qwen-code @google/gemini-cli
```

## API Flow

1. **Client Creates Grant File**:
   ```json
   {
     "grantee": "0x...",
     "operation": "prompt_qwen_agent",  // or "prompt_gemini_agent"
     "parameters": {
       "goal": "Analyze codebase and create documentation"
     }
   }
   ```

2. **Client Submits Operation Request**:
   ```json
   POST /operations
   {
     "app_signature": "0x...",
     "operation_request_json": "{\"permission_id\": 3072}"
   }
   ```

3. **Server Routes to Correct Agent**:
   - Validates permission on blockchain
   - Fetches and validates grant file
   - Routes based on `operation` field:
     - `prompt_qwen_agent` → QwenCodeAgentProvider
     - `prompt_gemini_agent` → GeminiAgentProvider
     - `agentic_task` → QwenCodeAgentProvider (legacy)

4. **Agent Executes Task**:
   - Creates secure workspace
   - Spawns CLI with proper authentication
   - Captures output and artifacts
   - Returns operation ID

5. **Client Polls for Results**:
   ```json
   GET /operations/{operation_id}
   ```
   - Routes based on operation ID prefix
   - Returns status and results

## Authentication Modes

Both agents support two authentication modes:

### Production Mode (API Keys)
- Qwen: Uses `QWEN_API_KEY`, `QWEN_API_URL`, `QWEN_MODEL_NAME`
- Gemini: Uses `GEMINI_API_KEY`

### Development Mode (OAuth)
- Qwen: Uses cached OAuth credentials
- Gemini: Uses Google OAuth credentials

## OpenAPI Documentation

The OpenAPI spec has been fully updated with:

1. **Grant File Schemas**:
   - `QwenAgentGrantFile`
   - `GeminiAgentGrantFile`

2. **Examples**:
   - Request examples for both agents
   - Complete workflow documentation
   - Comprehensive examples file at `/examples/agent_grant_examples.json`

## Verification Test

A test script (`test_agent_routing.py`) verifies:
- ✓ Qwen agent routing
- ✓ Gemini agent routing  
- ✓ Operation ID-based routing
- ✓ Legacy compatibility
- ✓ Dockerfile updates

All tests pass successfully.

## Environment Variables

Required environment variables for production:

```bash
# Qwen Agent (production)
QWEN_API_KEY=your-api-key
QWEN_API_URL=https://api.qwen.ai/v1
QWEN_MODEL_NAME=qwen-coder-32b

# Gemini Agent (production)
GEMINI_API_KEY=your-google-api-key

# Optional configuration
QWEN_TIMEOUT_SEC=180
QWEN_MAX_STDOUT_MB=2
GEMINI_TIMEOUT_SEC=180
GEMINI_MAX_STDOUT_MB=2
```

## Summary

✅ **API requests properly route** to the correct agent based on grant file operation type
✅ **Dockerfile updated** with Node.js and both CLI tools
✅ **Backward compatibility** maintained for legacy `agentic_task` operations
✅ **OpenAPI fully documented** with schemas and examples
✅ **Authentication supports** both development (OAuth) and production (API keys) modes