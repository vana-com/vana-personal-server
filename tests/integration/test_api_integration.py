import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app import app
from domain import PersonalServer

# Create test client for the full app
client = TestClient(app)

class TestAPIIntegration:
    """Integration tests for the full API."""
    
    def test_identity_endpoint_success(self):
        """Test successful identity endpoint through full app."""
        # Mock data
        mock_user_address = "0xd7Ae9319049f0B6cA9AD044b165c5B4F143EF451"
        mock_server_address = "0x35B8f61706f0D26d61c24F8293ea2095A803f845"
        mock_public_key = "0xe0ffb8d24a0532f26eede8db424e3d42706293a37a9b5938a92f7dadfa937781b9645d3f08bb77b2264a218f99c8004284036d4afa291815879c351585b7a8a3"
        
        # Mock the identity service
        with patch('api.identity.identity_service') as mock_service:
            # Create mock response
            mock_identity_response = Mock()
            mock_identity_response.user_address = mock_user_address
            mock_identity_response.personal_server = PersonalServer(
                address=mock_server_address,
                public_key=mock_public_key
            )
            
            # Configure the mock
            mock_service.derive_server_identity.return_value = mock_identity_response
            
            # Make request to full app
            response = client.get(f"/api/v1/identity?address={mock_user_address}")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["user_address"] == mock_user_address
            assert data["personal_server"]["address"] == mock_server_address
            assert data["personal_server"]["public_key"] == mock_public_key
    
    def test_identity_endpoint_failure(self):
        """Test identity endpoint failure through full app."""
        mock_user_address = "0xinvalid"
        
        with patch('api.identity.identity_service') as mock_service:
            # Configure mock to raise ValueError
            mock_service.derive_server_identity.side_effect = ValueError("Invalid address")
            
            # Make request to full app
            response = client.get(f"/api/v1/identity?address={mock_user_address}")
            
            # Assertions
            assert response.status_code == 400
            data = response.json()
            assert data["detail"] == "Invalid address"
    
    def test_operations_endpoint_success(self):
        """Test successful operations endpoint through full app."""
        # Mock data
        mock_request = {
            "app_signature": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1b",
            "operation_request_json": '{"permission_id": 1, "app_address": "0xd7Ae9319049f0B6cA9AD044b165c5B4F143EF451"}'
        }
        
        mock_prediction_response = Mock()
        mock_prediction_response.id = "test-prediction-id-123"
        mock_prediction_response.created_at = "2024-01-01T00:00:00Z"
        
        with patch('api.operations.operations_service') as mock_service:
            # Configure the mock
            mock_service.create.return_value = mock_prediction_response
            
            # Make request to full app
            response = client.post("/api/v1/operations", json=mock_request)
            
            # Assertions
            assert response.status_code == 202
            data = response.json()
            assert data["id"] == "test-prediction-id-123"
            assert data["created_at"] == "2024-01-01T00:00:00Z"
    
    def test_operations_endpoint_failure(self):
        """Test operations endpoint failure through full app."""
        mock_request = {
            "app_signature": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1b",
            "operation_request_json": '{"permission_id": 1, "app_address": "0xd7Ae9319049f0B6cA9AD044b165c5B4F143EF451"}'
        }
        
        with patch('api.operations.operations_service') as mock_service:
            # Configure mock to raise exception
            mock_service.create.side_effect = Exception("Service error")
            
            # Make request to full app
            response = client.post("/api/v1/operations", json=mock_request)
            
            # Assertions
            assert response.status_code == 500
            data = response.json()
            assert data["detail"] == "Service error"
    
    def test_api_health_check(self):
        """Test that the API is accessible."""
        # Test that we can reach the API root
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_invalid_endpoint(self):
        """Test invalid endpoint returns 404."""
        response = client.get("/api/v1/invalid")
        assert response.status_code == 404
    
    def test_identity_missing_parameter(self):
        """Test identity endpoint with missing parameter."""
        response = client.get("/api/v1/identity")
        assert response.status_code == 422  # Validation error
    
    def test_operations_invalid_json(self):
        """Test operations endpoint with invalid JSON."""
        response = client.post("/api/v1/operations", json={"invalid": "data"})
        assert response.status_code == 422  # Validation error 