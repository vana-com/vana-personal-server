# **Vana Personal Server Documentation Style Guide**

**Objective:** Ensure the Vana Personal Server API maintains consistently clear, precise documentation that enables both auto-generated OpenAPI specs and readable code. This is the canonical guide for all documentation within the server codebase.

## 1. Guiding Philosophy: The Contract and The Implementation

We maintain two levels of documentation with distinct purposes:

- **The OpenAPI Specification is the Contract.** It defines the exact API surface, data shapes, and behaviors that clients depend on.
- **The Code Documentation is the Implementation Guide.** It explains internal logic, edge cases, and operational details for maintainers.

Every docstring and Field annotation must serve both automated tooling and human developers. We prioritize precision and completeness over brevity.

## 2. Our Audience

When writing documentation, you are writing for:

- **The API Consumer:** Needs exact request/response schemas, status codes, and error conditions. They will generate client SDKs from our OpenAPI.
- **The Integrator:** Needs to understand data flow, authentication requirements, and operational limits.
- **The Maintainer:** Needs to understand implementation decisions, performance considerations, and system dependencies.

## 3. The Standardized Documentation Structure

### **For Pydantic Models (Schemas)**

Every field must use `Field()` with complete metadata for OpenAPI generation:

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class CreateOperationRequest(BaseModel):
    """Request payload for creating a new operation."""
    
    app_signature: str = Field(
        description="ECDSA signature over operation_request_json using app's private key",
        example="0x3cffa64411a02d4a257663848df70fd445f513edcbb78a2e94495af45987e2de...",
        pattern="^0x[a-fA-F0-9]{130}$",  # For hex signatures
        min_length=132,
        max_length=132
    )
    
    operation_request_json: str = Field(
        description=(
            "JSON-encoded operation request containing permission_id and optional parameters. "
            "The operation type and parameters are defined in the grant file referenced by "
            "the blockchain permission."
        ),
        example='{"permission_id": 1024, "params": {"model": "deepseek-v3"}}',
        min_length=2,
        max_length=10000
    )

    class Config:
        # Enhances OpenAPI schema generation
        schema_extra = {
            "example": {
                "app_signature": "0x3cffa64411a02d4a257663848df70fd445f513ed...",
                "operation_request_json": '{"permission_id": 1024}'
            }
        }
```

### **For Custom Types with Validation**

Document validation patterns explicitly:

```python
from typing import Annotated
from pydantic import BeforeValidator, Field

def validate_ethereum_address(value: str) -> str:
    """
    Validate EIP-55 checksum EVM address format.
    
    Args:
        value: Address string to validate
        
    Returns:
        Validated address string
        
    Raises:
        ValueError: If address format is invalid (not 40 hex chars with 0x prefix)
    """
    if not re.match(r'^0x[a-fA-F0-9]{40}$', value):
        raise ValueError(f"Invalid EVM address format: {value}")
    # TODO: Add EIP-55 checksum validation
    return value

EVMAddress = Annotated[
    str,
    BeforeValidator(validate_ethereum_address),
    Field(
        description="EIP-55 checksum EVM address (20 bytes, 0x-prefixed)",
        example="0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4",
        pattern="^0x[a-fA-F0-9]{40}$"
    )
]
```

### **For Response Models**

Include all metadata needed for clear API documentation:

```python
class GetOperationResponse(BaseModel):
    """Operation status and result information."""
    
    kind: Literal["OperationStatus"] = Field(
        default="OperationStatus",
        description="Resource type identifier for response routing",
        example="OperationStatus"
    )
    
    id: str = Field(
        description="Unique operation identifier returned from create operation",
        example="cm4xp9qkw0001qj0g8xqg8xqg"
    )
    
    status: Literal["starting", "processing", "succeeded", "failed", "canceled"] = Field(
        description=(
            "Current operation status. "
            "Transitions: starting -> processing -> (succeeded|failed|canceled)"
        ),
        example="processing"
    )
    
    started_at: Optional[datetime] = Field(
        default=None,
        description="ISO 8601 timestamp when operation began processing",
        example="2024-01-01T00:00:00Z"
    )
    
    result: Optional[str] = Field(
        default=None,
        description=(
            "Operation result data. Format depends on operation type. "
            "For LLM inference: generated text. "
            "For JSON mode: stringified JSON object."
        ),
        example="The analysis indicates...",
        max_length=1000000  # 1MB limit
    )
