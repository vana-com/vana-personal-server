from dataclasses import dataclass
from typing import Optional, List

# Import grant models for use in access permissions
from grants.grant_models import GrantFile


@dataclass
class PersonalServerRequest:
    permission_id: int

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