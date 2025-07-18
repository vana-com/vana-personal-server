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

    def execute(self, grant_file: GrantFile, files_content: list[str]) -> ReplicatePredictionResponse:
        prompt = self._build_prompt(grant_file, files_content)
        """Create a new prediction on Replicate."""
        try:
            logger.info(f"Replicate create prediction with prompt: {prompt}")

            # Use the Replicate client directly with the model identifier
            prediction = self.client.predictions.create(
                model=self.model_name,
                input={"prompt": prompt}
            )
            
            logger.info(f"Replicate response: {prediction}")
            
            return ExecuteResponse(
                id=prediction.id,
                created_at=prediction.created_at
            )
        except Exception as e:
            raise Exception(f"Failed to create prediction: {str(e)}")
    
    def get(self, prediction_id: str) -> ReplicatePredictionResponse:
        """Get prediction status and results."""
        try:
            # Use the Replicate client directly
            prediction = self.client.predictions.get(prediction_id)
            logger.info(f"Replicate get response: {prediction}")
            
            return GetResponse(
                id=prediction.id,
                status=prediction.status,
                started_at=prediction.started_at,
                finished_at=prediction.completed_at,
                result=prediction.output
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

