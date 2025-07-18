from dataclasses import dataclass
from typing import Any, List, Optional
from datetime import datetime
from enum import Enum

class OperationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Operation:
    id: str
    status: OperationStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Optional[str] = None
    prediction_id: Optional[str] = None

@dataclass
class ExecuteRequest:
    permission_grant: str

@dataclass
class OperationCreated:
    id: str
    created_at: str
    links: dict

@dataclass
class PersonalServer:
    address: str
    public_key: str

@dataclass
class FileMetadata:
    file_id: int
    owner_address: str
    public_url: str
    encrypted_key: str


@dataclass
class GrantData:
    typedData: dict
    signature: str


@dataclass
class PermissionData:
    id: int
    grantor: str
    nonce: int
    grant: str
    signature: bytes
    is_active: bool
    file_ids: List[int]

@dataclass
class GrantFile:
    grantee: str
    operation: str
    parameters: dict[str, Any]
    expires: Optional[int] = None

@dataclass
class PersonalServerRequest:
    permission_id: int