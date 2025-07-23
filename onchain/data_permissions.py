import logging
from typing import Optional

from domain.entities import PermissionData
from web3 import AsyncWeb3

from .abi import get_abi
from .chain import Chain, get_data_permissions_address

logger = logging.getLogger(__name__)


class DataPermissions:
    def __init__(self, chain: Chain, web3: AsyncWeb3):
        self.chain = chain
        self.web3 = web3

        self.data_permissions_address = get_data_permissions_address(chain.chain_id)
        self.data_permissions_abi = get_abi("DataPermissions")

        self.contract = self.web3.eth.contract(
            address=self.data_permissions_address, abi=self.data_permissions_abi
        )

    async def fetch_permission_from_blockchain(
        self, permission_id: int
    ) -> Optional[PermissionData]:
        """Fetch permission data from the PermissionRegistry contract"""
        try:
            # AsyncWeb3 connection check would need to be awaited if available
            # For now, we'll proceed with the contract call

            # Call the permissions function
            logger.info(f"[BLOCKCHAIN] Fetching permission {permission_id} from DataPermissions contract")
            logger.info(f"[BLOCKCHAIN] Contract address: {self.data_permissions_address}, Chain: {self.chain.chain_id}")
            
            permission_data = await self.contract.functions.permissions(permission_id).call()
            logger.info(f"[BLOCKCHAIN] Contract call successful for permission {permission_id}")

            result = PermissionData(
                id=permission_data[0],
                grantor=permission_data[1],
                nonce=permission_data[2],
                grant=permission_data[3],
                signature=permission_data[4],
                is_active=permission_data[5],
                file_ids=permission_data[6],
            )

            # Log the parsed permission data with contract details
            logger.info(f"[BLOCKCHAIN] Parsed permission data: {result}")
            logger.info(f"[BLOCKCHAIN] Permission {permission_id} - Grantor: {result.grantor}, Active: {result.is_active}, Files: {len(result.file_ids)}")

            return result

        except Exception as e:
            logger.error(
                f"[BLOCKCHAIN] Failed to fetch permission {permission_id} from blockchain: {e}"
            )
            logger.error(f"[BLOCKCHAIN] Contract address: {self.data_permissions_address}, Chain: {self.chain.chain_id}")
            logger.error(f"[BLOCKCHAIN] Exception type: {type(e).__name__}")
            return None
