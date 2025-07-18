import pytest
import os
import sys
from unittest.mock import Mock

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with pytest.MonkeyPatch().context() as m:
        m.setenv("REPLICATE_API_TOKEN", "test_token")
        m.setenv("WALLET_MNEMONIC", "test test test test test test test test test test test junk")
        m.setenv("MNEMONIC_LANGUAGE", "english")
        yield

@pytest.fixture
def mock_identity_service():
    """Mock identity service for testing."""
    mock_service = Mock()
    return mock_service

@pytest.fixture
def mock_operations_service():
    """Mock operations service for testing."""
    mock_service = Mock()
    return mock_service

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