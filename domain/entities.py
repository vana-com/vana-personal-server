"""
Domain entities - Core business objects with identity.
"""

from dataclasses import dataclass
from typing import Any, List, Optional
from datetime import datetime
from enum import Enum


class OperationStatus(Enum):
    """Status of an operation."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Operation:
    """Core operation entity with lifecycle management."""
    id: str
    status: OperationStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Optional[str] = None
    prediction_id: Optional[str] = None


@dataclass
class FileMetadata:
    """Metadata for encrypted files in the data registry."""
    file_id: int
    owner_address: str
    public_url: str
    encrypted_key: str


@dataclass
class PermissionData:
    """Permission data from blockchain."""
    id: int
    grantor: str
    nonce: int
    grantee_id: int
    grant: str
    start_block: int
    end_block: int
    file_ids: List[int]


@dataclass
class GrantFile:
    """Grant file configuration for operations."""
    grantee: str
    operation: str
    parameters: dict[str, Any]
    expires: Optional[int] = None