"""
Response formatting utilities for LLM and other text processing.

Provides advanced text formatting, cleaning, and normalization functions.
"""

import re
from typing import Any, List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """
    Advanced response formatting with configurable options.
    """
    
    def __init__(
        self,
        max_consecutive_newlines: int = 2,
        preserve_code_blocks: bool = True,
        normalize_whitespace: bool = True,
        strip_empty_lines: bool = True
    ):
        """
        Initialize response formatter with configuration.
        
        Args:
            max_consecutive_newlines: Maximum consecutive newlines to allow
            preserve_code_blocks: Whether to preserve code block formatting
            normalize_whitespace: Whether to normalize multiple spaces
            strip_empty_lines: Whether to remove trailing empty lines
        """
        self.max_consecutive_newlines = max_consecutive_newlines
        self.preserve_code_blocks = preserve_code_blocks
        self.normalize_whitespace = normalize_whitespace
        self.strip_empty_lines = strip_empty_lines
        
        # Code block patterns
        self.code_block_patterns = [
            r'```[\s\S]*?```',  # Markdown code blocks
            r'`[^`\n]+`',       # Inline code
            r'^\s{4,}.*$',      # Indented code (4+ spaces)
            r'^\t+.*$',         # Tab-indented code
        ]
    
    def format_response(self, response_data: Any) -> str:
        """
        Format response data with advanced options.
        
        Args:
            response_data: The raw response data
            
        Returns:
            Formatted string
        """
        if response_data is None:
            logger.warning("Response data is None")
            return ""
        
        # Convert to string representation
        if isinstance(response_data, str):
            text = response_data
        elif hasattr(response_data, '__iter__') and not isinstance(response_data, (str, bytes)):
            text = self._join_iterable(response_data)
        else:
            text = str(response_data)
        
        # Apply formatting
        return self._clean_text(text)
    
    def _join_iterable(self, iterable: Any) -> str:
        """Join iterable elements intelligently."""
        try:
            text_parts = []
            for item in iterable:
                if item is not None:
                    part = str(item).strip()
                    if part:
                        text_parts.append(part)
            
            if not text_parts:
                return ""
            
            # Smart joining - detect if parts already have good separation
            result = []
            for i, part in enumerate(text_parts):
                if i > 0:
                    # Check if previous part ends with punctuation or newline
                    prev_part = text_parts[i-1]
                    if not (prev_part.endswith(('.', '!', '?', ':', '\n')) or part.startswith('\n')):
                        result.append('\n')
                result.append(part)
            
            return ''.join(result)
            
        except Exception as e:
            logger.error(f"Error joining iterable: {str(e)}")
            return str(iterable)
    
    def _clean_text(self, text: str) -> str:
        """Clean text with configured options."""
        if not text or not isinstance(text, str):
            return ""
        
        text = text.strip()
        if not text:
            return ""
        
        # Preserve code blocks if requested
        if self.preserve_code_blocks:
            text = self._preserve_code_blocks(text)
        
        # Normalize consecutive newlines
        if self.max_consecutive_newlines > 0:
            pattern = r'\n{' + str(self.max_consecutive_newlines + 1) + r',}'
            replacement = '\n' * self.max_consecutive_newlines
            text = re.sub(pattern, replacement, text)
        
        # Normalize whitespace
        if self.normalize_whitespace:
            text = self._normalize_whitespace(text)
        
        # Strip empty lines
        if self.strip_empty_lines:
            text = self._strip_empty_lines(text)
        
        return text
    
    def _preserve_code_blocks(self, text: str) -> str:
        """Preserve formatting within code blocks."""
        # This is a placeholder for more sophisticated code block preservation
        # For now, we'll be less aggressive with whitespace normalization
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace while preserving structure."""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Preserve leading whitespace for indentation
            leading_whitespace = len(line) - len(line.lstrip())
            if leading_whitespace > 0:
                leading = line[:leading_whitespace]
                rest = line[leading_whitespace:]
                # Only normalize multiple spaces in the content, not indentation
                cleaned_rest = re.sub(r' {2,}', ' ', rest)
                cleaned_lines.append(leading + cleaned_rest)
            else:
                # Clean multiple spaces in regular lines
                cleaned_lines.append(re.sub(r' {2,}', ' ', line))
        
        return '\n'.join(cleaned_lines)
    
    def _strip_empty_lines(self, text: str) -> str:
        """Remove trailing empty lines and normalize."""
        lines = text.split('\n')
        
        # Remove trailing empty lines
        while lines and not lines[-1].strip():
            lines.pop()
        
        # Remove leading empty lines
        while lines and not lines[0].strip():
            lines.pop(0)
        
        return '\n'.join(line.rstrip() for line in lines)


# Default formatter instance
default_formatter = ResponseFormatter()


def format_llm_response_advanced(
    response_data: Any,
    max_consecutive_newlines: int = 2,
    preserve_code_blocks: bool = True,
    normalize_whitespace: bool = True,
    strip_empty_lines: bool = True
) -> str:
    """
    Advanced LLM response formatting with configurable options.
    
    Args:
        response_data: The raw response data
        max_consecutive_newlines: Maximum consecutive newlines to allow
        preserve_code_blocks: Whether to preserve code block formatting
        normalize_whitespace: Whether to normalize multiple spaces
        strip_empty_lines: Whether to remove trailing empty lines
        
    Returns:
        Formatted string
    """
    formatter = ResponseFormatter(
        max_consecutive_newlines=max_consecutive_newlines,
        preserve_code_blocks=preserve_code_blocks,
        normalize_whitespace=normalize_whitespace,
        strip_empty_lines=strip_empty_lines
    )
    return formatter.format_response(response_data)


def detect_response_format(text: str) -> Dict[str, Any]:
    """
    Detect the format and characteristics of response text.
    
    Args:
        text: The text to analyze
        
    Returns:
        Dictionary with format information
    """
    if not text:
        return {"type": "empty", "has_code": False, "has_lists": False, "line_count": 0}
    
    lines = text.split('\n')
    
    # Detect code blocks
    has_code = bool(re.search(r'```|`[^`]+`|^\s{4,}', text, re.MULTILINE))
    
    # Detect lists
    has_lists = bool(re.search(r'^\s*[-*+]\s|^\s*\d+\.\s', text, re.MULTILINE))
    
    # Detect tables
    has_tables = bool(re.search(r'\|.*\|', text, re.MULTILINE))
    
    # Count excessive newlines
    excessive_newlines = len(re.findall(r'\n{3,}', text))
    
    # Analyze line length distribution
    line_lengths = [len(line) for line in lines]
    avg_line_length = sum(line_lengths) / len(line_lengths) if line_lengths else 0
    
    return {
        "type": "text",
        "has_code": has_code,
        "has_lists": has_lists,
        "has_tables": has_tables,
        "line_count": len(lines),
        "excessive_newlines": excessive_newlines,
        "avg_line_length": avg_line_length,
        "needs_cleaning": excessive_newlines > 0 or avg_line_length > 120
    }


def smart_format_response(response_data: Any) -> str:
    """
    Smart formatting that adapts to response content.
    
    Args:
        response_data: The raw response data
        
    Returns:
        Formatted string optimized for the content type
    """
    # First, do basic formatting
    formatted = default_formatter.format_response(response_data)
    
    if not formatted:
        return formatted
    
    # Analyze the content
    format_info = detect_response_format(formatted)
    
    # Adjust formatting based on content
    if format_info["has_code"]:
        # Be more conservative with code-heavy content
        formatter = ResponseFormatter(
            max_consecutive_newlines=2,
            preserve_code_blocks=True,
            normalize_whitespace=False,  # Don't normalize whitespace in code
            strip_empty_lines=True
        )
        return formatter.format_response(response_data)
    
    elif format_info["has_lists"] or format_info["has_tables"]:
        # Preserve structure for lists and tables
        formatter = ResponseFormatter(
            max_consecutive_newlines=2,
            preserve_code_blocks=True,
            normalize_whitespace=True,
            strip_empty_lines=True
        )
        return formatter.format_response(response_data)
    
    else:
        # Regular text - more aggressive cleaning
        formatter = ResponseFormatter(
            max_consecutive_newlines=2,
            preserve_code_blocks=False,
            normalize_whitespace=True,
            strip_empty_lines=True
        )
        return formatter.format_response(response_data)