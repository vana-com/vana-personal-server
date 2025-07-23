import logging
from typing import Optional

from domain.entities import PermissionData
from web3 import Web3

from .abi import get_abi
from .chain import Chain, get_data_permissions_address

logger = logging.getLogger(__name__)


class DataPermissions:
    def __init__(self, chain: Chain, web3: Web3):
        self.chain = chain
        self.web3 = web3

        self.data_permissions_address = get_data_permissions_address(chain.chain_id)
        self.data_permissions_abi = get_abi("DataPermissions")

        self.contract = self.web3.eth.contract(
            address=self.data_permissions_address, abi=self.data_permissions_abi
        )

    def fetch_permission_from_blockchain(
        self, permission_id: int
    ) -> Optional[PermissionData]:
        """Fetch permission data from the PermissionRegistry contract"""
        try:
            logger.info(f"[DATA_PERMISSIONS] Starting fetch_permission_from_blockchain for ID: {permission_id}")
            logger.info(f"[DATA_PERMISSIONS] Web3 instance: {self.web3}")
            logger.info(f"[DATA_PERMISSIONS] Contract address: {self.data_permissions_address}")
            
            if not self.web3.is_connected():
                logger.error("[DATA_PERMISSIONS] Web3 is not connected!")
                raise ValueError("Web3 not connected to blockchain")
            
            logger.info(f"[DATA_PERMISSIONS] Web3 is connected. Chain ID: {self.web3.eth.chain_id}")

            # Call the permissions function
            logger.info(f"[DATA_PERMISSIONS] About to call contract.functions.permissions({permission_id})")
            logger.info(f"[DATA_PERMISSIONS] Contract object: {self.contract}")
            logger.info(f"[DATA_PERMISSIONS] Contract functions: {dir(self.contract.functions)}")
            
            # THIS IS THE CRITICAL LINE WHERE IT CRASHES
            logger.info(f"[DATA_PERMISSIONS] *** CALLING CONTRACT NOW ***")
            permission_data = self.contract.functions.permissions(permission_id).call()
            logger.info(f"[DATA_PERMISSIONS] *** CONTRACT CALL SUCCEEDED ***")

            result = PermissionData(
                id=permission_data[0],
                grantor=permission_data[1],
                nonce=permission_data[2],
                grant=permission_data[3],
                signature=permission_data[4],
                is_active=permission_data[5],
                file_ids=permission_data[6],
            )

            # Debug: logger.info the parsed permission data
            logger.info(f"Parsed permission data: {result}")

            return result

        except Exception as e:
            logger.error(
                f"Failed to fetch permission {permission_id} from blockchain: {e}"
            )
            return None
