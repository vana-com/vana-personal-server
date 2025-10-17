"""
Operation context for request lifecycle tracking.

Provides a lightweight context object that flows through the operation pipeline,
carrying critical identity and permission information from API request through
execution and artifact storage.
"""
from dataclasses import dataclass


@dataclass
class OperationContext:
    """
    Context object carrying operation ownership and permission metadata.

    Flows through the entire operation lifecycle to enable:
    - Correct encryption (using grantor's keys)
    - Access control (verifying grantee permissions)
    - Audit logging (tracking who did what)
    - Artifact association (linking outputs to operations)

    Attributes:
        operation_id: Unique CUID identifier for this operation instance
        grantor: EVM address of the user who owns the data being processed
        grantee: EVM address of the app that was granted permission to process data
        permission_id: On-chain permission ID that authorizes this operation

    Usage:
        context = OperationContext(
            operation_id="cm4xp9qkw0001qj0g8xqg8xqg",
            grantor="0xUser...",
            grantee="0xApp...",
            permission_id=1024
        )
        # Pass to compute providers, artifact storage, etc.

    Note:
        Grantor and grantee addresses should be in EIP-55 checksum format.
        Permission ID must exist on-chain and be active.
    """
    operation_id: str  # CUID format
    grantor: str       # User EVM address (data owner)
    grantee: str       # App EVM address (delegated accessor)
    permission_id: int # On-chain permission identifier