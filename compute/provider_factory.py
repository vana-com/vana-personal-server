"""
Compute provider factory for clean provider instantiation and routing.
Following SOLID principles and enabling extensibility without modification.
"""
from typing import Dict, Type, Optional, Protocol
from abc import ABC, abstractmethod
import logging

from compute.base import BaseCompute
from compute.replicate import ReplicateLlmInference
from compute.base_agent import BaseAgentProvider
from compute.qwen_agent import QwenCodeAgentProvider
from compute.gemini_agent import GeminiAgentProvider

logger = logging.getLogger(__name__)


class ComputeProvider(Protocol):
    """Protocol defining the compute provider interface."""
    async def execute(self, *args, **kwargs) -> Dict:
        """Execute computation and return results."""
        ...


class ProviderRegistry:
    """
    Registry for compute providers following Open/Closed Principle.
    New providers can be added without modifying existing code.
    """
    
    def __init__(self):
        self._providers: Dict[str, Type[ComputeProvider]] = {}
        self._instances: Dict[str, ComputeProvider] = {}
        self._initialize_default_providers()
    
    def _initialize_default_providers(self):
        """Register default providers."""
        self.register("llm_inference", ReplicateLlmInference)
        self.register("prompt_qwen_agent", QwenCodeAgentProvider)
        self.register("prompt_gemini_agent", GeminiAgentProvider)
    
    def register(self, operation_type: str, provider_class: Type[ComputeProvider]):
        """Register a new provider type."""
        self._providers[operation_type] = provider_class
        logger.info(f"Registered provider for operation: {operation_type}")
    
    def get_provider(self, operation_type: str) -> Optional[ComputeProvider]:
        """
        Get or create a provider instance for the given operation type.
        Uses singleton pattern for stateful providers (agents).
        """
        if operation_type not in self._providers:
            logger.warning(f"No provider registered for operation: {operation_type}")
            return None
        
        # Use singleton for agent providers to maintain state
        if operation_type.endswith("_agent"):
            if operation_type not in self._instances:
                self._instances[operation_type] = self._providers[operation_type]()
            return self._instances[operation_type]
        
        # Create new instance for stateless providers
        return self._providers[operation_type]()
    
    def supports_operation(self, operation_type: str) -> bool:
        """Check if an operation type is supported."""
        return operation_type in self._providers


class ComputeProviderFactory:
    """
    Factory for creating compute providers.
    Eliminates duplication and enables clean dependency injection.
    """
    
    def __init__(self, registry: Optional[ProviderRegistry] = None):
        self.registry = registry or ProviderRegistry()
    
    def create_provider(self, operation_type: str) -> Optional[ComputeProvider]:
        """
        Create a compute provider for the given operation type.
        
        Args:
            operation_type: The type of operation (e.g., "llm_inference", "prompt_qwen_agent")
            
        Returns:
            ComputeProvider instance or None if not supported
        """
        provider = self.registry.get_provider(operation_type)
        
        if not provider:
            logger.error(f"Unsupported operation type: {operation_type}")
            return None
        
        return provider
    
    def create_from_operation_id(self, operation_id: str) -> Optional[ComputeProvider]:
        """
        Create a provider based on operation ID prefix (for backward compatibility).
        This method exists for migration purposes and should be deprecated.
        
        Args:
            operation_id: Operation ID that may contain provider prefix
            
        Returns:
            ComputeProvider instance or None
        """
        # Map prefixes to operation types for backward compatibility
        prefix_mapping = {
            "qwen_": "prompt_qwen_agent",
            "gemini_": "prompt_gemini_agent",
            "replicate_": "llm_inference"
        }
        
        for prefix, operation_type in prefix_mapping.items():
            if operation_id.startswith(prefix):
                return self.create_provider(operation_type)
        
        # Default to LLM inference for unknown prefixes
        return self.create_provider("llm_inference")
    
    def register_provider(self, operation_type: str, provider_class: Type[ComputeProvider]):
        """
        Register a new provider type.
        Follows Open/Closed Principle - extend without modification.
        """
        self.registry.register(operation_type, provider_class)
    
    def supports_operation(self, operation_type: str) -> bool:
        """Check if an operation type is supported."""
        return self.registry.supports_operation(operation_type)


# Global factory instance for dependency injection
_global_factory = ComputeProviderFactory()


def get_compute_factory() -> ComputeProviderFactory:
    """Get the global compute provider factory."""
    return _global_factory


def register_custom_provider(operation_type: str, provider_class: Type[ComputeProvider]):
    """
    Register a custom provider with the global factory.
    Enables extending the system without modifying core code.
    
    Example:
        from my_custom_provider import CustomAgentProvider
        register_custom_provider("custom_agent", CustomAgentProvider)
    """
    _global_factory.register_provider(operation_type, provider_class)