```

### **For FastAPI Routes**

Use comprehensive route documentation:

```python
from fastapi import APIRouter, HTTPException, status, Query, Path
from typing import Annotated

router = APIRouter(tags=["operations"])

@router.post(
    "/operations",
    summary="Create a new operation",
    description=(
        "Submit a new operation for asynchronous processing. "
        "Operations are validated against blockchain permissions before execution."
    ),
    response_model=CreateOperationResponse,
    responses={
        202: {
            "description": "Operation accepted and queued for processing",
            "content": {
                "application/json": {
                    "example": {
                        "kind": "OperationCreated",
                        "id": "cm4xp9qkw0001qj0g8xqg8xqg",
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                }
            }
        },
        400: {"description": "Invalid request format or parameters"},
        401: {"description": "Invalid signature or authentication failed"},
        403: {"description": "Permission denied for requested operation"},
        429: {"description": "Rate limit exceeded, retry after delay"},
        500: {"description": "Internal server error during operation creation"}
    },
    status_code=status.HTTP_202_ACCEPTED
)
async def create_operation(
    request: CreateOperationRequest,
    x_request_id: Annotated[Optional[str], Header()] = None
) -> CreateOperationResponse:
    """
    Create and queue a new operation for asynchronous processing.
    
    This endpoint:
    1. Validates the app signature against the operation request
    2. Verifies blockchain permissions for the requested operation
    3. Fetches and decrypts user data based on permissions
    4. Submits the operation to the appropriate compute backend
    
    Args:
        request: Operation creation request with signature and parameters
        x_request_id: Optional client-provided request ID for tracing
        
    Returns:
        CreateOperationResponse with operation ID for status polling
        
    Raises:
        HTTPException(400): Malformed request or invalid JSON
        HTTPException(401): Signature verification failed
        HTTPException(403): No valid permission for operation
        HTTPException(429): Rate limit exceeded
        HTTPException(500): Backend service unavailable
        
    Note:
        Operations are processed asynchronously. Use the returned operation_id
        with GET /operations/{operation_id} to poll for results.
    """
    # Implementation here
    pass
```

### **For Service/Utility Classes**

Use Google-style docstrings for internal classes:

```python
class ReplicateLlmInference(BaseCompute):
    """
    Replicate API provider for LLM inference operations.
    
    Handles:
        - Prompt template rendering with data injection
        - JSON mode enforcement for structured outputs
        - Token limit management and truncation
        - Asynchronous prediction lifecycle
    
    Attributes:
        client: Authenticated Replicate API client
        model_name: Target model identifier (default: deepseek-v3)
        _prediction_formats: Cache of response formats by prediction ID
        
    Configuration:
        MAX_PROMPT_CHAR_LIMIT: Maximum prompt size (75,000 chars ~25k tokens)
        PROMPT_DATA_SEPARATOR: Delimiter between data files in prompt
    """
    
    def _build_prompt(self, grant_file: GrantFile, files_content: list[str]) -> str:
        """
        Construct final prompt with data injection.
        
        Ensures data is always included by appending {{data}} placeholder
        if not present in template. Handles truncation when content exceeds
        model context limits.
        
        Args:
            grant_file: Permission grant with prompt template in parameters
            files_content: Decrypted file contents to inject
            
        Returns:
            Rendered prompt with data replacing {{data}} placeholder
            
        Note:
            If prompt template lacks {{data}}, it's automatically appended.
            Data is truncated with warning message if exceeding limits.
        """
        # Implementation
        pass
```

## 4. Voice & Style Guidelines

| Do | Don't |
|---|---|
| **Use present tense, active voice:** "Validates the signature" | Use past or passive: "The signature will be validated" |
| **Be explicit about types:** "Returns `str` containing JSON" | Be vague: "Returns the result" |
| **State limits and constraints:** "Maximum 5MB file size" | Omit operational limits |
| **Document state transitions:** "Status: pending → processing → completed" | Leave state machines undocumented |
| **Include format examples:** `pattern="^0x[a-fA-F0-9]{40}$"` | Describe formats in prose only |
| **Specify units:** "Timeout in milliseconds (default: 30000)" | Use ambiguous units: "timeout value" |

### Terminology Consistency

- **Operation:** An asynchronous computation task (not "job", "task", or "request")
- **Permission:** Blockchain-granted access rights (not "authorization" or "grant")
- **Personal Server:** The user's compute instance (not "node" or "worker")
- **Grant File:** IPFS-stored permission parameters (not "config" or "manifest")
- **$VANA:** The network token (always with $)

## 5. Error Documentation Standards

Always use typed exceptions with clear recovery guidance:

```python
class RelayerError(Exception):
    """
    Gasless transaction submission failed.
    
    Common causes:
        - Relayer service unavailable
        - User lacks relay credits
        - Transaction exceeds complexity limits
        
    Recovery:
        - Retry with exponential backoff
        - Fall back to direct transaction submission
        - Check relay service status endpoint
    """
    pass

# In route handlers:
if not signature_valid:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": "invalid_signature",
            "message": "Signature verification failed",
            "field": "app_signature",
            "hint": "Ensure signature is hex-encoded and uses correct message format"
        }
    )
