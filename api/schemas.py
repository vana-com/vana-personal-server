from typing import Annotated, Optional, Dict, Any, Literal, List
from pydantic import BaseModel, Field, BeforeValidator, validator
from datetime import datetime
import re
import json

def validate_evm_address(value: str) -> str:
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
        raise ValueError(f'Invalid EVM address format: {value} - must be 42 chars (0x + 40 hex)')
    # TODO: Add EIP-55 checksum validation
    return value

def validate_public_key(value: str) -> str:
    """
    Validate secp256k1 public key format (compressed or uncompressed).
    
    Args:
        value: Public key string to validate
        
    Returns:
        Validated public key string
        
    Raises:
        ValueError: If public key format is invalid
    """
    # Ethereum public keys can be:
    # - Compressed: 33 bytes (66 hex chars with 0x) - starts with 0x02 or 0x03
    # - Uncompressed: 65 bytes (130 hex chars with 0x) - starts with 0x04
    if not re.match(r'^0x[a-fA-F0-9]{64}$|^0x[a-fA-F0-9]{130}$', value):
        raise ValueError(
            f'Invalid public key format: {value} - '
            'must be 66 chars (compressed) or 132 chars (uncompressed) with 0x prefix'
        )
    return value

EVMAddress = Annotated[
    str,
    BeforeValidator(validate_evm_address),
    Field(
        description="EIP-55 checksum EVM address (20 bytes, 0x-prefixed)",
        example="0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4",
        pattern="^0x[a-fA-F0-9]{40}$"
    )
]

PublicKey = Annotated[
    str,
    BeforeValidator(validate_public_key),
    Field(
        description="SEC1 uncompressed secp256k1 public key (65 bytes, 0x04-prefixed, 130 hex chars)",
        example="0x04bcdf3e094f5c9a7819baedfabe81c235b8e6c8a5b26b62a98fa685deaac1e488090fa3c6b2667c1bf3a6e593bc0fb3e670f78a72e9fe0b1c40e2f9dda957f61a",
        pattern="^0x[a-fA-F0-9]{130}$"
    )
]

class IdentityRequestModel(BaseModel):
    """Request model for identity queries."""
    user_address: EVMAddress = Field(
        description="User's EVM wallet address to query identity for",
        example="0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4"
    )

class PersonalServerModel(BaseModel):
    """Personal server identity information."""
    kind: Literal["PersonalServer"] = Field(
        default="PersonalServer",
        description="Resource type identifier for response routing",
        example="PersonalServer"
    )
    address: EVMAddress = Field(
        description="Personal server's EVM wallet address",
        example="0x742d35Cc6558Fd4D9e9E0E888F0462ef6919Bd36"
    )
    public_key: PublicKey = Field(
        description="Personal server's public key for encryption (SEC1 uncompressed format)",
        example="0x04bcdf3e094f5c9a7819baedfabe81c235b8e6c8a5b26b62a98fa685deaac1e488090fa3c6b2667c1bf3a6e593bc0fb3e670f78a72e9fe0b1c40e2f9dda957f61a"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "kind": "PersonalServer",
                "address": "0x742d35Cc6558Fd4D9e9E0E888F0462ef6919Bd36",
                "public_key": "0x04bcdf3e094f5c9a7819baedfabe81c235b8e6c8a5b26b62a98fa685deaac1e488090fa3c6b2667c1bf3a6e593bc0fb3e670f78a72e9fe0b1c40e2f9dda957f61a"
            }
        }

