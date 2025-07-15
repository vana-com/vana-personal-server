from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Union
import re


@dataclass
class GrantFile:
    """Represents a grant file with permission data"""

    grantee: str  # EVM address of the application authorized to use this grant
    operation: str  # Operation the grantee is authorized to perform
    parameters: Dict[str, Any]  # Operation-specific parameters
    expires: Optional[int] = None  # Optional Unix timestamp when grant expires


@dataclass
class GrantValidationOptions:
    """Options for grant validation"""

    schema: bool = True  # Enable JSON schema validation
    grantee: Optional[str] = None  # Grantee address to validate access for
    operation: Optional[str] = None  # Operation to validate permission for
    current_time: Optional[int] = None  # Override current time for expiry checking
    throw_on_error: bool = True  # Return detailed results instead of throwing


@dataclass
class GrantValidationResult:
    """Detailed validation result"""

    valid: bool
    errors: List[Dict[str, Any]]  # Validation errors encountered
    grant: Optional[GrantFile] = None  # The validated grant file (if validation passed)


class GrantValidationError(Exception):
    """Base error class for grant validation failures"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.name = "GrantValidationError"
        self.details = details or {}


class GrantExpiredError(GrantValidationError):
    """Error thrown when a grant has expired"""

    def __init__(self, message: str, expires: int, current_time: int):
        super().__init__(message, {"expires": expires, "currentTime": current_time})
        self.name = "GrantExpiredError"
        self.expires = expires
        self.current_time = current_time


class GranteeMismatchError(GrantValidationError):
    """Error thrown when grantee doesn't match requesting address"""

    def __init__(self, message: str, grantee: str, requesting_address: str):
        super().__init__(
            message, {"grantee": grantee, "requestingAddress": requesting_address}
        )
        self.name = "GranteeMismatchError"
        self.grantee = grantee
        self.requesting_address = requesting_address


class OperationNotAllowedError(GrantValidationError):
    """Error thrown when operation is not allowed by grant"""

    def __init__(self, message: str, granted_operation: str, requested_operation: str):
        super().__init__(
            message,
            {
                "grantedOperation": granted_operation,
                "requestedOperation": requested_operation,
            },
        )
        self.name = "OperationNotAllowedError"
        self.granted_operation = granted_operation
        self.requested_operation = requested_operation


class GrantSchemaError(GrantValidationError):
    """Error thrown when grant file structure is invalid"""

    def __init__(self, message: str, schema_errors: List[Any], invalid_data: Any):
        super().__init__(message, {"errors": schema_errors, "data": invalid_data})
        self.name = "GrantSchemaError"
        self.schema_errors = schema_errors
        self.invalid_data = invalid_data


def validate_grant_file_structure(data: Any) -> bool:
    """Basic validation of grant file structure"""
    if not data or not isinstance(data, dict):
        return False

    # Validate required fields
    if not isinstance(data.get("grantee"), str):
        return False

    # Validate grantee address format
    if not re.match(r"^0x[a-fA-F0-9]{40}$", data["grantee"]):
        return False

    if not isinstance(data.get("operation"), str) or len(data["operation"]) == 0:
        return False

    if not isinstance(data.get("parameters"), dict):
        return False

    # Validate optional expires field
    expires = data.get("expires")
    if expires is not None:
        if not isinstance(expires, int) or expires < 0:
            return False

    return True
