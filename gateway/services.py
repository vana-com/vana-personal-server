import re
import requests
from typing import Dict, Any
from datetime import datetime
from entities import ExecuteRequest, IdentityResponse, PersonalServer

class ReplicateService:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.replicate.com/v1"
    
    def create_prediction(self, request: ExecuteRequest) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "version": "your-model-version",
            "input": {"permission_grant": request.permission_grant}
        }
        
        response = requests.post(
            f"{self.base_url}/predictions",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 201:
            raise Exception(f"Replicate API error: {response.text}")
        
        return response.json()
    
    def get_prediction(self, prediction_id: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Token {self.api_token}"}
        
        response = requests.get(
            f"{self.base_url}/predictions/{prediction_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Replicate API error: {response.text}")
        
        return response.json()
    
    def cancel_prediction(self, prediction_id: str) -> bool:
        headers = {"Authorization": f"Token {self.api_token}"}
        
        response = requests.post(
            f"{self.base_url}/predictions/{prediction_id}/cancel",
            headers=headers
        )
        
        return response.status_code == 200

class IdentityService:
    def get_identity(self, address: str) -> IdentityResponse:
        if not self._is_valid_address(address):
            raise ValueError("Invalid address")
        
        personal_server = PersonalServer(
            address='0x' + '0' * 40,
            public_key='0x04' + '0' * 126
        )
        
        return IdentityResponse(
            user_address=address,
            personal_server=personal_server
        )
    
    def _is_valid_address(self, address: str) -> bool:
        return bool(re.match(r'^0x[a-fA-F0-9]{40}$', address))