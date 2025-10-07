import pytest
import os
import sys
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from api.operations import router as operations_router
from api.identity import router as identity_router
from fastapi import FastAPI

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create a test app with mocked dependencies
@pytest.fixture
def test_app():
    app = FastAPI()
    app.include_router(operations_router, prefix="/api/v1")
    app.include_router(identity_router, prefix="/api/v1")
    return app

@pytest.fixture
def operations_client(test_app):
    return TestClient(test_app)

@pytest.fixture
def identity_client(test_app):
    return TestClient(test_app)

@pytest.fixture
def mock_operations_service():
    """Mock operations service for testing."""
    service = Mock()
    service.create = AsyncMock()
    service.get = Mock()
    service.cancel = Mock()
    return service

@pytest.fixture
def mock_identity_service():
    """Mock identity service for testing."""
    service = Mock()
    service.derive_server_identity = Mock()
    return service

# Mock the dependencies
@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch, mock_operations_service, mock_identity_service):
    """Automatically mock dependencies for all tests."""
    
    # Mock the operations service dependency
    def mock_get_operations_service():
        return mock_operations_service
    
    # Mock the identity service dependency  
    def mock_get_identity_service():
        return mock_identity_service
    
    # Apply the mocks to the actual dependency functions
    monkeypatch.setattr("dependencies.get_operations_service", mock_get_operations_service)
    monkeypatch.setattr("dependencies.get_identity_service", mock_get_identity_service)
    
    # Also mock the compute provider to avoid real Replicate calls
    def mock_get_compute_provider():
        mock_compute = Mock()
        mock_compute.execute = Mock()
        mock_compute.get = Mock()
        mock_compute.cancel = Mock()
        return mock_compute
    
    monkeypatch.setattr("dependencies.get_compute_provider", mock_get_compute_provider)
    
    return {
        "operations_service": mock_operations_service,
        "identity_service": mock_identity_service
    }

@pytest.fixture
def valid_ethereum_address():
    """Valid Ethereum address for testing."""
    return "0xd7Ae9319049f0B6cA9AD044b165c5B4F143EF451"

@pytest.fixture
def invalid_ethereum_address():
    """Invalid Ethereum address for testing."""
    return "0xinvalid"

@pytest.fixture
def mock_prediction_response():
    """Mock prediction response for testing."""
    mock_response = Mock()
    mock_response.id = "test-prediction-id-123"
    mock_response.status = "succeeded"
    mock_response.created_at = "2024-01-01T00:00:00Z"
    mock_response.started_at = "2024-01-01T00:00:00Z"
    mock_response.completed_at = "2024-01-01T00:01:00Z"
    mock_response.output = "Operation completed successfully"
    return mock_response 