class IdentityResponseModel(BaseModel):
    """Identity response containing user and personal server information."""
    kind: Literal["Identity"] = Field(
        default="Identity",
        description="Resource type identifier for response routing",
        example="Identity"
    )
    user_address: EVMAddress = Field(
        description="User's EVM wallet address",
        example="0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4"
    )
    personal_server: PersonalServerModel = Field(
        description="Personal server details for this user"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "kind": "Identity",
                "user_address": "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4",
                "personal_server": {
                    "kind": "PersonalServer",
                    "address": "0x742d35Cc6558Fd4D9e9E0E888F0462ef6919Bd36",
                    "public_key": "0x04bcdf3e094f5c9a7819baedfabe81c235b8e6c8a5b26b62a98fa685deaac1e488090fa3c6b2667c1bf3a6e593bc0fb3e670f78a72e9fe0b1c40e2f9dda957f61a"
                }
            }
        }

class CreateOperationRequest(BaseModel):
    """Request payload for creating a new operation."""
    app_signature: str = Field(
        description=(
            "ECDSA signature over operation_request_json using app's private key. "
            "Must be hex-encoded with 0x prefix (132 chars total)"
        ),
        example="0x3cffa64411a02d4a257663848df70fd445f513edcbb78a2e94495af45987e2de6144efdafd37a3d2b95e4e535c4a84fbcfb088d8052d435c382e7ca9a5ac57801c",
        pattern="^0x[a-fA-F0-9]{130}$",
        min_length=132,
        max_length=132
    )
    operation_request_json: str = Field(
        description=(
            "JSON-encoded operation request. Must contain permission_id. "
            "Can optionally include operation (for verification) and parameters (runtime values). "
            "Runtime parameters are merged with grant parameters (grant takes precedence)."
        ),
        example='{"permission_id": 1024, "parameters": {"goal": "analyze trends"}}',
        min_length=2,
        max_length=100000
    )

    @validator('operation_request_json')
    def validate_request_json(cls, v):
        """Validate operation_request_json structure."""
        try:
            data = json.loads(v)
            if not isinstance(data, dict):
                raise ValueError("operation_request_json must be a JSON object")
            if 'permission_id' not in data:
                raise ValueError("operation_request_json must contain 'permission_id'")
            return v
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in operation_request_json: {e}")
    
    class Config:
        json_schema_extra = {
            "example": {
                "app_signature": "0x3cffa64411a02d4a257663848df70fd445f513edcbb78a2e94495af45987e2de6144efdafd37a3d2b95e4e535c4a84fbcfb088d8052d435c382e7ca9a5ac57801c",
                "operation_request_json": '{"permission_id": 1024}'
            }
        }

class CreateOperationResponse(BaseModel):
    """Response after successfully creating an operation."""
    kind: Literal["OperationCreated"] = Field(
        default="OperationCreated",
        description="Resource type identifier for response routing",
        example="OperationCreated"
    )
    id: str = Field(
        description="Unique operation identifier for tracking and status queries",
        example="cm4xp9qkw0001qj0g8xqg8xqg"
    )
    created_at: str = Field(
        description="ISO 8601 timestamp when operation was created",
        example="2024-01-01T00:00:00Z"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "kind": "OperationCreated",
                "id": "cm4xp9qkw0001qj0g8xqg8xqg",
                "created_at": "2024-01-01T00:00:00Z"
            }
        }

class GetOperationResponse(BaseModel):
    """Operation status and result information."""
    kind: Literal["OperationStatus"] = Field(
        default="OperationStatus",
        description="Resource type identifier for response routing",
        example="OperationStatus"
    )
    id: str = Field(
        description="Unique operation identifier",
        example="cm4xp9qkw0001qj0g8xqg8xqg"
    )
    status: Literal["starting", "processing", "succeeded", "failed", "canceled"] = Field(
        description=(
            "Current operation status. "
            "Transitions: starting → processing → (succeeded|failed|canceled)"
        ),
        example="processing"
    )
    started_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp when operation began processing",
        example="2024-01-01T00:00:01Z"
    )
    finished_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp when operation completed (succeeded, failed, or canceled)",
        example="2024-01-01T00:00:05Z"
    )
    result: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Operation result data as a dictionary. Format depends on operation type. "
            "For LLM inference: {'output': 'generated text'} or parsed JSON object. "
            "For JSON mode: parsed JSON object structure."
        ),
        example={"output": "The analysis of your data indicates positive trends in engagement metrics..."}
    )

    class Config:
        json_schema_extra = {
            "example": {
                "kind": "OperationStatus",
                "id": "cm4xp9qkw0001qj0g8xqg8xqg",
                "status": "succeeded",
                "started_at": "2024-01-01T00:00:01Z",
                "finished_at": "2024-01-01T00:00:05Z",
                "result": {"output": "The analysis of your data indicates positive trends..."}
            }
        }

