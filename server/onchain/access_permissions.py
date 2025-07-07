import json
import logging
import os
from typing import Optional
import web3
from web3 import Web3
from eth_account.messages import encode_defunct

from entities import AccessPermissionsResponse, PersonalServerRequest, GrantData

logger = logging.getLogger(__name__)

class AccessPermissions:
    def __init__(self):
        # Initialize Web3 connection
        blockchain_url = os.getenv("BLOCKCHAIN_HTTP_URL", "https://rpc.moksha.vana.org")
        self.web3 = Web3(Web3.HTTPProvider(blockchain_url))
        
        # PermissionRegistry contract address and ABI
        self.permission_registry_address = os.getenv(
            "PERMISSION_REGISTRY_ADDRESS", 
            "0x3acB2023DF2617EFb61422BA0c8C6E97916961e0"  # Moksha Address
        )
        
        # Full ABI from PermissionRegistryImplementation.ts
        self.permission_registry_abi = [
            {
                "inputs": [
                    {
                        "internalType": "uint256",
                        "name": "permissionId",
                        "type": "uint256"
                    }
                ],
                "name": "permissions",
                "outputs": [
                    {
                        "components": [
                            {
                                "internalType": "address",
                                "name": "user",
                                "type": "address"
                            },
                            {
                                "internalType": "uint256",
                                "name": "nonce",
                                "type": "uint256"
                            },
                            {
                                "internalType": "string",
                                "name": "grant",
                                "type": "string"
                            },
                            {
                                "internalType": "bytes",
                                "name": "signature",
                                "type": "bytes"
                            }
                        ],
                        "internalType": "struct IDataPermission.Permission",
                        "name": "",
                        "type": "tuple"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        self.contract = self.web3.eth.contract(
            address=self.permission_registry_address,
            abi=self.permission_registry_abi
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
            
            # Handle the struct return type properly
            if hasattr(permission_data, 'user'):
                # If it's a named tuple/struct
                result = {
                    'user': permission_data.user,
                    'nonce': permission_data.nonce,
                    'grant': permission_data.grant,
                    'signature': permission_data.signature
                }
            else:
                # Fallback to tuple indexing
                result = {
                    'user': permission_data[0],
                    'nonce': permission_data[1],
                    'grant': permission_data[2],
                    'signature': permission_data[3]
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
