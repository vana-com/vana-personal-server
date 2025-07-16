from dataclasses import dataclass
from typing import Any, Dict, Optional, List


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
    parameters: Dict[str, Any]
    expires: Optional[int] = None