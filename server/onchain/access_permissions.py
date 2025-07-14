import json
import logging
import os
from typing import Optional
import web3
from web3 import Web3

from entities import AccessPermissionsResponse, PersonalServerRequest, GrantData
from .chain import Chain, get_data_permissions_address
from .abi import get_abi

logger = logging.getLogger(__name__)

class AccessPermissions:
    def __init__(self, chain: Chain, web3: Web3):
        self.chain = chain
        self.web3 = web3
        
        self.data_permissions_address = get_data_permissions_address(chain.chain_id)
        self.data_permissions_abi = get_abi("DataPermissions")
        
        self.contract = self.web3.eth.contract(
            address=self.data_permissions_address,
            abi=self.data_permissions_abi
        )

    def fetch_access_permissions(
        self, app_address: str, request: PersonalServerRequest
    ) -> AccessPermissionsResponse:
        """
        Fetch access permissions from the blockchain based on permission ID.
        This involves:
        1. Fetching the permission from the PermissionRegistry contract
        2. Fetching the grant data from IPFS
        3. Extracting file_ids, operation, and parameters from the grant data
        """
        try:
            # Step 1: Fetch permission from blockchain
            permission = self._fetch_permission_from_blockchain(request.permission_id)
            if not permission:
                raise ValueError(f"Permission {request.permission_id} not found on blockchain")
            
            # Step 2: Fetch grant data from IPFS
            grant_data = self._fetch_grant_from_ipfs(permission['grant'])
            if not grant_data:
                raise ValueError(f"Grant data not found at {permission['grant']}")
            
            # Step 3: Extract data from grant
            file_ids, operation, parameters = self._extract_data_from_grant(grant_data)
            
            return AccessPermissionsResponse(
                app_address=app_address,
                file_ids=file_ids,
                operation=operation,
                parameters=parameters
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch access permissions: {e}")
            raise

    def _fetch_permission_from_blockchain(self, permission_id: int) -> Optional[dict]:
        """Fetch permission data from the PermissionRegistry contract"""
        try:
            if not self.web3.is_connected():
                raise ValueError("Web3 not connected to blockchain")
            
            # Call the permissions function
            permission_data = self.contract.functions.permissions(permission_id).call()
            
            # Debug: Print the raw permission data
            print(f"Raw permission data: {permission_data}")
            
            # Web3.py automatically converts the struct to a named tuple with field access
            # The ABI defines the structure, so we can access fields by name
            result = {
                'id': permission_data.id,
                'grantor': permission_data.grantor,
                'nonce': permission_data.nonce,
                'grant': permission_data.grant,
                'signature': permission_data.signature,
                'isActive': permission_data.isActive,
                'fileIds': permission_data.fileIds
            }
            
            # Debug: Print the parsed permission data
            print(f"Parsed permission data: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch permission {permission_id} from blockchain: {e}")
            return None

    def _fetch_grant_from_ipfs(self, grant_url: str) -> Optional[GrantData]:
        """Fetch grant data from IPFS or HTTP URL"""
        try:
            import requests
            
            # Convert IPFS URL to HTTP gateway URL if needed
            if grant_url.startswith("ipfs://"):
                fetch_url = grant_url.replace("ipfs://", "https://ipfs.io/ipfs/")
            else:
                fetch_url = grant_url
            
            print(f"Fetching grant from: {fetch_url}")
            
            # Fetch the grant data
            response = requests.get(fetch_url, timeout=10)
            response.raise_for_status()
            
            grant_json = response.json()
            print(f"Grant JSON: {grant_json}")
            
            # Support both old (typedData) and new (flat) grant structure
            if "typedData" in grant_json:
                result = GrantData(
                    typedData=grant_json.get("typedData", {}),
                    signature=grant_json.get("signature", "")
                )
            else:
                # Wrap flat structure in a typedData-like dict for compatibility
                result = GrantData(
                    typedData={
                        "message": {
                            "operation": grant_json.get("operation", ""),
                            "files": grant_json.get("files", []),
                            "parameters": grant_json.get("parameters", {})
                        }
                    },
                    signature=grant_json.get("signature", "")
                )
            print(f"Parsed grant data: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to fetch grant from {grant_url}: {e}")
            return None

    def _extract_data_from_grant(self, grant_data: GrantData) -> tuple[set[int], str, dict]:
        """Extract file_ids, operation, and parameters from grant data"""
        try:
            typed_data = grant_data.typedData
            message = typed_data.get("message", {})
            
            # Extract file IDs
            files = message.get("files", [])
            file_ids = set(files)
            
            # Extract operation
            operation = message.get("operation", "")
            
            # Extract and parse parameters
            parameters_val = message.get("parameters", {})
            if isinstance(parameters_val, str):
                try:
                    parameters = json.loads(parameters_val)
                except json.JSONDecodeError:
                    parameters = {}
            elif isinstance(parameters_val, dict):
                parameters = parameters_val
            else:
                parameters = {}
            
            return file_ids, operation, parameters
        except Exception as e:
            logger.error(f"Failed to extract data from grant: {e}")
            raise ValueError(f"Invalid grant data format: {e}")
