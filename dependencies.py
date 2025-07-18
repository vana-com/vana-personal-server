"""
Dependency injection configuration for FastAPI.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from compute.base import BaseCompute
from compute.replicate import ReplicateLlmInference
from services.operations import OperationsService
from services.identity import IdentityService
from onchain.chain import Chain, MOKSHA
from settings import Settings, get_settings
from utils.ipfs import test_gateway_availability


# Settings dependency
def get_settings_dependency() -> Settings:
    """Get application settings."""
    return get_settings()


# Compute provider dependency
@lru_cache()
def get_compute_provider() -> BaseCompute:
    """Get compute provider instance."""
    return ReplicateLlmInference()


# Chain dependency
@lru_cache()
def get_chain() -> Chain:
    """Get blockchain chain configuration."""
    return MOKSHA


# Operations service dependency
def get_operations_service(
    compute: Annotated[BaseCompute, Depends(get_compute_provider)],
    chain: Annotated[Chain, Depends(get_chain)]
) -> OperationsService:
    """Get operations service instance."""
    return OperationsService(compute, chain)


# Identity service dependency
@lru_cache()
def get_identity_service() -> IdentityService:
    """Get identity service instance."""
    return IdentityService()


# IPFS health check dependency
def check_ipfs_health() -> dict:
    """Check IPFS gateway availability for monitoring."""
    return test_gateway_availability(timeout=3)


# Type aliases for dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]
ComputeDep = Annotated[BaseCompute, Depends(get_compute_provider)]
ChainDep = Annotated[Chain, Depends(get_chain)]
OperationsServiceDep = Annotated[OperationsService, Depends(get_operations_service)]
IdentityServiceDep = Annotated[IdentityService, Depends(get_identity_service)]
IPFSHealthDep = Annotated[dict, Depends(check_ipfs_health)]