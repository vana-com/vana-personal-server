"""
Compute provider registry for clean separation of concerns.
Implements factory pattern for extensible agent/compute provider management.
"""
import logging
from typing import Dict, Type, Optional
from compute.base import BaseCompute
from compute.replicate_llm_inference import ReplicateLlmInference
from compute.qwen_agent import QwenCodeAgentProvider
from compute.gemini_agent import GeminiAgentProvider

logger = logging.getLogger(__name__)


class ComputeProviderRegistry:
    """
    Registry for compute providers implementing factory pattern.
    
    This replaces hardcoded if/elif chains with a clean, extensible
    registration system following the Open/Closed principle.
    """
    
    def __init__(self):
        """Initialize the registry with default providers."""
        self._providers: Dict[str, Type[BaseCompute]] = {}
        self._register_default_providers()
    
    def _register_default_providers(self):
        """Register the default set of compute providers."""
        # LLM inference provider
        self.register("llm_inference", ReplicateLlmInference)
        
        # Agent providers
        self.register("prompt_qwen_agent", QwenCodeAgentProvider)
        self.register("prompt_gemini_agent", GeminiAgentProvider)
        
        logger.info(f"Registered {len(self._providers)} compute providers")
    
    def register(self, operation: str, provider_class: Type[BaseCompute]):
        """
        Register a compute provider for an operation type.
        
        Args:
            operation: Operation name (e.g., "llm_inference", "prompt_qwen_agent")
            provider_class: Class implementing BaseCompute interface
        """
        if not issubclass(provider_class, BaseCompute):
            raise ValueError(f"{provider_class} must implement BaseCompute interface")
        
        self._providers[operation] = provider_class
        logger.debug(f"Registered provider {provider_class.__name__} for operation '{operation}'")
    
    def get_provider(self, operation: str) -> Optional[BaseCompute]:
        """
        Get an instance of the compute provider for the given operation.
        
        Args:
            operation: Operation name
            
        Returns:
            Instance of compute provider or None if not found
        """
        provider_class = self._providers.get(operation)
        if provider_class:
            return provider_class()
        return None
    
    def has_provider(self, operation: str) -> bool:
        """Check if a provider is registered for the operation."""
        return operation in self._providers
    
    def list_operations(self) -> list[str]:
        """Get list of all registered operations."""
        return list(self._providers.keys())


# Global registry instance
_registry = None


def get_compute_registry() -> ComputeProviderRegistry:
    """Get the global compute provider registry (singleton)."""
    global _registry
    if _registry is None:
        _registry = ComputeProviderRegistry()
    return _registry