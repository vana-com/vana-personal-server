import os
import logging
from typing import Optional
from web3 import Web3
from entities import FileMetadata

logger = logging.getLogger(__name__)

class DataRegistry:
    def __init__(self):
        # Initialize Web3 connection
        blockchain_url = os.getenv("BLOCKCHAIN_HTTP_URL", "https://rpc.moksha.vana.org")
        self.web3 = Web3(Web3.HTTPProvider(blockchain_url))
        
        # DataRegistry contract address and ABI
        self.data_registry_address = os.getenv(
            "DATA_REGISTRY_ADDRESS", 
            "0x8C8788f98385F6ba1adD4234e551ABba0f82Cb7C"  # DataRegistry Proxy address
        )
        
        # ABI for the files and filePermissions functions from DataRegistryImplementation.ts
        self.data_registry_abi = [
            {
                "inputs": [
                    {
                        "internalType": "uint256",
                        "name": "fileId",
                        "type": "uint256"
                    }
                ],
                "name": "files",
                "outputs": [
                    {
                        "components": [
                            {
                                "internalType": "uint256",
                                "name": "id",
                                "type": "uint256"
                            },
                            {
                                "internalType": "address",
                                "name": "ownerAddress",
                                "type": "address"
                            },
                            {
                                "internalType": "string",
                                "name": "url",
                                "type": "string"
                            },
                            {
                                "internalType": "uint256",
                                "name": "addedAtBlock",
                                "type": "uint256"
                            }
                        ],
                        "internalType": "struct IDataRegistry.FileResponse",
                        "name": "",
                        "type": "tuple"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {
                        "internalType": "uint256",
                        "name": "fileId",
                        "type": "uint256"
                    },
                    {
                        "internalType": "address",
                        "name": "account",
                        "type": "address"
                    }
                ],
                "name": "filePermissions",
                "outputs": [
                    {
                        "internalType": "string",
                        "name": "",
                        "type": "string"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            },
        ]
        
        self.contract = self.web3.eth.contract(
            address=self.data_registry_address,
            abi=self.data_registry_abi
        )

    def fetch_file_metadata(self, file_id: int, user_address: str) -> Optional[FileMetadata]:
        """Fetch file metadata from the DataRegistry contract"""
        try:
            if not self.web3.is_connected():
                raise ValueError("Web3 not connected to blockchain")
            
            # Call the files function
            file_data = self.contract.functions.files(file_id).call()
            
            # Debug: Print the raw file data
            print(f"Raw file data for file {file_id}: {file_data}")
            
            # Use attribute access for the latest web3 SDK
            file_id_from_contract = file_data.id
            owner_address = file_data.ownerAddress
            public_url = file_data.url
            
            # Debug: Print the parsed file data
            print(f"Parsed file data: id={file_id_from_contract}, owner={owner_address}, url={public_url}")
            
            # For now, we need to get the encrypted key from somewhere else
            # This might be stored separately or derived from the file data
            # For testing, we'll use a placeholder
            encrypted_key = self._get_encrypted_key_for_file(file_id, owner_address)
            
            return FileMetadata(
                file_id=file_id_from_contract,
                owner_address=owner_address,
                public_url=public_url,
                encrypted_key=encrypted_key
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch file {file_id} from blockchain: {e}")
            return None

    def _get_encrypted_key_for_file(self, file_id: int, owner_address: str) -> str:
        """Get the encrypted key for a file using the filePermissions function."""
        try:
            if not self.web3.is_connected():
                raise ValueError("Web3 not connected to blockchain")
            
            # Call the filePermissions function to get the encrypted key
            encrypted_key = self.contract.functions.filePermissions(file_id, owner_address).call()
            
            return encrypted_key
            
        except Exception as e:
            logger.error(f"Failed to fetch encrypted key for file {file_id} and owner {owner_address}: {e}")
            raise