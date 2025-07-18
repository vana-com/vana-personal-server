"""
Domain layer - Core business logic and entities.

This module contains the core domain objects that represent the business concepts
of the Vana Personal Server system.
"""

# Export entities
from .entities import (
    Operation,
    OperationStatus,
    FileMetadata,
    PermissionData,
    GrantFile,
)

# Export value objects
from .value_objects import (
    PersonalServer,
    GrantData,
    PersonalServerRequest,
    ExecuteRequest,
    OperationCreated,
)

# Export exceptions
from .exceptions import (
    VanaAPIError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    BlockchainError,
    FileAccessError,
    ComputeError,
    DecryptionError,
    GrantValidationError,
    OperationError,
)

# For backward compatibility and convenience
__all__ = [
    # Entities
    "Operation",
    "OperationStatus", 
    "FileMetadata",
    "PermissionData",
    "GrantFile",
    
    # Value Objects
    "PersonalServer",
    "GrantData",
    "PersonalServerRequest",
    "ExecuteRequest",
    "OperationCreated",
    
    # Exceptions
    "VanaAPIError",
    "ValidationError",
    "AuthenticationError", 
    "AuthorizationError",
    "NotFoundError",
    "BlockchainError",
    "FileAccessError",
    "ComputeError",
    "DecryptionError",
    "GrantValidationError",
    "OperationError",
]