```

## 6. OpenAPI Synchronization

### Generating OpenAPI from Code

```python
# scripts/generate_openapi.py
import json
import yaml
from app import app

def generate_openapi():
    """Generate OpenAPI spec with custom modifications."""
    schema = app.openapi()
    
    # Add custom server configuration
    schema["servers"] = [
        {"url": "https://server.vana.com/api/v1", "description": "Production"},
        {"url": "http://localhost:8000/api/v1", "description": "Local development"}
    ]
    
    # Enhance with custom examples
    if "paths" in schema:
        enhance_path_examples(schema["paths"])
    
    return schema

# Run: python scripts/generate_openapi.py > openapi.yaml
```

### Validating Schema Completeness

Every exported schema must have:
- ✅ Description in Field()
- ✅ Example value
- ✅ Validation pattern (where applicable)
- ✅ Min/max constraints (where applicable)
- ✅ Enum values for literals
- ✅ Format specification for dates/times

## 7. Testing Documentation

Documentation tests ensure examples work:

```python
# tests/test_documentation.py
import pytest
from fastapi.testclient import TestClient
from app import app

class TestDocumentationExamples:
    """Verify all OpenAPI examples are valid."""
    
    def test_operation_create_example(self):
        """Ensure create operation example is executable."""
        client = TestClient(app)
        
        # Use the exact example from the schema
        example_request = {
            "app_signature": "0x3cffa644...",
            "operation_request_json": '{"permission_id": 1024}'
        }
        
        response = client.post("/api/v1/operations", json=example_request)
        assert response.status_code in [202, 401]  # 401 expected with fake signature
```

## 8. Migration Path

To improve existing code documentation:

1. **Phase 1:** Add Field() annotations to all Pydantic models
2. **Phase 2:** Enhance route decorators with responses and descriptions  
3. **Phase 3:** Add comprehensive docstrings to service classes
4. **Phase 4:** Generate and validate OpenAPI spec matches manual version
5. **Phase 5:** Set up CI to enforce documentation standards

## 9. Review Checklist

Before committing code, ensure:

- [ ] All public Pydantic fields have Field() with description and example
- [ ] Custom validators have clear error messages
- [ ] Routes define all possible response codes with descriptions
- [ ] Complex business logic has explanatory docstrings
- [ ] Error messages include actionable recovery steps
- [ ] Generated OpenAPI spec validates without warnings
- [ ] Examples in documentation are tested and working

---

*This guide is a living document. Update it as patterns evolve, but maintain consistency across the codebase.*