"""Simplified unit tests for JSON mode functionality with json_repair."""

import pytest
from utils.json_mode import (
    JSONModeHandler,
    ResponseFormat,
    ResponseFormatConfig,
    create_json_mode_handler,
)


class TestJSONModeHandler:
    """Essential tests for JSONModeHandler."""

    def test_init_and_config(self):
        """Test initialization and configuration."""
        # Default config
        handler = JSONModeHandler()
        assert handler.config.type == ResponseFormat.TEXT
        assert handler.config.strict_validation is True
        
        # Custom config
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

    def test_extract_json_basic_cases(self):
        """Test extraction from various response formats."""
        handler = JSONModeHandler()
        
        # Pure JSON
        response = '{"key": "value", "number": 123}'
        result, error = handler.extract_json_from_response(response)
        assert result == {"key": "value", "number": 123}
        assert error is None
        
        # JSON in markdown
        response = '```json\n{"key": "value"}\n```'
        result, error = handler.extract_json_from_response(response)
        assert result == {"key": "value"}
        assert error is None
        
        # JSON with surrounding text
        response = 'Here is the result: {"success": true, "data": "test"}'
        result, error = handler.extract_json_from_response(response)
        assert result == {"success": True, "data": "test"}
        assert error is None
        
        # JSON with comments (json_repair handles this)
        response = '{"key": "value", // comment\n"number": 123}'
        result, error = handler.extract_json_from_response(response)
        assert result == {"key": "value", "number": 123}
        assert error is None

    def test_extract_json_edge_cases(self):
        """Test edge cases that json_repair handles."""
        handler = JSONModeHandler()
        
        # Missing quotes
        response = '{key: "value", number: 123}'
        result, error = handler.extract_json_from_response(response)
        assert result == {"key": "value", "number": 123}
        assert error is None
        
        # Trailing comma
        response = '{"key": "value", "number": 123,}'
        result, error = handler.extract_json_from_response(response)
        assert result == {"key": "value", "number": 123}
        assert error is None
        
        # Single quotes
        response = "{'key': 'value', 'number': 123}"
        result, error = handler.extract_json_from_response(response)
        assert result == {"key": "value", "number": 123}
        assert error is None

    def test_invalid_responses(self):
        """Test handling of invalid responses."""
        handler = JSONModeHandler()
        
        # Empty response
        result, error = handler.extract_json_from_response("")
        assert result is None
        assert "empty" in error.lower()
        
        # None response
        result, error = handler.extract_json_from_response(None)
        assert result is None
        assert "empty" in error.lower()
        
        # Non-dict JSON (array)
        response = '[1, 2, 3]'
        result, error = handler.extract_json_from_response(response)
        assert result is None
        assert "not an object" in error

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

    def test_process_response(self):
        """Test complete response processing."""
        # Text mode
        handler = JSONModeHandler()
        handler.config.type = ResponseFormat.TEXT
        processed, error = handler.process_response("Plain text")
        assert processed == "Plain text"
        assert error is None
        
        # JSON mode success
        handler.config.type = ResponseFormat.JSON_OBJECT
        processed, error = handler.process_response('{"result": "success"}')
        assert processed == {"result": "success"}
        assert error is None
        
        # JSON mode failure
        processed, error = handler.process_response("Not JSON at all")
        assert isinstance(processed, str)
        assert error is not None


class TestFactoryFunction:
    """Tests for create_json_mode_handler factory."""

    def test_create_handlers(self):
        """Test handler creation with different configs."""
        # Default (text mode)
        handler = create_json_mode_handler()
        assert handler.config.type == ResponseFormat.TEXT
        
        # Explicit text mode
        handler = create_json_mode_handler({"type": "text"})
        assert handler.config.type == ResponseFormat.TEXT
        
        # JSON object mode
        handler = create_json_mode_handler({"type": "json_object"})
        assert handler.config.type == ResponseFormat.JSON_OBJECT
        assert handler.config.strict_validation is True
        
        # Invalid type defaults to text
        handler = create_json_mode_handler({"type": "invalid"})
        assert handler.config.type == ResponseFormat.TEXT