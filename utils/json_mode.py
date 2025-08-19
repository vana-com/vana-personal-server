"""
JSON Mode support for LLM responses - OpenAI-compatible implementation.

Provides utilities for enforcing JSON output from LLMs through prompt engineering,
validation, and retry logic with exponential backoff.
"""

import json
import re
import time
import logging
from typing import Any, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ResponseFormat(Enum):
    """Response format types following OpenAI specification."""
    TEXT = "text"
    JSON_OBJECT = "json_object"


@dataclass
class ResponseFormatConfig:
    """Configuration for response format handling."""
    type: ResponseFormat = ResponseFormat.TEXT
    strict_validation: bool = True  # Whether to require non-empty JSON objects


class JSONModeHandler:
    """
    Handler for JSON mode responses from LLMs.
    
    Implements OpenAI-compatible JSON mode with:
    - Prompt modification to enforce JSON output
    - Response validation and extraction
    - Comprehensive error handling
    
    Note: Retry logic should be implemented at the API call level,
    not in this handler. This handler only deals with single responses.
    """
    
    # Prompt suffixes for enforcing JSON output
    JSON_ENFORCE_PROMPT = """

CRITICAL REQUIREMENT: You MUST respond with ONLY valid JSON. Do not include any explanatory text, markdown formatting, or code blocks. Your entire response must be a single valid JSON object that can be parsed by JSON.parse().

Example of CORRECT format:
{"key": "value", "nested": {"field": 123}}

Example of INCORRECT formats:
- ```json {"key": "value"} ```
- Here is the JSON: {"key": "value"}
- {"key": "value"} // comments not allowed

Remember: Output ONLY the raw JSON object, nothing else."""
    
    JSON_RETRY_PROMPT = """

Your previous response was not valid JSON. Please try again and ensure you output ONLY a valid JSON object with no additional text, markdown, or formatting. The response must start with '{' and end with '}' and be parseable by standard JSON parsers."""
    
    def __init__(self, config: Optional[ResponseFormatConfig] = None):
        """
        Initialize JSON mode handler.
        
        Args:
            config: Configuration for response format handling
        """
        self.config = config or ResponseFormatConfig()
    
    def modify_prompt_for_json(self, original_prompt: str) -> str:
        """
        Modify prompt to enforce JSON output.
        
        Args:
            original_prompt: The original user prompt
            
        Returns:
            Modified prompt that enforces JSON output
        """
        return original_prompt + self.JSON_ENFORCE_PROMPT
    
    def extract_json_from_response(self, response: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Extract and validate JSON from LLM response.
        
        Handles common issues like:
        - Markdown code blocks
        - Explanatory text before/after JSON
        - Comments in JSON
        - Malformed JSON
        
        Args:
            response: Raw LLM response
            
        Returns:
            Tuple of (parsed_json, error_message)
            - parsed_json is None if extraction failed
            - error_message is None if extraction succeeded
        """
        if not response or not isinstance(response, str):
            return None, "Response is empty or not a string"
        
        # Track the original response for logging
        original_response = response
        response = response.strip()
        
        # Strategy 1: Try parsing as-is (best case: pure JSON)
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                logger.info("Successfully parsed pure JSON response")
                return parsed, None
            else:
                return None, f"Response is valid JSON but not an object: {type(parsed).__name__}"
        except json.JSONDecodeError as e:
            logger.debug(f"Direct JSON parse failed: {str(e)}")
        
        # Strategy 2: Remove markdown code blocks
        markdown_patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
            r'`([^`]+)`'
        ]
        
        for pattern in markdown_patterns:
            matches = re.findall(pattern, response, re.MULTILINE)
            if matches:
                # Try the first match
                potential_json = matches[0] if isinstance(matches[0], str) else matches[0][0]
                try:
                    parsed = json.loads(potential_json)
                    if isinstance(parsed, dict):
                        logger.info(f"Successfully extracted JSON from markdown block")
                        return parsed, None
                except json.JSONDecodeError:
                    continue
        
        # Strategy 3: Use raw_decode to find first valid JSON object
        # This properly handles strings with braces, escaped quotes, etc.
        decoder = json.JSONDecoder()
        
        # Collect all valid JSON objects found, prefer non-empty ones
        found_objects = []
        
        # Try to find where JSON might start (look for '{')
        idx = 0
        while idx < len(response):
            # Find next potential JSON object start
            next_brace = response.find('{', idx)
            if next_brace == -1:
                break
            
            # First try without any preprocessing
            try:
                obj, end_idx = decoder.raw_decode(response, next_brace)
                if isinstance(obj, dict):
                    found_objects.append((obj, next_brace))
                    # If we found a non-empty object, return it immediately
                    if obj:
                        logger.info(f"Successfully extracted JSON using raw_decode at position {next_brace}")
                        return obj, None
                    # Continue searching for better options
                    idx = end_idx
                    continue
            except json.JSONDecodeError:
                pass
            
            # If that failed, try removing comments from this potential JSON
            # Find the likely end of this JSON object (being aware of strings)
            brace_count = 0
            in_string = False
            escape_next = False
            potential_end = next_brace
            
            for i in range(next_brace, len(response)):
                char = response[i]
                
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            potential_end = i + 1
                            break
            
            if potential_end > next_brace and brace_count == 0:
                potential_json = response[next_brace:potential_end]
                # Remove comments
                cleaned = re.sub(r'//.*?$', '', potential_json, flags=re.MULTILINE)
                cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
                
                try:
                    obj = json.loads(cleaned)
                    if isinstance(obj, dict):
                        logger.info(f"Successfully extracted JSON after comment removal at position {next_brace}")
                        return obj, None
                except json.JSONDecodeError:
                    pass
            
            # Move past this '{' and continue searching
            idx = next_brace + 1
        
        # If we only found empty objects, return the first one
        if found_objects and not any(obj for obj, _ in found_objects if obj):
            logger.info(f"Only found empty JSON objects, returning first at position {found_objects[0][1]}")
            return found_objects[0][0], None
        
        # Strategy 4: Try to fix common JSON issues and retry
        # Look for anything that might be JSON-like
        json_like_match = re.search(r'\{[^{}]*\}', response)
        if json_like_match:
            potential_json = json_like_match.group(0)
            
            # Fix single quotes (convert to double quotes)
            fixed_json = re.sub(r"'([^']*)'", r'"\1"', potential_json)
            
            # Fix unquoted keys (simple heuristic)
            fixed_json = re.sub(r'(\w+):', r'"\1":', fixed_json)
            
            # Remove any remaining ellipsis
            fixed_json = re.sub(r'\.\.\.', '""', fixed_json)
            
            # Remove trailing commas
            fixed_json = re.sub(r',\s*([}\]])', r'\1', fixed_json)
            
            try:
                parsed = json.loads(fixed_json)
                if isinstance(parsed, dict):
                    logger.info("Successfully parsed JSON after applying fixes")
                    return parsed, None
            except json.JSONDecodeError as e:
                logger.debug(f"Fixed JSON parse failed: {str(e)}")
        
        # All strategies failed
        error_msg = f"Failed to extract valid JSON from response. Response length: {len(original_response)} chars"
        if len(original_response) < 500:
            error_msg += f"\nResponse: {original_response}"
        else:
            error_msg += f"\nResponse (first 500 chars): {original_response[:500]}..."
        
        return None, error_msg
    
    def validate_json_response(self, json_obj: Dict[str, Any]) -> bool:
        """
        Validate that the JSON response meets basic requirements.
        
        Args:
            json_obj: Parsed JSON object
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(json_obj, dict):
            logger.error(f"JSON response is not an object: {type(json_obj).__name__}")
            return False
        
        if not json_obj:
            logger.error("JSON response is an empty object")
            return False if self.config.strict_validation else True
        
        # Additional validation can be added here based on requirements
        # For now, we just ensure it's a non-empty dict
        
        return True
    
    
    def process_response(self, response: str) -> Tuple[Union[Dict[str, Any], str], Optional[str]]:
        """
        Process an LLM response according to the configured format.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Tuple of (processed_response, error_message)
            - processed_response: Either parsed JSON dict or original string
            - error_message: Error details if processing failed (None on success)
        """
        if self.config.type == ResponseFormat.TEXT:
            # Text mode - return as-is
            return response, None
        
        # JSON mode - extract and validate
        json_obj, error = self.extract_json_from_response(response)
        
        if json_obj is not None:
            if self.validate_json_response(json_obj):
                return json_obj, None
            else:
                error = "JSON validation failed: empty object" if not json_obj else "JSON validation failed"
        
        # Extraction or validation failed
        logger.error(f"JSON extraction failed: {error}")
        return response, error


def create_json_mode_handler(response_format: Optional[Dict[str, Any]] = None) -> JSONModeHandler:
    """
    Factory function to create a JSON mode handler from OpenAI-compatible format.
    
    Args:
        response_format: OpenAI-compatible response format dict
                        e.g., {"type": "json_object"} or {"type": "text"}
    
    Returns:
        Configured JSONModeHandler instance
    """
    if response_format is None:
        response_format = {"type": "text"}
    
    format_type = response_format.get("type", "text")
    
    if format_type == "json_object":
        config = ResponseFormatConfig(
            type=ResponseFormat.JSON_OBJECT,
            strict_validation=True  # Require non-empty JSON objects
        )
    else:
        config = ResponseFormatConfig(type=ResponseFormat.TEXT)
    
    return JSONModeHandler(config)