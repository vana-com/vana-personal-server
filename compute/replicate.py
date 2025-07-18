import replicate
import logging
from typing import Dict, Any
from dataclasses import dataclass
from .base import BaseCompute, ExecuteResponse, GetResponse
from settings import get_settings
from domain.entities import GrantFile

logger = logging.getLogger(__name__)



@dataclass
class ReplicateInput:
    """Data class for Replicate API input structure."""
    prompt: str

@dataclass
class ReplicateRequest:
    """Data class for Replicate API request structure."""
    model: str
    input: ReplicateInput

@dataclass
class ReplicateUrls:
    """Data class for Replicate API URLs."""
    cancel: str
    get: str
    web: str

@dataclass
class ReplicatePredictionResponse:
    """Data class for Replicate API prediction response."""
    id: str
    model: str
    version: str
    input: Dict[str, Any]
    logs: str = ""
    output: Any = None
    data_removed: bool = False
    error: str = None
    status: str = "starting"
    created_at: str = None
    started_at: str = None
    completed_at: str = None
    urls: ReplicateUrls = None

PROMPT_DATA_SEPARATOR = "-----" * 80 + "\n"


class ReplicateLlmInference(BaseCompute):
    """Replicate API provider for ML model inference."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = replicate.Client(
            api_token=self.settings.replicate_api_token
        )
        self.model_name = "deepseek-ai/deepseek-v3"

    def execute(self, grant_file: GrantFile, files_content: list[str]) -> ExecuteResponse:
        prompt = self._build_prompt(grant_file, files_content)
        try:
            prediction = self.client.predictions.create(
                model=self.model_name,
                input={"prompt": prompt}
            )
            return ExecuteResponse(
                id=prediction.id,
                created_at=prediction.created_at
            )
        except Exception as e:
            raise Exception(f"Failed to create prediction: {str(e)}")
    
    def get(self, prediction_id: str) -> GetResponse:
        try:
            prediction = self.client.predictions.get(prediction_id)
            started_at = prediction.started_at if prediction.started_at else None
            finished_at = prediction.completed_at if prediction.completed_at else None
            result = prediction.output if prediction.output else None
            
            # Convert list result to string if needed
            if isinstance(result, list):
                result = ''.join(result)
            
            return GetResponse(
                id=prediction.id,
                status=prediction.status,
                started_at=started_at,
                finished_at=finished_at,
                result=result
            )
        except Exception as e:
            raise Exception(f"Failed to get prediction: {str(e)}")
    
    def cancel(self, prediction_id: str) -> bool:
        """Cancel a running prediction."""
        try:
            # Use the Replicate client directly
            prediction = self.client.predictions.cancel(prediction_id)
            return prediction.status == "canceled"
        except Exception:
            return False 
        
    
    def _build_prompt(self, grant_file: GrantFile, files_content: list[str]):
        prompt_template = grant_file.parameters.get("prompt", "")
        concatenated_data = (
            "\n"
            + PROMPT_DATA_SEPARATOR.join(files_content)
            + "\n"
            + PROMPT_DATA_SEPARATOR
        )
        return prompt_template.replace("{{data}}", concatenated_data)

