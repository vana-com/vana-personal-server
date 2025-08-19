"""Unit tests for JSON mode functionality."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from utils.json_mode import (
    JSONModeHandler,
    ResponseFormat,
    ResponseFormatConfig,
    create_json_mode_handler,
)


class TestJSONModeHandler:
    """Test suite for JSONModeHandler class."""

    def test_init_default_config(self):
        """Test initialization with default configuration."""
        handler = JSONModeHandler()
        assert handler.config.type == ResponseFormat.TEXT
        assert handler.config.strict_validation is True

    def test_init_custom_config(self):
        """Test initialization with custom configuration."""
        config = ResponseFormatConfig(
            type=ResponseFormat.JSON_OBJECT,
            strict_validation=False
        )
        handler = JSONModeHandler(config)
        assert handler.config.type == ResponseFormat.JSON_OBJECT
        assert handler.config.strict_validation is False

    def test_modify_prompt_for_json(self):
        """Test prompt modification for JSON mode."""
        handler = JSONModeHandler()
        original = "Please provide the data"
        
        modified = handler.modify_prompt_for_json(original)
        assert original in modified
        assert "valid JSON" in modified
        assert "JSON.parse()" in modified

    def test_extract_json_pure_json(self):
        """Test extraction from pure JSON response."""
        handler = JSONModeHandler()
        
        # Valid JSON object
        response = '{"key": "value", "number": 123}'
        result, error = handler.extract_json_from_response(response)
        assert result == {"key": "value", "number": 123}
        assert error is None
        
        # Valid JSON with whitespace
        response = '  \n  {"key": "value"}  \n  '
        result, error = handler.extract_json_from_response(response)
        assert result == {"key": "value"}
        assert error is None

    def test_extract_json_from_markdown(self):
        """Test extraction from markdown code blocks."""
        handler = JSONModeHandler()
        
        # JSON in markdown code block
        response = '```json\n{"key": "value", "number": 123}\n```'
        result, error = handler.extract_json_from_response(response)
        assert result == {"key": "value", "number": 123}
        assert error is None
        
        # JSON in generic code block
        response = '```\n{"key": "value"}\n```'
        result, error = handler.extract_json_from_response(response)
        assert result == {"key": "value"}
        assert error is None
        
        # With surrounding text
        response = 'Here is the JSON:\n```json\n{"result": true}\n```\nThat was the JSON.'
        result, error = handler.extract_json_from_response(response)
        assert result == {"result": True}
        assert error is None

    def test_extract_json_with_text(self):
        """Test extraction from response with surrounding text."""
        handler = JSONModeHandler()
        
        # JSON with prefix text
        response = 'The result is: {"key": "value", "number": 123}'
        result, error = handler.extract_json_from_response(response)
        assert result == {"key": "value", "number": 123}
        assert error is None
        
        # JSON with suffix text
        response = '{"key": "value"} // This is a comment'
        result, error = handler.extract_json_from_response(response)
        assert result == {"key": "value"}
        assert error is None

    def test_extract_json_with_comments(self):
        """Test extraction handling JSON with comments."""
        handler = JSONModeHandler()
        
        # Single-line comments
        response = '{"key": "value", // comment\n"number": 123}'
        result, error = handler.extract_json_from_response(response)
        # Should handle comment removal
        assert result is not None
        assert error is None
        
        # Multi-line comments
        response = '{"key": "value", /* comment */ "number": 123}'
        result, error = handler.extract_json_from_response(response)
        assert result is not None
        assert error is None

    def test_extract_json_malformed(self):
        """Test extraction from malformed JSON."""
        handler = JSONModeHandler()
        
        # Missing closing brace
        response = '{"key": "value"'
        result, error = handler.extract_json_from_response(response)
        assert result is None
        assert error is not None
        assert "Failed to extract valid JSON" in error
        
        # Not JSON at all
        response = 'This is just plain text'
        result, error = handler.extract_json_from_response(response)
        assert result is None
        assert error is not None
        
        # Empty response
        response = ''
        result, error = handler.extract_json_from_response(response)
        assert result is None
        assert error == "Response is empty or not a string"

    def test_validate_json_response(self):
        """Test JSON response validation."""
        handler = JSONModeHandler()
        
        # Valid non-empty dict
        assert handler.validate_json_response({"key": "value"}) is True
        
        # Empty dict with strict validation
        handler.config.strict_validation = True
        assert handler.validate_json_response({}) is False
        
        # Empty dict without strict validation
        handler.config.strict_validation = False
        assert handler.validate_json_response({}) is True
        
        # Not a dict
        assert handler.validate_json_response("string") is False
        assert handler.validate_json_response([1, 2, 3]) is False


    def test_process_response_text_mode(self):
        """Test response processing in text mode."""
        handler = JSONModeHandler()
        handler.config.type = ResponseFormat.TEXT
        
        response = "Plain text response"
        processed, error = handler.process_response(response)
        
        assert processed == "Plain text response"
        assert error is None

    def test_process_response_json_mode_success(self):
        """Test successful JSON mode processing."""
        handler = JSONModeHandler()
        handler.config.type = ResponseFormat.JSON_OBJECT
        
        response = '{"result": "success", "value": 42}'
        processed, error = handler.process_response(response)
        
        assert processed == {"result": "success", "value": 42}
        assert error is None

    def test_process_response_json_mode_failure(self):
        """Test JSON mode processing failure."""
        handler = JSONModeHandler()
        handler.config.type = ResponseFormat.JSON_OBJECT
        
        response = "Not valid JSON"
        processed, error = handler.process_response(response)
        
        assert processed == "Not valid JSON"
        assert error is not None
        assert "Failed to extract valid JSON" in error


class TestFactoryFunction:
    """Test suite for create_json_mode_handler factory function."""

    def test_create_default_handler(self):
        """Test creation with default settings."""
        handler = create_json_mode_handler()
        assert handler.config.type == ResponseFormat.TEXT
        
        handler = create_json_mode_handler(None)
        assert handler.config.type == ResponseFormat.TEXT

    def test_create_text_mode_handler(self):
        """Test creation with text mode."""
        handler = create_json_mode_handler({"type": "text"})
        assert handler.config.type == ResponseFormat.TEXT

    def test_create_json_mode_handler(self):
        """Test creation with JSON mode."""
        handler = create_json_mode_handler({"type": "json_object"})
        assert handler.config.type == ResponseFormat.JSON_OBJECT

    def test_create_with_json_object_uses_defaults(self):
        """Test that json_object mode uses internal defaults."""
        handler = create_json_mode_handler({
            "type": "json_object"
        })
        assert handler.config.type == ResponseFormat.JSON_OBJECT
        assert handler.config.strict_validation is True

    def test_create_with_invalid_type(self):
        """Test creation with invalid type defaults to text."""
        handler = create_json_mode_handler({"type": "invalid"})
        assert handler.config.type == ResponseFormat.TEXT


class TestEdgeCases:
    """Test suite for edge cases and complex scenarios."""

    def test_nested_json_extraction(self):
        """Test extraction of nested JSON structures."""
        handler = JSONModeHandler()
        
        response = '''{
            "outer": {
                "inner": {
                    "deep": "value"
                },
                "array": [1, 2, {"nested": true}]
            }
        }'''
        result, error = handler.extract_json_from_response(response)
        assert result["outer"]["inner"]["deep"] == "value"
        assert result["outer"]["array"][2]["nested"] is True
        assert error is None

    def test_unicode_handling(self):
        """Test handling of Unicode characters in JSON."""
        handler = JSONModeHandler()
        
        response = '{"emoji": "🚀", "chinese": "你好", "special": "café"}'
        result, error = handler.extract_json_from_response(response)
        assert result["emoji"] == "🚀"
        assert result["chinese"] == "你好"
        assert result["special"] == "café"
        assert error is None

    def test_large_json_handling(self):
        """Test handling of large JSON responses."""
        handler = JSONModeHandler()
        
        # Create a large JSON object
        large_obj = {f"key_{i}": f"value_{i}" for i in range(1000)}
        response = json.dumps(large_obj)
        
        result, error = handler.extract_json_from_response(response)
        assert len(result) == 1000
        assert result["key_500"] == "value_500"
        assert error is None

    def test_json_with_trailing_comma(self):
        """Test handling of JSON with trailing commas."""
        handler = JSONModeHandler()
        
        # Trailing comma (invalid JSON but common mistake)
        response = '{"key": "value", "number": 123,}'
        result, error = handler.extract_json_from_response(response)
        # Should fix the trailing comma
        assert result is not None
        assert error is None

    def test_multiple_json_objects(self):
        """Test extraction when multiple JSON objects are present."""
        handler = JSONModeHandler()
        
        # Multiple JSON objects - should extract first valid one
        response = 'First: {"first": true} Second: {"second": true}'
        result, error = handler.extract_json_from_response(response)
        # Should extract the first complete JSON object
        assert result is not None
        assert "first" in result  # Should get the first one
        assert error is None