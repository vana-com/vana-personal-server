import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from api.identity import router
from domain.value_objects import PersonalServer

# Create test client
client = TestClient(router)

class TestIdentityAPISimple:
    """Simple test cases for the identity API endpoints."""
    
    def test_get_identity_success(self):
        """Test successful identity derivation."""
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
            
            # Make request
            response = client.get(f"/identity?address={mock_user_address}")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["user_address"] == mock_user_address
            assert data["personal_server"]["address"] == mock_server_address
            assert data["personal_server"]["public_key"] == mock_public_key
            
            # Verify service was called with correct parameters
            mock_service.derive_server_identity.assert_called_once_with(mock_user_address)
    
    def test_get_identity_service_error(self):
        """Test identity API when service raises exception."""
        mock_user_address = "0xd7Ae9319049f0B6cA9AD044b165c5B4F143EF451"
        
        with patch('api.identity.identity_service') as mock_service:
            # Configure mock to raise ValueError
            mock_service.derive_server_identity.side_effect = ValueError("Invalid address")
            
            # Make request and handle the exception
            try:
                response = client.get(f"/identity?address={mock_user_address}")
                # If we get here, the request succeeded but should have failed
                assert False, "Expected HTTPException but got success"
            except Exception as e:
                # Check if it's the expected HTTPException
                from fastapi.exceptions import HTTPException
                assert isinstance(e, HTTPException)
                assert e.status_code == 400
                assert e.detail == "Invalid address"
            
            # Verify service was called
            mock_service.derive_server_identity.assert_called_once_with(mock_user_address)
    
    def test_get_identity_missing_parameter(self):
        """Test identity API with missing address parameter."""
        try:
            response = client.get("/identity")
            # If we get here, the request succeeded but should have failed
            assert False, "Expected validation error but got success"
        except Exception as e:
            # Check if it's the expected validation error
            from fastapi.exceptions import RequestValidationError
            assert isinstance(e, RequestValidationError) 