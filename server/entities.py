from dataclasses import dataclass


@dataclass
class PersonalServerRequest:
    user_address: str
    file_ids: set[int]
    operation: str
    parameters: dict


@dataclass
class AccessPermissionsResponse:
    app_address: str
    file_ids: set[int]
    operation: str
    parameters: dict


@dataclass
class FileMetadata:
    file_id: int
    owner_address: str
    public_url: str
    encrypted_key: str