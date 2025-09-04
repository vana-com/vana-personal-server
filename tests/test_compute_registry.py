"""
Tests for compute provider registry (factory pattern).
"""
import pytest
from unittest.mock import Mock, MagicMock
from services.compute_registry import ComputeProviderRegistry
from compute.base import BaseCompute


class MockComputeProvider(BaseCompute):
    """Mock compute provider for testing."""
    
    async def execute(self, grant_file, files_content):
        return Mock(id="test_123", created_at="2024-01-01T00:00:00Z")
    
    async def get(self, prediction_id):
        return Mock(id=prediction_id, status="succeeded")
    
    async def cancel(self, prediction_id):
        return True


class TestComputeProviderRegistry:
    """Test compute provider registry functionality."""
    
    def test_registry_initialization(self):
        """Test registry initializes with default providers."""
        registry = ComputeProviderRegistry()
        
        # Check default providers are registered
        assert registry.has_provider("llm_inference")
        assert registry.has_provider("prompt_qwen_agent")
        assert registry.has_provider("prompt_gemini_agent")
    
    def test_register_provider(self):
        """Test registering a new provider."""
        registry = ComputeProviderRegistry()
        
        # Register new provider
        registry.register("test_operation", MockComputeProvider)
        
        assert registry.has_provider("test_operation")
        provider = registry.get_provider("test_operation")
        assert isinstance(provider, MockComputeProvider)
    
    def test_register_invalid_provider(self):
        """Test registering invalid provider raises error."""
        registry = ComputeProviderRegistry()
        
        # Try to register non-BaseCompute class
        class InvalidProvider:
            pass
        
        with pytest.raises(ValueError, match="must implement BaseCompute"):
            registry.register("invalid", InvalidProvider)
    
    def test_get_provider_returns_instance(self):
        """Test get_provider returns new instance each time."""
        registry = ComputeProviderRegistry()
        
        provider1 = registry.get_provider("llm_inference")
        provider2 = registry.get_provider("llm_inference")
        
        # Should be different instances
        assert provider1 is not provider2
        assert type(provider1) == type(provider2)
    
    def test_get_unknown_provider_returns_none(self):
        """Test getting unknown provider returns None."""
        registry = ComputeProviderRegistry()
        
        provider = registry.get_provider("unknown_operation")
        assert provider is None
    
    def test_list_operations(self):
        """Test listing all registered operations."""
        registry = ComputeProviderRegistry()
        
        operations = registry.list_operations()
        assert "llm_inference" in operations
        assert "prompt_qwen_agent" in operations
        assert "prompt_gemini_agent" in operations
        assert len(operations) >= 3
    
    def test_registry_extensibility(self):
        """Test registry can be extended without modifying core code."""
        registry = ComputeProviderRegistry()
        
        # Add multiple new providers
        class Provider1(MockComputeProvider):
            pass
        
        class Provider2(MockComputeProvider):
            pass
        
        registry.register("custom_op_1", Provider1)
        registry.register("custom_op_2", Provider2)
        
        # Verify they work
        p1 = registry.get_provider("custom_op_1")
        p2 = registry.get_provider("custom_op_2")
        
        assert isinstance(p1, Provider1)
        assert isinstance(p2, Provider2)
        assert p1 is not p2
    
    def test_registry_singleton_pattern(self):
        """Test global registry uses singleton pattern."""
        from services.compute_registry import get_compute_registry
        
        registry1 = get_compute_registry()
        registry2 = get_compute_registry()
        
        # Should be same instance
        assert registry1 is registry2
        
        # Changes to one affect the other
        registry1.register("singleton_test", MockComputeProvider)
        assert registry2.has_provider("singleton_test")