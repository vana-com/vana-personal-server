"""
JSON Mode support for LLM responses - OpenAI-compatible implementation.

Provides utilities for enforcing JSON output from LLMs through prompt engineering
and validation. Uses json_repair library for robust JSON extraction and fixing.
"""

import logging
from typing import Any, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

try:
    import json_repair
except ImportError:
    raise ImportError(
        "json_repair is required for JSON mode. Install it with: pip install json-repair"
    )

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
    - Response validation and extraction using json_repair
    - Comprehensive error handling
    
    The json_repair library handles:
    - Markdown code blocks
    - Comments in JSON
    - Missing quotes, commas, brackets
    - Malformed JSON structures
    - Multiple JSON objects (takes first valid one)
    """
    
    # Prompt suffix for enforcing JSON output
    JSON_ENFORCE_PROMPT = """

CRITICAL REQUIREMENT: You MUST respond with ONLY valid JSON. Do not include any explanatory text, markdown formatting, or code blocks. Your entire response must be a single valid JSON object that can be parsed by JSON.parse().

Example of CORRECT format:
{"key": "value", "nested": {"field": 123}}

Example of INCORRECT formats:
- ```json {"key": "value"} ```
- Here is the JSON: {"key": "value"}
- {"key": "value"} // comments not allowed

Remember: Output ONLY the raw JSON object, nothing else."""
    
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
        Extract and validate JSON from LLM response using json_repair.
        
        The json_repair library automatically handles:
        - Markdown code blocks
        - Comments in JSON
        - Missing quotes, commas, brackets
        - Trailing commas
        - Unquoted keys
        - Multiple JSON objects
        - Escaped characters
        - And many other common JSON issues
        
        Args:
            response: Raw LLM response
            
        Returns:
            Tuple of (parsed_json, error_message)
            - parsed_json is None if extraction failed
            - error_message is None if extraction succeeded
        """
        if not response or not isinstance(response, str):
            return None, "Response is empty or not a string"
        
        try:
            # json_repair handles all the edge cases for us
            # It will find and fix JSON even if it's wrapped in markdown,
            # has comments, missing quotes, etc.
            parsed = json_repair.loads(response)
            
            # Ensure we got a dictionary (not a list or primitive)
            if not isinstance(parsed, dict):
                return None, f"Response is valid JSON but not an object: {type(parsed).__name__}"
            
            logger.info("Successfully extracted and repaired JSON from response")
            return parsed, None
            
        except Exception as e:
            # json_repair returns an empty dict {} if the JSON is completely broken
            # We treat this as an error if strict validation is enabled
            error_msg = f"Failed to extract valid JSON from response: {str(e)}"
            logger.error(error_msg)
            
            # Log first 500 chars of response for debugging
            if len(response) < 500:
                logger.debug(f"Response: {response}")
            else:
                logger.debug(f"Response (first 500 chars): {response[:500]}...")
            
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
        
        # If strict validation is enabled, don't accept empty objects
        # (json_repair returns {} for completely broken JSON)
        if self.config.strict_validation and not json_obj:
            logger.error("JSON response is an empty object (possibly due to repair failure)")
            return False
        
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