import replicate
import requests
import json
import logging
from typing import Dict, Any
from dataclasses import dataclass, asdict
from .base import BaseCompute
from settings import settings

logger = logging.getLogger(__name__)

# API endpoint constants
PREDICTIONS_ENDPOINT = "/predictions"
CANCEL_ENDPOINT = "/cancel"

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

class ReplicateCompute(BaseCompute):
    """Replicate API provider for ML model inference."""
    
    def __init__(self):
        self.client = replicate.Client(
            api_token=settings.REPLICATE_API_TOKEN
        )
        self.model_name = "deepseek-ai/deepseek-v3"
        self.base_url = "https://api.replicate.com/v1"
        self.headers = {
            "Authorization": f"Token {settings.REPLICATE_API_TOKEN}",
            "Content-Type": "application/json"
        }

    def execute(self, request: Dict[str, Any]) -> ReplicatePredictionResponse:
        prompt = request.get("prompt", "")
        """Create a new prediction on Replicate."""
        try:
            logger.info(f"Replicate create prediction with prompt: {prompt}")

            replicate_request = ReplicateRequest(
                model=self.model_name,
                input=ReplicateInput(prompt=prompt)
            )

            response = requests.post(
                f"{self.base_url}{PREDICTIONS_ENDPOINT}",
                headers=self.headers,
                json=asdict(replicate_request)
            )
            response.raise_for_status()
            response_data = response.json()
            logger.info(f"Replicate response: {response_data}")
            
            # Convert nested urls dict to ReplicateUrls dataclass
            if 'urls' in response_data and response_data['urls']:
                response_data['urls'] = ReplicateUrls(**response_data['urls'])
            
            return ReplicatePredictionResponse(**response_data)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to create prediction: {str(e)}")
    
    def get(self, prediction_id: str) -> ReplicatePredictionResponse:
        """Get prediction status and results."""
        try:
            response = requests.get(
                f"{self.base_url}{PREDICTIONS_ENDPOINT}/{prediction_id}",
                headers=self.headers
            )
            response.raise_for_status()
            response_data = response.json()
            logger.info(f"Replicate get response: {response_data}")
            
            # Convert nested urls dict to ReplicateUrls dataclass
            if 'urls' in response_data and response_data['urls']:
                response_data['urls'] = ReplicateUrls(**response_data['urls'])
            
            return ReplicatePredictionResponse(**response_data)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get prediction: {str(e)}")
    
    def cancel(self, prediction_id: str) -> bool:
        """Cancel a running prediction."""
        try:
            response = requests.post(
                f"{self.base_url}{PREDICTIONS_ENDPOINT}/{prediction_id}{CANCEL_ENDPOINT}",
                headers=self.headers
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False 