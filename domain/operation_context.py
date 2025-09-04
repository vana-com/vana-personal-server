"""Operation context to carry grantor and grantee information through the pipeline."""
from dataclasses import dataclass


@dataclass
class OperationContext:
    """Context for operation execution carrying ownership and access information.
    
    Attributes:
        operation_id: Unique identifier for the operation
        grantor: User who owns the data (for encryption)
        grantee: App with delegated access (for access control)
        permission_id: ID of the blockchain permission
    """
    operation_id: str
    grantor: str  # User who owns the data
    grantee: str  # App with delegated access
    permission_id: int