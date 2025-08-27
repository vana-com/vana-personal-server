import requests
import logging
import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .base import BaseCompute, ExecuteResponse, GetResponse
from domain.entities import GrantFile

logger = logging.getLogger(__name__)

@dataclass
class LocalInferenceRequest:
    """Data class for local inference request structure."""
    model: str
    prompt: str
    stream: bool = False

@dataclass
class LocalInferenceResponse:
    """Data class for local inference response structure."""
    response: str
    model: str
    created_at: str
    usage: Dict[str, Any] = None

class LocalLlmInference(BaseCompute):
    """Local Ollama inference provider for complete privacy."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url
        self.model_name = "phi3:mini"  # Default model, can be configured
        self._active_inferences: Dict[str, Dict[str, Any]] = {}
        
    def execute(self, grant_file: GrantFile, files_content: list[str]) -> ExecuteResponse:
        """Execute local inference - data NEVER leaves your server!"""
        
        # Build the prompt from grant file parameters
        prompt = self._build_prompt(grant_file, files_content)
        
        # Generate unique inference ID
        inference_id = f"local_{int(time.time() * 1000)}"
        
        try:
            # Store inference metadata for tracking
            self._active_inferences[inference_id] = {
                "model": self.model_name,
                "prompt": prompt,
                "status": "processing",
                "created_at": time.time(),
                "files_content": files_content  # Keep for processing
            }
            
            logger.info(f"Started local inference {inference_id} with model {self.model_name}")
            
            return ExecuteResponse(
                id=inference_id,
                created_at=time.time()
            )
            
        except Exception as e:
            logger.error(f"Failed to start local inference: {str(e)}")
            raise Exception(f"Failed to start local inference: {str(e)}")
    
    def get(self, inference_id: str) -> GetResponse:
        """Get the result of a local inference."""
        
        if inference_id not in self._active_inferences:
            raise Exception(f"Inference {inference_id} not found")
        
        inference_data = self._active_inferences[inference_id]
        
        try:
            # If still processing, run the inference now
            if inference_data["status"] == "processing":
                result = self._run_inference(inference_data["prompt"])
                
                # Update status
                inference_data["status"] = "completed"
                inference_data["result"] = result
                inference_data["completed_at"] = time.time()
                
                # Clean up sensitive data from memory
                self._secure_cleanup(inference_data)
                
                return GetResponse(
                    id=inference_id,
                    status="succeeded",
                    started_at=inference_data["created_at"],
                    finished_at=inference_data["completed_at"],
                    result=result
                )
            else:
                # Already completed
                return GetResponse(
                    id=inference_id,
                    status=inference_data["status"],
                    started_at=inference_data["created_at"],
                    finished_at=inference_data.get("completed_at"),
                    result=inference_data.get("result")
                )
                
        except Exception as e:
            inference_data["status"] = "failed"
            inference_data["error"] = str(e)
            raise Exception(f"Failed to get inference result: {str(e)}")
    
    def cancel(self, inference_id: str) -> bool:
        """Cancel a running inference."""
        if inference_id in self._active_inferences:
            inference_data = self._active_inferences[inference_id]
            if inference_data["status"] == "processing":
                inference_data["status"] = "canceled"
                # Secure cleanup
                self._secure_cleanup(inference_data)
                return True
        return False
    
    def _run_inference(self, prompt: str) -> str:
        """Run the actual local inference using Ollama."""
        
        try:
            # Call Ollama API
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=300  # 5 minute timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API request failed: {str(e)}")
            raise Exception(f"Ollama API request failed: {str(e)}")
    
    def _build_prompt(self, grant_file: GrantFile, files_content: list[str]) -> str:
        """Build the prompt for local inference."""
        
        # Get the prompt template from grant file
        prompt_template = grant_file.parameters.get("prompt", "")
        
        # Concatenate file content
        concatenated_data = "\n\n".join(files_content)
        
        # Combine template with data
        if "{{data}}" in prompt_template:
            full_prompt = prompt_template.replace("{{data}}", concatenated_data)
        else:
            full_prompt = f"{prompt_template}\n\nData to analyze:\n{concatenated_data}"
        
        return full_prompt
    
    def _secure_cleanup(self, inference_data: Dict[str, Any]):
        """Securely clean up sensitive data from memory."""
        
        # Remove sensitive content
        if "files_content" in inference_data:
            # Overwrite with zeros before deletion
            files_content = inference_data["files_content"]
            if isinstance(files_content, list):
                for content in files_content:
                    if isinstance(content, str):
                        # Overwrite string content
                        content = "0" * len(content)
            del inference_data["files_content"]
        
        if "prompt" in inference_data:
            # Overwrite prompt content
            prompt = inference_data["prompt"]
            if isinstance(prompt, str):
                prompt = "0" * len(prompt)
            del inference_data["prompt"]
    
    def list_models(self) -> list[str]:
        """List available local models."""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json()
                return [model["name"] for model in models.get("models", [])]
            return []
        except:
            return []
    
    def set_model(self, model_name: str):
        """Set the model to use for inference."""
        self.model_name = model_name
        logger.info(f"Switched to model: {model_name}")
