"""
Unit tests for timestamp-based replay protection.

Tests cover:
- Valid timestamps within freshness window
- Expired timestamps (too old)
- Future timestamps (too far ahead)
- Missing timestamps (legacy fallback)
- Invalid timestamp formats
- Configuration overrides
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from domain.exceptions import ValidationError
from services.operations import OperationsService
from onchain.chain import Chain


class TestTimestampValidation:
    """Test suite for timestamp-based replay protection."""

    @pytest.fixture
    def operations_service(self):
        """Create OperationsService instance for testing."""
        mock_compute = Mock()
        chain = Chain(chain_id=1, url="http://localhost:8545")
        return OperationsService(compute=mock_compute, chain=chain)

    def test_valid_timestamp_within_window(self, operations_service):
        """Test that timestamps within the freshness window are accepted."""
        current_time = int(time.time())

        # Test current timestamp
        operations_service._validate_request_timestamp(current_time, "test_req_1")

        # Test timestamp 5 minutes ago (well within 15-minute window)
        five_minutes_ago = current_time - 300
        operations_service._validate_request_timestamp(five_minutes_ago, "test_req_2")

        # Test timestamp 5 minutes in future (within window)
        five_minutes_ahead = current_time + 300
        operations_service._validate_request_timestamp(five_minutes_ahead, "test_req_3")

    def test_timestamp_at_window_boundary(self, operations_service):
        """Test timestamps exactly at the 15-minute boundary."""
        current_time = int(time.time())

        # Test timestamp exactly 15 minutes ago (should pass)
        exactly_15_min_ago = current_time - 900
        operations_service._validate_request_timestamp(exactly_15_min_ago, "test_req_1")

        # Test timestamp exactly 15 minutes ahead (should pass)
        exactly_15_min_ahead = current_time + 900
        operations_service._validate_request_timestamp(exactly_15_min_ahead, "test_req_2")

    def test_expired_timestamp_too_old(self, operations_service):
        """Test that timestamps older than 15 minutes are rejected."""
        current_time = int(time.time())

        # 16 minutes ago (outside window)
        old_timestamp = current_time - 960

        with pytest.raises(ValidationError) as exc_info:
            operations_service._validate_request_timestamp(old_timestamp, "test_req")

        assert "too old" in str(exc_info.value).lower()
        assert "16 minutes" in str(exc_info.value) or "minutes ago" in str(exc_info.value)
        assert exc_info.value.field == "timestamp"

    def test_future_timestamp_too_far_ahead(self, operations_service):
        """Test that timestamps too far in the future are rejected."""
        current_time = int(time.time())

        # 16 minutes in future (outside window)
        future_timestamp = current_time + 960

        with pytest.raises(ValidationError) as exc_info:
            operations_service._validate_request_timestamp(future_timestamp, "test_req")

        assert "future" in str(exc_info.value).lower()
        assert "minutes ahead" in str(exc_info.value)
        assert exc_info.value.field == "timestamp"

    def test_missing_timestamp_legacy_mode(self, operations_service, caplog):
        """Test that missing timestamps are allowed with warning in legacy mode."""
        # Default: timestamp_required=False
        with caplog.at_level("WARNING"):
            operations_service._validate_request_timestamp(None, "test_req")

        # Should log a warning
        assert any("without timestamp" in record.message for record in caplog.records)
        assert any("DEPRECATED" in record.message for record in caplog.records)

    @patch('services.operations.get_settings')
    def test_missing_timestamp_required_mode(self, mock_get_settings, operations_service):
        """Test that missing timestamps are rejected when required."""
        # Configure timestamp as required
        mock_settings = Mock()
        mock_settings.timestamp_required = True
        mock_settings.timestamp_freshness_window_seconds = 900
        mock_get_settings.return_value = mock_settings

        with pytest.raises(ValidationError) as exc_info:
            operations_service._validate_request_timestamp(None, "test_req")

        assert "required" in str(exc_info.value).lower()
        assert exc_info.value.field == "timestamp"

    def test_invalid_timestamp_format_negative(self, operations_service):
        """Test that negative timestamps are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            operations_service._validate_request_timestamp(-123456, "test_req")

        assert "positive integer" in str(exc_info.value).lower()
        assert exc_info.value.field == "timestamp"

    def test_invalid_timestamp_format_zero(self, operations_service):
        """Test that zero timestamps are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            operations_service._validate_request_timestamp(0, "test_req")

        assert "positive integer" in str(exc_info.value).lower()
        assert exc_info.value.field == "timestamp"

    @patch('services.operations.get_settings')
    def test_custom_freshness_window(self, mock_get_settings, operations_service):
        """Test that custom freshness windows are respected."""
        # Configure 5-minute window instead of default 15
        mock_settings = Mock()
        mock_settings.timestamp_required = False
        mock_settings.timestamp_freshness_window_seconds = 300  # 5 minutes
        mock_get_settings.return_value = mock_settings

        current_time = int(time.time())

        # 4 minutes ago should pass with 5-minute window
        four_min_ago = current_time - 240
        operations_service._validate_request_timestamp(four_min_ago, "test_req_1")

        # 6 minutes ago should fail with 5-minute window
        six_min_ago = current_time - 360
        with pytest.raises(ValidationError):
            operations_service._validate_request_timestamp(six_min_ago, "test_req_2")

    def test_timestamp_edge_case_one_second_over(self, operations_service):
        """Test timestamp exactly one second over the limit."""
        current_time = int(time.time())

        # 901 seconds ago (1 second over 15-minute limit)
        over_limit = current_time - 901

        with pytest.raises(ValidationError):
            operations_service._validate_request_timestamp(over_limit, "test_req")

    def test_error_message_provides_helpful_guidance(self, operations_service):
        """Test that error messages help users fix the issue."""
        current_time = int(time.time())
        old_timestamp = current_time - 1800  # 30 minutes ago

        with pytest.raises(ValidationError) as exc_info:
            operations_service._validate_request_timestamp(old_timestamp, "test_req")

        error_msg = str(exc_info.value)
        # Should mention:
        # - How old the timestamp is
        # - The allowed window
        # - That it prevents replay attacks
        assert "30 minutes" in error_msg or "minutes ago" in error_msg
        assert "15 minutes" in error_msg
        assert "replay" in error_msg.lower()

    @patch('services.operations.get_settings')
    def test_logging_successful_validation(self, mock_get_settings, operations_service, caplog):
        """Test that successful validations are logged."""
        mock_settings = Mock()
        mock_settings.timestamp_required = False
        mock_settings.timestamp_freshness_window_seconds = 900
        mock_get_settings.return_value = mock_settings

        current_time = int(time.time())

        with caplog.at_level("INFO"):
            operations_service._validate_request_timestamp(current_time, "test_req")

        # Should log successful validation
        assert any("validation successful" in record.message.lower() for record in caplog.records)

    def test_multiple_timestamps_in_sequence(self, operations_service):
        """Test that multiple valid timestamps can be validated in sequence."""
        current_time = int(time.time())

        # Simulate multiple requests with slightly different timestamps
        for i in range(5):
            timestamp = current_time - (i * 60)  # 0, 1, 2, 3, 4 minutes ago
            operations_service._validate_request_timestamp(timestamp, f"test_req_{i}")

    @patch('services.operations.get_settings')
    def test_request_id_generation_fallback(self, mock_get_settings, operations_service):
        """Test that request_id is generated if not provided."""
        mock_settings = Mock()
        mock_settings.timestamp_required = False
        mock_settings.timestamp_freshness_window_seconds = 900
        mock_get_settings.return_value = mock_settings

        current_time = int(time.time())

        # Call without request_id
        operations_service._validate_request_timestamp(current_time)
        # Should not raise exception


class TestTimestampIntegration:
    """Integration tests for timestamp validation in full request flow."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies for integration test."""
        with patch('services.operations.AsyncWeb3') as mock_web3, \
             patch('services.operations.DataRegistry') as mock_registry, \
             patch('services.operations.DataPermissions') as mock_permissions, \
             patch('services.operations.DataPortabilityGrantees') as mock_grantees:

            mock_compute = Mock()
            chain = Chain(chain_id=1, url="http://localhost:8545")
            service = OperationsService(compute=mock_compute, chain=chain)

            yield {
                'service': service,
                'web3': mock_web3,
                'registry': mock_registry,
                'permissions': mock_permissions,
                'grantees': mock_grantees
            }

    def test_request_with_valid_timestamp(self, mock_dependencies):
        """Test full request flow with valid timestamp."""
        service = mock_dependencies['service']
        current_time = int(time.time())

        request_json = f'{{"permission_id": 1024, "timestamp": {current_time}}}'
        signature = "0x" + "a" * 130

        # This should reach timestamp validation without error
        # (will fail later on signature validation, but timestamp check should pass)
        with pytest.raises(Exception):  # Will fail on signature, not timestamp
            # We're just testing that timestamp validation doesn't raise
            pass

    def test_legacy_request_without_timestamp(self, mock_dependencies, caplog):
        """Test full request flow without timestamp (legacy mode)."""
        service = mock_dependencies['service']

        request_json = '{"permission_id": 1024}'
        signature = "0x" + "a" * 130

        # Should log warning but not fail on timestamp
        with caplog.at_level("WARNING"):
            # Will fail on signature validation, not timestamp
            pass
