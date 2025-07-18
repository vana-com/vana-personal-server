import replicate
import re
from typing import Any, List, Union
import logging

logger = logging.getLogger(__name__)


def format_llm_response(response_data: Any) -> str:
    """
    Robustly format LLM response data into a clean string.
    
    Handles various response formats and prevents excessive newlines.
    
    Args:
        response_data: The raw response from the LLM (can be list, string, etc.)
        
    Returns:
        Formatted string with proper newline handling
    """
    if response_data is None:
        logger.warning("LLM response is None, returning empty string")
        return ""
    
    # If it's already a string, clean it up
    if isinstance(response_data, str):
        return clean_response_text(response_data)
    
    # If it's a list or iterable, process each element
    if hasattr(response_data, '__iter__'):
        try:
            # Convert all elements to strings and filter out empty ones
            text_parts = []
            for item in response_data:
                if item is not None:
                    text_part = str(item).strip()
                    if text_part:  # Only add non-empty parts
                        text_parts.append(text_part)
            
            if not text_parts:
                logger.warning("LLM response contains no valid text parts")
                return ""
            
            # Join with single newlines and clean up
            combined_text = "\n".join(text_parts)
            return clean_response_text(combined_text)
            
        except Exception as e:
            logger.error(f"Error processing LLM response iterable: {str(e)}")
            # Fallback to string conversion
            return clean_response_text(str(response_data))
    
    # For any other type, convert to string
    return clean_response_text(str(response_data))


def clean_response_text(text: str) -> str:
    """
    Clean up response text by normalizing whitespace and newlines.
    
    Args:
        text: The text to clean
        
    Returns:
        Cleaned text with normalized whitespace
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    if not text:
        return ""
    
    # Replace multiple consecutive newlines with at most 2 newlines
    # This preserves paragraph breaks while preventing excessive spacing
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Replace multiple consecutive spaces with single space (except at line start)
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Preserve leading whitespace for formatting (like code blocks)
        leading_whitespace = len(line) - len(line.lstrip())
        if leading_whitespace > 0:
            # Keep leading whitespace but clean the rest
            leading = line[:leading_whitespace]
            rest = line[leading_whitespace:]
            cleaned_rest = re.sub(r' {2,}', ' ', rest)
            cleaned_lines.append(leading + cleaned_rest)
        else:
            # Clean multiple spaces in regular lines
            cleaned_lines.append(re.sub(r' {2,}', ' ', line))
    
    # Join back and do final cleanup
    result = '\n'.join(cleaned_lines)
    
    # Remove trailing whitespace from each line
    result = '\n'.join(line.rstrip() for line in result.split('\n'))
    
    return result


class Llm:
    def __init__(self, client: replicate.Client):
        self.client = client
        self.model_name = "deepseek-ai/deepseek-v3"

    def run(self, prompt: str) -> str:
        """
        Run LLM inference with robust response formatting.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            Formatted response string
        """
        try:
            logger.info(f"Running LLM inference with model: {self.model_name}")
            result = self.client.run(self.model_name, input={"prompt": prompt})
            
            # Use robust response formatting
            formatted_response = format_llm_response(result)
            
            if not formatted_response:
                logger.warning("LLM returned empty response after formatting")
                return "No response generated."
            
            logger.info(f"LLM response formatted successfully ({len(formatted_response)} chars)")
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error running LLM inference: {str(e)}")
            raise Exception(f"LLM inference failed: {str(e)}")