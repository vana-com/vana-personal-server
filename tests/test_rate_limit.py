import pytest
import json
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, MagicMock


# Import settings to clear cache
from settings import get_settings
from utils.rate_limit import RateLimiter

class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        """Setup test environment with mocked rate limiter."""
        # Mock the Redis client to avoid real Redis calls
        with patch('utils.rate_limit.Redis') as mock_redis:
            # Create a mock rate limiter that tracks calls
            self.mock_results = {}
            self.call_counts = {}

            def mock_limit(identifier):
                # Track calls per identifier
                if identifier not in self.call_counts:
                    self.call_counts[identifier] = 0
                self.call_counts[identifier] += 1

                # Get limit based on identifier type
                if identifier.startswith("ip:"):
                    if "identity" in identifier or identifier in self.mock_results:
                        limit = self.mock_results.get(identifier, {}).get('limit', 5)
                    else:
                        limit = 5
                elif identifier.startswith("sig:"):
                    limit = 5
                else:
                    limit = 5

                # Calculate if allowed based on call count
                allowed = self.call_counts[identifier] <= limit
                remaining = max(0, limit - self.call_counts[identifier])

                # Return mock result
                result = Mock()
                result.allowed = allowed
                result.limit = limit
                result.remaining = remaining
                result.reset = int(time.time()) + 60
                return result

            # Create mock rate limiters
            mock_limiter = Mock()
            mock_limiter.limit = mock_limit

            with patch('utils.rate_limit.Ratelimit') as mock_ratelimit:
                mock_ratelimit.return_value = mock_limiter

                # Set environment variables
                monkeypatch.setenv('RATE_LIMIT_DEFAULT_RPM', '5')
                monkeypatch.setenv('RATE_LIMIT_IDENTITY_RPM', '5')
                monkeypatch.setenv('RATE_LIMIT_OPERATIONS_PER_HOUR', '3')
                monkeypatch.setenv('RATE_LIMIT_ENABLED', 'true')
                monkeypatch.setenv('UPSTASH_REDIS_REST_URL', 'https://test.upstash.io')
                monkeypatch.setenv('UPSTASH_REDIS_REST_TOKEN', 'test-token')

                # Clear caches
                get_settings.cache_clear()
                import utils.rate_limit
                utils.rate_limit._rate_limiter = None

                # Create fresh app instance
                from app import app
                self.client = TestClient(app)

                yield

                # Cleanup
                self.call_counts.clear()
                self.mock_results.clear()

    def test_identity_endpoint_rate_limiting(self):
        """Test rate limiting on identity endpoint."""
        address = "0xd7Ae9319049f0B6cA9AD044b165c5B4F143EF451"

        # Reset call counts for this test
        self.call_counts.clear()

        # Make requests up to the limit
        for i in range(5):
            response = self.client.get(f"/api/v1/identity?address={address}")
            assert response.status_code == 200, f"Request {i+1} should succeed"

        # This request should be rate limited
        response = self.client.get(f"/api/v1/identity?address={address}")
        assert response.status_code == 429
        data = response.json()
        assert data["detail"]["error_code"] == "RATE_LIMIT_ERROR"

        # Check rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"

    def test_operations_endpoint_rate_limiting(self):
        """Test rate limiting on operations endpoint."""
        # Reset call counts
        self.call_counts.clear()

        request_data = {
            "app_signature": "0x" + "1234567890abcdef" * 8 + "1b",
            "operation_request_json": json.dumps({"permission_id": 1})
        }

        # Mock the entire OperationsService.create method
        from compute.base import ExecuteResponse
        mock_response = ExecuteResponse(
            id="test-id",
            created_at="2024-01-01T00:00:00Z"
        )

        # Mock at the service instance level
        with patch('services.operations.OperationsService.create', return_value=mock_response) as mock_create:
            # Also mock the signature recovery to avoid authentication errors
            with patch('services.operations.OperationsService._recover_app_address', return_value="0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4"):

                # Override the limit for operations
                self.mock_results['ip:testclient'] = {'limit': 3}

                # Make requests up to the limit (3 per hour)
                for i in range(3):
                    response = self.client.post("/api/v1/operations", json=request_data)
                    assert response.status_code == 202, f"Request {i+1} should succeed, got {response.status_code}: {response.text}"

                    # Verify the mock was called
                    assert mock_create.called

                # This request should be rate limited
                response = self.client.post("/api/v1/operations", json=request_data)
                assert response.status_code == 429
                data = response.json()
                assert data["detail"]["error_code"] == "RATE_LIMIT_ERROR"

    def test_rate_limit_headers(self):
        """Test that rate limit headers are properly set."""
        address = "0xd7Ae9319049f0B6cA9AD044b165c5B4F143EF451"

        # Reset call counts
        self.call_counts.clear()

        # Exhaust rate limit
        for _ in range(6):
            response = self.client.get(f"/api/v1/identity?address={address}")

        # Last response should have rate limit headers
        assert response.status_code == 429
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert "Retry-After" in response.headers

        # Verify header values
        assert int(response.headers["X-RateLimit-Remaining"]) == 0
        # Handle float in Retry-After
        retry_after = float(response.headers["Retry-After"])
        assert retry_after >= 0


# Test without mocking Redis - just disable rate limiting
def test_rate_limiting_disabled(monkeypatch):
    """Test that requests work when rate limiting is disabled."""
    monkeypatch.setenv('RATE_LIMIT_ENABLED', 'false')

    # Clear caches
    get_settings.cache_clear()
    import utils.rate_limit
    utils.rate_limit._rate_limiter = None

    from app import app
    client = TestClient(app)

    address = "0xd7Ae9319049f0B6cA9AD044b165c5B4F143EF451"

    # Should be able to make many requests
    for i in range(10):
        response = client.get(f"/api/v1/identity?address={address}")
        assert response.status_code == 200, f"Request {i+1} should succeed when rate limiting is disabled"


# Simple integration test
def test_rate_limiting_whitelist(monkeypatch):
    """Test that whitelisted IPs bypass rate limiting."""
    # Whitelist the test client IP
    monkeypatch.setenv('RATE_LIMIT_WHITELIST_IPS', 'testclient')
    monkeypatch.setenv('RATE_LIMIT_IDENTITY_RPM', '2')

    # Clear caches
    get_settings.cache_clear()
    import utils.rate_limit
    utils.rate_limit._rate_limiter = None

    from app import app
    client = TestClient(app)

    address = "0xd7Ae9319049f0B6cA9AD044b165c5B4F143EF451"

    # Should be able to make many requests
    for i in range(10):
        response = client.get(f"/api/v1/identity?address={address}")
        assert response.status_code == 200, f"Whitelisted IP should not be rate limited"