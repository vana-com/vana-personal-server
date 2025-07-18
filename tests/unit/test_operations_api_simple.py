import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from api.operations import router

# Create test client
client = TestClient(router)

class TestOperationsAPISimple:
    """Simple test cases for the operations API endpoints."""
    
    def test_create_operation_success(self):
        """Test successful operation creation."""
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
            
            # Make request
            response = client.post("/operations", json=mock_request)
            
            # Assertions
            assert response.status_code == 202
            data = response.json()
            assert data["id"] == "test-prediction-id-123"
            assert data["created_at"] == "2024-01-01T00:00:00Z"
            
            # Verify service was called with correct parameters
            mock_service.create.assert_called_once_with(
                request_json=mock_request["operation_request_json"],
                signature=mock_request["app_signature"]
            )
    
    def test_create_operation_service_error(self):
        """Test operation creation when service raises exception."""
        mock_request = {
            "app_signature": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1b",
            "operation_request_json": '{"permission_id": 1, "app_address": "0xd7Ae9319049f0B6cA9AD044b165c5B4F143EF451"}'
        }
        
        with patch('api.operations.operations_service') as mock_service:
            # Configure mock to raise exception
            mock_service.create.side_effect = Exception("Service error")
            
            # Make request
            response = client.post("/operations", json=mock_request)
            
            # Assertions
            assert response.status_code == 500
            data = response.json()
            assert data["detail"] == "Service error"
    
    def test_get_operation_success(self):
        """Test successful operation retrieval."""
        operation_id = "test-prediction-id-123"
        
        mock_prediction_response = Mock()
        mock_prediction_response.id = operation_id
        mock_prediction_response.status = "succeeded"
        mock_prediction_response.started_at = "2024-01-01T00:00:00Z"
        mock_prediction_response.completed_at = "2024-01-01T00:01:00Z"
        mock_prediction_response.output = "Operation completed successfully"
        
        with patch('api.operations.operations_service') as mock_service:
            # Configure the mock
            mock_service.get.return_value = mock_prediction_response
            
            # Make request
            response = client.get(f"/operations/{operation_id}")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == operation_id
            assert data["status"] == "succeeded"
            assert data["started_at"] == "2024-01-01T00:00:00Z"
            assert data["finished_at"] == "2024-01-01T00:01:00Z"
            assert data["result"] == "Operation completed successfully"
            
            # Verify service was called
            mock_service.get.assert_called_once_with(operation_id)
    
    def test_get_operation_not_found(self):
        """Test operation retrieval when operation doesn't exist."""
        operation_id = "non-existent-id"
        
        with patch('api.operations.operations_service') as mock_service:
            # Configure mock to raise exception
            mock_service.get.side_effect = Exception("Operation not found")
            
            # Make request
            response = client.get(f"/operations/{operation_id}")
            
            # Assertions
            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "Operation not found"
    
    def test_cancel_operation_success(self):
        """Test successful operation cancellation."""
        operation_id = "test-prediction-id-123"
        
        with patch('api.operations.operations_service') as mock_service:
            # Configure the mock
            mock_service.cancel.return_value = True
            
            # Make request
            response = client.post(f"/operations/cancel?operation_id={operation_id}")
            
            # Assertions
            assert response.status_code == 204
            
            # Verify service was called
            mock_service.cancel.assert_called_once_with(operation_id)
    
    def test_cancel_operation_not_found(self):
        """Test operation cancellation when operation doesn't exist."""
        operation_id = "non-existent-id"
        
        with patch('api.operations.operations_service') as mock_service:
            # Configure mock to return False (operation not found)
            mock_service.cancel.return_value = False
            
            # Make request
            response = client.post(f"/operations/cancel?operation_id={operation_id}")
            
            # Assertions
            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "Operation not found"
    
    def test_create_operation_invalid_request(self):
        """Test operation creation with invalid request data."""
        invalid_request = {
            "app_signature": "invalid-signature",
            "operation_request_json": "invalid-json"
        }
        
        # Make request
        response = client.post("/operations", json=invalid_request)
        
        # Should return validation error
        assert response.status_code == 422 