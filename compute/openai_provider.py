#!/usr/bin/env python3
"""
OpenAI Provider for Privacy-Preserving AI Processing.
This integrates ChatGPT with our privacy pipeline.
"""

import logging
import openai
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .base import BaseCompute, ExecuteResponse, GetResponse
from domain.entities import GrantFile

logger = logging.getLogger(__name__)

@dataclass
class OpenAIConfig:
    """OpenAI configuration."""
    api_key: str
    model: str = "gpt-4o-mini"  # Default to GPT-4o-mini for cost efficiency
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout: int = 30

class OpenAIProvider(BaseCompute):
    """OpenAI provider that processes privacy-enhanced features."""
    
    def __init__(self, config: Optional[OpenAIConfig] = None):
        """Initialize OpenAI provider."""
        if config is None:
            # Try to get from environment
            import os
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable required")
            config = OpenAIConfig(api_key=api_key)
        
        self.config = config
        openai.api_key = config.api_key
        self._active_requests: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"OpenAI provider initialized with model: {config.model}")
    
    def execute(self, grant_file: GrantFile, files_content: list[str]) -> ExecuteResponse:
        """
        Execute privacy-preserving processing with OpenAI.
        
        Note: This should receive privacy-enhanced features, not raw content.
        """
        request_id = f"openai_{int(time.time() * 1000)}"
        
        # Store request metadata
        self._active_requests[request_id] = {
            "grant_file": grant_file,
            "files_content": files_content,
            "status": "processing",
            "created_at": time.time()
        }
        
        logger.info(f"OpenAI processing initiated for request {request_id}")
        
        return ExecuteResponse(id=request_id, created_at=time.time())
    
    def get(self, request_id: str) -> GetResponse:
        """Get processing results from OpenAI."""
        if request_id not in self._active_requests:
            raise ValueError(f"Request {request_id} not found")
        
        request_data = self._active_requests[request_id]
        
        try:
            # Process the request if it's still pending
            if request_data["status"] == "processing":
                result = self._process_with_openai(request_data)
                request_data["status"] = "completed"
                request_data["result"] = result
            else:
                result = request_data["result"]
            
            # Clean up sensitive data
            self._secure_cleanup(request_data)
            
            return GetResponse(
                id=request_id,
                status="completed",
                result=result,
                created_at=request_data["created_at"]
            )
            
        except Exception as e:
            request_data["status"] = "failed"
            request_data["error"] = str(e)
            logger.error(f"OpenAI processing failed for {request_id}: {e}")
            raise
    
    def _process_with_openai(self, request_data: Dict[str, Any]) -> str:
        """Process data with OpenAI API."""
        try:
            # Build a privacy-aware prompt
            prompt = self._build_privacy_aware_prompt(request_data)
            
            logger.info(f"Sending privacy-enhanced prompt to OpenAI: {len(prompt)} characters")
            
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "You are a privacy-aware AI assistant. Process the provided features and provide insights without revealing sensitive information."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                timeout=self.config.timeout
            )
            
            result = response.choices[0].message.content
            logger.info(f"OpenAI response received: {len(result)} characters")
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _build_privacy_aware_prompt(self, request_data: Dict[str, Any]) -> str:
        """Build a prompt that preserves privacy."""
        grant_file = request_data["grant_file"]
        files_content = request_data["files_content"]
        
        # This is where we'd integrate with our privacy pipeline
        # For now, we'll create a basic privacy-aware prompt
        prompt = f"""
        Analyze the following privacy-enhanced document features:
        
        Document Type: {getattr(grant_file, 'document_type', 'unknown')}
        Number of Files: {len(files_content)}
        
        Please provide insights based on these features while maintaining privacy.
        Focus on patterns, trends, and general analysis without revealing specific details.
        """
        
        return prompt
    
    def _secure_cleanup(self, request_data: Dict[str, Any]):
        """Securely clean up sensitive data."""
        try:
            # Clear sensitive fields
            if "files_content" in request_data:
                request_data["files_content"] = None
            
            # Mark for garbage collection
            import gc
            gc.collect()
            
            logger.debug("Secure cleanup completed for OpenAI request")
            
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

# Convenience function
def create_openai_provider(api_key: Optional[str] = None, model: str = "gpt-4o-mini") -> OpenAIProvider:
    """Create an OpenAI provider instance."""
    if api_key is None:
        import os
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable required")
    
    config = OpenAIConfig(api_key=api_key, model=model)
    return OpenAIProvider(config)
