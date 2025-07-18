import replicate
import requests
import logging
from typing import Dict, Any
from dataclasses import dataclass, asdict
from .base import BaseCompute, ExecuteResponse, GetResponse
from settings import get_settings
from onchain.data_registry import GrantFile

logger = logging.getLogger(__name__)

# API endpoint constants
PREDICTIONS_ENDPOINT = "predictions"
CANCEL_ENDPOINT = "cancel"

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
        self.base_url = "https://api.replicate.com/v1"
        self.headers = {
            "Authorization": f"Token {self.settings.replicate_api_token}",
            "Content-Type": "application/json"
        }

    def execute(self, grant_file: GrantFile, files_content: list[str]) -> ReplicatePredictionResponse:
        prompt = self._build_prompt(grant_file, files_content)
        """Create a new prediction on Replicate."""
        try:
            logger.info(f"Replicate create prediction with prompt: {prompt}")

            replicate_request = ReplicateRequest(
                model=self.model_name,
                input=ReplicateInput(prompt=prompt)
            )

            response_data = self._make_post(json_data=asdict(replicate_request))
            logger.info(f"Replicate response: {response_data}")
            
            # Convert nested urls dict to ReplicateUrls dataclass
            if 'urls' in response_data and response_data['urls']:
                response_data['urls'] = ReplicateUrls(**response_data['urls'])
            
            replicate_prediction_response = ReplicatePredictionResponse(**response_data)
            return ExecuteResponse(
                id=replicate_prediction_response.id,
                created_at=replicate_prediction_response.created_at
            )
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to create prediction: {str(e)}")
    
    def get(self, prediction_id: str) -> ReplicatePredictionResponse:
        """Get prediction status and results."""
        try:
            response_data = self._make_get(prediction_id)
            logger.info(f"Replicate get response: {response_data}")
            
            # Convert nested urls dict to ReplicateUrls dataclass
            if 'urls' in response_data and response_data['urls']:
                response_data['urls'] = ReplicateUrls(**response_data['urls'])
            
            replicate_prediction_response = ReplicatePredictionResponse(**response_data)
            return GetResponse(
                id=replicate_prediction_response.id,
                status=replicate_prediction_response.status,
                started_at=replicate_prediction_response.started_at,
                finished_at=replicate_prediction_response.completed_at,
                result=replicate_prediction_response.output
            )
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get prediction: {str(e)}")
    
    def cancel(self, prediction_id: str) -> bool:
        """Cancel a running prediction."""
        try:
            response_data = self._make_post(f"/{prediction_id}/{CANCEL_ENDPOINT}")
            return response_data.get("status") == "canceled"
        except requests.exceptions.RequestException:
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

    def _make_post(self, endpoint: str = "", json_data: dict = {}) -> dict:
        """Make HTTP request to Replicate API."""
        url = f"{self.base_url}/{PREDICTIONS_ENDPOINT}/{endpoint}"
        response = requests.post(url, headers=self.headers, json=json_data)
        response.raise_for_status()
        return response.json()