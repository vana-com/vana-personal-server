"""
Domain value objects - Immutable objects defined by their values.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class PersonalServer:
    """Immutable personal server configuration."""
    address: str
    public_key: str
    private_key: str


@dataclass(frozen=True)
class GrantData:
    """Immutable grant data structure."""
    typedData: Dict[str, Any]
    signature: str


@dataclass(frozen=True)
class PersonalServerRequest:
    """Immutable request for personal server operations."""
    permission_id: int


@dataclass(frozen=True)
class ExecuteRequest:
    """Immutable request for operation execution."""
    permission_grant: str


@dataclass(frozen=True)
class OperationCreated:
    """Immutable response for operation creation."""
    id: str
    created_at: str
    links: Dict[str, Any]