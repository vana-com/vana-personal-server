"""Test cases for robust JSON extraction with edge cases."""

import json
from utils.json_mode import JSONModeHandler


class TestRobustJSONExtraction:
    """Test suite for robust JSON extraction using raw_decode."""

    def test_json_with_braces_in_strings(self):
        """Test extraction with braces inside string values."""
        handler = JSONModeHandler()
        
        # JSON with braces in string value
        response = '{"message": "Use {} for empty dict and {key: value} for objects"}'
        result, error = handler.extract_json_from_response(response)
        assert result is not None
        assert result["message"] == "Use {} for empty dict and {key: value} for objects"
        assert error is None

    def test_json_with_escaped_quotes(self):
        """Test extraction with escaped quotes in strings."""
        handler = JSONModeHandler()
        
        # JSON with escaped quotes
        response = '{"text": "She said \\"Hello\\" to me", "value": 123}'
        result, error = handler.extract_json_from_response(response)
        assert result is not None
        assert result["text"] == 'She said "Hello" to me'
        assert result["value"] == 123
        assert error is None

    def test_json_with_newlines_in_strings(self):
        """Test extraction with newlines in string values."""
        handler = JSONModeHandler()
        
        # JSON with newlines (escaped)
        response = '{"multiline": "Line 1\\nLine 2\\nLine 3", "ok": true}'
        result, error = handler.extract_json_from_response(response)
        assert result is not None
        assert "Line 1\nLine 2\nLine 3" in result["multiline"]
        assert result["ok"] is True
        assert error is None

    def test_multiple_json_with_complex_strings(self):
        """Test extraction of first JSON when multiple present with complex content."""
        handler = JSONModeHandler()
        
        # Multiple JSON objects with complex content
        response = '''
        First object: {"id": 1, "text": "Has } and { in it", "valid": true}
        Second object: {"id": 2, "text": "Another one"}
        '''
        result, error = handler.extract_json_from_response(response)
        assert result is not None
        assert result["id"] == 1
        assert "Has } and { in it" in result["text"]
        assert error is None

    def test_json_after_text_with_braces(self):
        """Test extraction when non-JSON text with braces precedes valid JSON."""
        handler = JSONModeHandler()
        
        # Text with braces before JSON
        response = 'Use format{} for templates. Here is the JSON: {"result": "success", "code": 200}'
        result, error = handler.extract_json_from_response(response)
        assert result is not None
        assert result["result"] == "success"
        assert result["code"] == 200
        assert error is None

    def test_nested_json_with_json_string(self):
        """Test extraction of JSON containing stringified JSON."""
        handler = JSONModeHandler()
        
        # JSON containing another JSON as string
        response = '{"outer": "value", "inner_json": "{\\"nested\\": true}"}'
        result, error = handler.extract_json_from_response(response)
        assert result is not None
        assert result["outer"] == "value"
        assert result["inner_json"] == '{"nested": true}'
        assert error is None

    def test_json_with_special_characters(self):
        """Test extraction with various special characters."""
        handler = JSONModeHandler()
        
        # JSON with special characters
        response = r'{"path": "C:\\Users\\name\\file.txt", "regex": "\\d+", "tab": "\t"}'
        result, error = handler.extract_json_from_response(response)
        assert result is not None
        assert result["path"] == "C:\\Users\\name\\file.txt"
        assert result["regex"] == "\\d+"
        assert result["tab"] == "\t"
        assert error is None

    def test_json_mixed_with_arrays(self):
        """Test extraction skips arrays and finds objects."""
        handler = JSONModeHandler()
        
        # Response with array first, then object
        response = '[1, 2, 3] is an array. {"type": "object", "valid": true} is what we want.'
        result, error = handler.extract_json_from_response(response)
        assert result is not None
        assert result["type"] == "object"
        assert result["valid"] is True
        assert error is None

    def test_incomplete_json_objects(self):
        """Test handling of incomplete JSON objects."""
        handler = JSONModeHandler()
        
        # Incomplete JSON followed by complete
        response = '{"incomplete": "no closing brace... But here is good: {"complete": true, "value": 42}'
        result, error = handler.extract_json_from_response(response)
        assert result is not None
        assert result["complete"] is True
        assert result["value"] == 42
        assert error is None