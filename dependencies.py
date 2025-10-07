"""
Dependency injection configuration for FastAPI.
"""

import logging
from functools import lru_cache
from typing import Annotated, Dict

logger = logging.getLogger(__name__)

from fastapi import Depends
from compute.base import BaseCompute
from compute.replicate import ReplicateLlmInference
from services.operations import OperationsService
from services.identity import IdentityService
from onchain.chain import Chain, get_chain
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
    try:
        from compute.local_inference import LocalLlmInference
        logger.info("Using Local Inference for complete privacy")
        return LocalLlmInference()
    except ImportError:
        logger.warning("Local inference not available, falling back to Replicate")
        return ReplicateLlmInference()

@lru_cache()
def get_openai_provider() -> BaseCompute:
    """Get OpenAI provider instance for ChatGPT integration."""
    try:
        from compute.openai_provider import create_openai_provider
        logger.info("Using OpenAI provider for ChatGPT integration")
        return create_openai_provider()
    except Exception as e:
        logger.warning(f"OpenAI provider not available: {e}, falling back to local inference")
        from compute.local_inference import LocalLlmInference
        return LocalLlmInference()

@lru_cache()
def get_multi_model_provider() -> Dict[str, BaseCompute]:
    """Get multiple model providers for orchestration."""
    providers = {}
    
    try:
        from compute.local_inference import LocalLlmInference
        providers["local"] = LocalLlmInference()
        logger.info("Local inference provider available")
    except ImportError:
        logger.warning("Local inference not available")
    
    try:
        from compute.replicate import ReplicateLlmInference
        providers["replicate"] = ReplicateLlmInference()
        logger.info("Replicate provider available")
    except ImportError:
        logger.warning("Replicate provider not available")
    
    try:
        from compute.openai_provider import create_openai_provider
        providers["openai"] = create_openai_provider()
        logger.info("OpenAI provider available")
    except Exception as e:
        logger.warning(f"OpenAI provider not available: {e}")
    
    if not providers:
        raise RuntimeError("No compute providers available")
    
    logger.info(f"Multi-model provider initialized with {len(providers)} providers: {list(providers.keys())}")
    return providers


# Chain dependency
def get_chain_dependency(settings: Annotated[Settings, Depends(get_settings_dependency)]) -> Chain:
    """Get blockchain chain configuration based on settings."""
    return get_chain(settings.chain_id)


# Operations service dependency
def get_operations_service(
    compute: Annotated[BaseCompute, Depends(get_compute_provider)],
    chain: Annotated[Chain, Depends(get_chain_dependency)]
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
ChainDep = Annotated[Chain, Depends(get_chain_dependency)]
OperationsServiceDep = Annotated[OperationsService, Depends(get_operations_service)]
IdentityServiceDep = Annotated[IdentityService, Depends(get_identity_service)]
IPFSHealthDep = Annotated[dict, Depends(check_ipfs_health)]