class ErrorResponse(BaseModel):
    """Standardized error response format."""
    kind: Literal["Error"] = Field(
        default="Error",
        description="Resource type identifier for error responses",
        example="Error"
    )
    detail: str = Field(
        description="Human-readable error message explaining what went wrong",
        example="Signature verification failed"
    )
    error_code: str = Field(
        description=(
            "Machine-readable error code for programmatic handling. "
            "Common codes: INVALID_SIGNATURE, PERMISSION_DENIED, NOT_FOUND, "
            "RATE_LIMIT_EXCEEDED, INTERNAL_SERVER_ERROR"
        ),
        example="INVALID_SIGNATURE"
    )
    field: Optional[str] = Field(
        default=None,
        description="Specific field that caused the error, if applicable",
        example="app_signature"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "kind": "Error",
                "detail": "Signature verification failed",
                "error_code": "INVALID_SIGNATURE",
                "field": "app_signature",
                "hint": "Ensure signature is hex-encoded with 0x prefix"
            }
        }

class ArtifactDownloadRequest(BaseModel):
    """Request model for authenticated artifact downloads."""
    operation_id: str = Field(
        description="Unique operation identifier",
        example="cm4xp9qkw0001qj0g8xqg8xqg"
    )
    artifact_path: str = Field(
        description="Path to the artifact file to download",
        example="outputs/result.json"
    )
    signature: str = Field(
        description="Ethereum signature of the request for authentication",
        pattern="^0x[a-fA-F0-9]{130}$",
        example="0x3cffa64411a02d4a257663848df70fd445f513edcbb78a2e94495af45987e2de6144efdafd37a3d2b95e4e535c4a84fbcfb088d8052d435c382e7ca9a5ac57801c"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "operation_id": "cm4xp9qkw0001qj0g8xqg8xqg",
                "artifact_path": "outputs/result.json",
                "signature": "0x3cffa64411a02d4a257663848df70fd445f513edcbb78a2e94495af45987e2de6144efdafd37a3d2b95e4e535c4a84fbcfb088d8052d435c382e7ca9a5ac57801c"
            }
        }

class ArtifactInfo(BaseModel):
    """Information about a single artifact file."""
    path: str = Field(
        description="Relative path to the artifact file",
        example="outputs/analysis.json"
    )
    size: int = Field(
        description="File size in bytes",
        example=4096
    )
    content_type: str = Field(
        description="MIME type of the artifact",
        example="application/json"
    )

class ArtifactListResponse(BaseModel):
    """Response containing list of available artifacts for an operation."""
    kind: Literal["ArtifactList"] = Field(
        default="ArtifactList",
        description="Resource type identifier for response routing",
        example="ArtifactList"
    )
    operation_id: str = Field(
        description="Unique operation identifier",
        example="cm4xp9qkw0001qj0g8xqg8xqg"
    )
    artifacts: List[ArtifactInfo] = Field(
        description="List of available artifacts for this operation",
        default=[]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "kind": "ArtifactList",
                "operation_id": "cm4xp9qkw0001qj0g8xqg8xqg",
                "artifacts": [
                    {
                        "path": "outputs/analysis.json",
                        "size": 4096,
                        "content_type": "application/json"
                    },
                    {
                        "path": "outputs/report.md",
                        "size": 2048,
                        "content_type": "text/markdown"
                    }
                ]
            }
        }
