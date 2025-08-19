"""Integration tests for JSON mode with ReplicateLlmInference."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from compute.replicate import ReplicateLlmInference
from compute.base import ExecuteResponse, GetResponse
from domain.entities import GrantFile
from utils.json_mode import ResponseFormat


class TestReplicateLlmInferenceJSONMode:
    """Integration tests for ReplicateLlmInference with JSON mode."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        mock = Mock()
        mock.replicate_api_token = "test_token"
        return mock

    @pytest.fixture
    def mock_client(self):
        """Mock Replicate client."""
        return Mock()

    @pytest.fixture
    def llm_inference(self, mock_settings, mock_client):
        """Create ReplicateLlmInference instance with mocks."""
        with patch('compute.replicate.get_settings', return_value=mock_settings):
            with patch('compute.replicate.replicate.Client', return_value=mock_client):
                return ReplicateLlmInference()

    def test_execute_with_json_mode(self, llm_inference, mock_client):
        """Test execute method with JSON mode enabled."""
        # Setup
        grant_file = GrantFile(
            grantee="0x123",
            operation="llm_inference",
            parameters={"prompt": "Analyze this data: {{data}}"}
        )
        files_content = ["file1 content", "file2 content"]
        response_format = {"type": "json_object"}
        
        # Mock prediction response
        mock_prediction = Mock()
        mock_prediction.id = "test-prediction-123"
        mock_prediction.created_at = "2024-01-01T00:00:00Z"
        mock_client.predictions.create.return_value = mock_prediction
        
        # Execute
        result = llm_inference.execute(grant_file, files_content, response_format)
        
        # Verify
        assert result.id == "test-prediction-123"
        assert result.created_at == "2024-01-01T00:00:00Z"
        
        # Check that prompt was modified for JSON mode
        call_args = mock_client.predictions.create.call_args
        prompt = call_args[1]["input"]["prompt"]
        assert "valid JSON" in prompt
        assert "JSON.parse()" in prompt
        
        # Check that response format was stored
        assert llm_inference._prediction_formats["test-prediction-123"] == response_format

    def test_execute_without_json_mode(self, llm_inference, mock_client):
        """Test execute method without JSON mode (text mode)."""
        # Setup
        grant_file = GrantFile(
            grantee="0x123",
            operation="llm_inference",
            parameters={"prompt": "Analyze this data: {{data}}"}
        )
        files_content = ["file1 content", "file2 content"]
        
        # Mock prediction response
        mock_prediction = Mock()
        mock_prediction.id = "test-prediction-456"
        mock_prediction.created_at = "2024-01-01T00:00:00Z"
        mock_client.predictions.create.return_value = mock_prediction
        
        # Execute without response_format
        result = llm_inference.execute(grant_file, files_content)
        
        # Verify
        assert result.id == "test-prediction-456"
        assert result.created_at == "2024-01-01T00:00:00Z"
        
        # Check that prompt was NOT modified
        call_args = mock_client.predictions.create.call_args
        prompt = call_args[1]["input"]["prompt"]
        assert "valid JSON" not in prompt
        assert "JSON.parse()" not in prompt
        
        # Check that no response format was stored
        assert "test-prediction-456" not in llm_inference._prediction_formats

    def test_get_with_json_mode_success(self, llm_inference, mock_client):
        """Test get method with JSON mode - successful parsing."""
        # Setup - store response format for this prediction
        prediction_id = "test-prediction-789"
        llm_inference._prediction_formats[prediction_id] = {"type": "json_object"}
        
        # Mock prediction response with JSON output
        mock_prediction = Mock()
        mock_prediction.id = prediction_id
        mock_prediction.status = "succeeded"
        mock_prediction.started_at = "2024-01-01T00:00:00Z"
        mock_prediction.completed_at = "2024-01-01T00:01:00Z"
        mock_prediction.output = '{"result": "success", "data": {"key": "value", "number": 42}}'
        mock_client.predictions.get.return_value = mock_prediction
        
        # Execute
        result = llm_inference.get(prediction_id)
        
        # Verify
        assert result.id == prediction_id
        assert result.status == "succeeded"
        
        # Check that JSON was parsed and re-serialized
        parsed_result = json.loads(result.result)
        assert parsed_result["result"] == "success"
        assert parsed_result["data"]["key"] == "value"
        assert parsed_result["data"]["number"] == 42
        
        # Check that response format was cleaned up
        assert prediction_id not in llm_inference._prediction_formats

    def test_get_with_json_mode_parse_failure(self, llm_inference, mock_client):
        """Test get method with JSON mode - parsing failure."""
        # Setup - store response format for this prediction
        prediction_id = "test-prediction-fail"
        llm_inference._prediction_formats[prediction_id] = {"type": "json_object"}
        
        # Mock prediction response with invalid JSON output
        mock_prediction = Mock()
        mock_prediction.id = prediction_id
        mock_prediction.status = "succeeded"
        mock_prediction.started_at = "2024-01-01T00:00:00Z"
        mock_prediction.completed_at = "2024-01-01T00:01:00Z"
        mock_prediction.output = "This is not valid JSON at all"
        mock_client.predictions.get.return_value = mock_prediction
        
        # Execute
        result = llm_inference.get(prediction_id)
        
        # Verify
        assert result.id == prediction_id
        assert result.status == "succeeded"
        
        # Check that error wrapper was created
        error_result = json.loads(result.result)
        assert error_result["error"] == "json_parse_failed"
        assert "error_message" in error_result
        assert "raw_response" in error_result
        
        # Check that response format was cleaned up
        assert prediction_id not in llm_inference._prediction_formats

    def test_get_with_json_mode_markdown_wrapped(self, llm_inference, mock_client):
        """Test get method with JSON wrapped in markdown."""
        # Setup - store response format for this prediction
        prediction_id = "test-prediction-markdown"
        llm_inference._prediction_formats[prediction_id] = {"type": "json_object"}
        
        # Mock prediction response with markdown-wrapped JSON
        mock_prediction = Mock()
        mock_prediction.id = prediction_id
        mock_prediction.status = "succeeded"
        mock_prediction.started_at = "2024-01-01T00:00:00Z"
        mock_prediction.completed_at = "2024-01-01T00:01:00Z"
        mock_prediction.output = '```json\n{"result": "wrapped", "valid": true}\n```'
        mock_client.predictions.get.return_value = mock_prediction
        
        # Execute
        result = llm_inference.get(prediction_id)
        
        # Verify
        assert result.id == prediction_id
        assert result.status == "succeeded"
        
        # Check that JSON was extracted from markdown and parsed
        parsed_result = json.loads(result.result)
        assert parsed_result["result"] == "wrapped"
        assert parsed_result["valid"] is True

    def test_get_without_json_mode(self, llm_inference, mock_client):
        """Test get method without JSON mode."""
        # Setup - no response format stored
        prediction_id = "test-prediction-text"
        
        # Mock prediction response
        mock_prediction = Mock()
        mock_prediction.id = prediction_id
        mock_prediction.status = "succeeded"
        mock_prediction.started_at = "2024-01-01T00:00:00Z"
        mock_prediction.completed_at = "2024-01-01T00:01:00Z"
        mock_prediction.output = "This is plain text output"
        mock_client.predictions.get.return_value = mock_prediction
        
        # Execute
        result = llm_inference.get(prediction_id)
        
        # Verify
        assert result.id == prediction_id
        assert result.status == "succeeded"
        assert result.result == "This is plain text output"

    def test_get_with_list_output(self, llm_inference, mock_client):
        """Test get method with list output (common Replicate response format)."""
        # Setup
        prediction_id = "test-prediction-list"
        llm_inference._prediction_formats[prediction_id] = {"type": "json_object"}
        
        # Mock prediction response with list output
        mock_prediction = Mock()
        mock_prediction.id = prediction_id
        mock_prediction.status = "succeeded"
        mock_prediction.started_at = "2024-01-01T00:00:00Z"
        mock_prediction.completed_at = "2024-01-01T00:01:00Z"
        # Replicate often returns output as a list of strings
        mock_prediction.output = ['{"result":', ' "success",', ' "data":', ' {"key":', ' "value"}}']
        mock_client.predictions.get.return_value = mock_prediction
        
        # Execute
        result = llm_inference.get(prediction_id)
        
        # Verify
        assert result.id == prediction_id
        assert result.status == "succeeded"
        
        # Check that list was joined and JSON was parsed
        parsed_result = json.loads(result.result)
        assert parsed_result["result"] == "success"
        assert parsed_result["data"]["key"] == "value"

    def test_response_format_cleanup_on_failure(self, llm_inference, mock_client):
        """Test that response format is cleaned up on prediction failure."""
        # Setup
        prediction_id = "test-prediction-failed"
        llm_inference._prediction_formats[prediction_id] = {"type": "json_object"}
        
        # Mock failed prediction
        mock_prediction = Mock()
        mock_prediction.id = prediction_id
        mock_prediction.status = "failed"
        mock_prediction.started_at = "2024-01-01T00:00:00Z"
        mock_prediction.completed_at = "2024-01-01T00:01:00Z"
        mock_prediction.output = None
        mock_client.predictions.get.return_value = mock_prediction
        
        # Execute
        result = llm_inference.get(prediction_id)
        
        # Verify
        assert result.id == prediction_id
        assert result.status == "failed"
        assert result.result is None
        
        # Check that response format was cleaned up
        assert prediction_id not in llm_inference._prediction_formats

    def test_response_format_cleanup_on_cancel(self, llm_inference, mock_client):
        """Test that response format is cleaned up on prediction cancellation."""
        # Setup
        prediction_id = "test-prediction-canceled"
        llm_inference._prediction_formats[prediction_id] = {"type": "json_object"}
        
        # Mock canceled prediction
        mock_prediction = Mock()
        mock_prediction.id = prediction_id
        mock_prediction.status = "canceled"
        mock_prediction.started_at = "2024-01-01T00:00:00Z"
        mock_prediction.completed_at = None
        mock_prediction.output = None
        mock_client.predictions.get.return_value = mock_prediction
        
        # Execute
        result = llm_inference.get(prediction_id)
        
        # Verify
        assert result.id == prediction_id
        assert result.status == "canceled"
        assert result.result is None
        
        # Check that response format was cleaned up
        assert prediction_id not in llm_inference._prediction_formats

    def test_prompt_truncation_with_json_mode(self, llm_inference, mock_client):
        """Test that prompt truncation still works with JSON mode."""
        # Setup
        grant_file = GrantFile(
            grantee="0x123",
            operation="llm_inference",
            parameters={"prompt": "Analyze: {{data}}"}
        )
        # Create very large content that will be truncated
        files_content = ["x" * 100000]  # Very large content
        response_format = {"type": "json_object"}
        
        # Mock prediction response
        mock_prediction = Mock()
        mock_prediction.id = "test-prediction-truncate"
        mock_prediction.created_at = "2024-01-01T00:00:00Z"
        mock_client.predictions.create.return_value = mock_prediction
        
        # Execute
        result = llm_inference.execute(grant_file, files_content, response_format)
        
        # Verify
        assert result.id == "test-prediction-truncate"
        
        # Check that prompt includes both truncation and JSON enforcement
        call_args = mock_client.predictions.create.call_args
        prompt = call_args[1]["input"]["prompt"]
        assert "DATA TRUNCATED" in prompt
        assert "valid JSON" in prompt